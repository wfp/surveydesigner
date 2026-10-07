"""Codebook scope for expression validation and dependency metadata.

Admin forms, bulk edits, and bulk import all validate expression-bearing fields
here before anything is persisted or dependency metadata is synchronized.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from django.db.models import Q
from questions.models import (
    BaseQuestion,
    Calculation,
    RepeatSection,
    RootQuestion,
    SubQuestion,
)

from .expression_validation import (
    DEPENDENCY_CYCLE_FIELDS,
    DependencyEdge,
    ExpressionContext,
    analyse_expression,
    cycle_dependency_names,
    dependency_cycle_issue,
    expression_dependency_names,
    find_dependency_cycles,
    lint_expression,
)
from .form_validation import ValidationIssue
from .xls_form import XLSForm

# Names every generated survey emits, so expressions may reference them.
GENERATED_METADATA_NAMES = frozenset(
    (*XLSForm.METADATA, *XLSForm.SURVEY_DESIGNER_METADATA_FIELD_NAMES)
)
# Bound the dependency walk; cycles longer than this are left to the
# final-artifact gate, which sees the whole composed survey.
_MAX_CYCLE_SEARCH_NODES = 500
_DEPENDENCY_RELATIONS = {
    RootQuestion: {
        "relevant": "relevant_dependencies",
        "constraint": "constraint_dependencies",
        "required": "required_dependencies",
        "read_only": "read_only_dependencies",
        "default": "default_dependencies",
        "choice_filter": "choice_filter_dependencies",
        "calculation": "calculation_dependencies",
    },
    RepeatSection: {
        "relevant": "relevant_dependencies",
        "repeat_count": "repeat_count_dependencies",
    },
    Calculation: {"calculation": "related_questions"},
}
_DEPENDENCY_RELATIONS[SubQuestion] = _DEPENDENCY_RELATIONS[RootQuestion]


@dataclass
class ReferenceScope:
    """Codebook names that could satisfy a set of references."""

    names: set[str] = field(default_factory=set)
    types: dict[str, str] = field(default_factory=dict)
    repeats: dict[str, frozenset[str]] = field(default_factory=dict)

    def update(self, other: "ReferenceScope") -> None:
        self.names.update(other.names)
        self.types.update(other.types)
        self.repeats.update(other.repeats)


def expression_references(values: Mapping[str, Any]) -> set[str]:
    """Every name referenced by the well-formed expressions in ``values``."""

    names: set[str] = set()
    for value in values.values():
        text = str(value or "").strip()
        if text:
            names.update(
                reference.name for reference in analyse_expression(text).references
            )
    return names


def load_reference_scope(names: Iterable[str]) -> ReferenceScope:
    """Load exact and case-variant codebook matches for ``names``.

    Names use a case-insensitive collation, so ``name__in`` also returns case
    variants. Callers compare exactly, which turns those into case-mismatch
    diagnostics instead of silently resolving them.
    """

    names = {name for name in names if name}
    scope = ReferenceScope()
    if not names:
        return scope

    folded = {name.casefold() for name in names}
    scope.names.update(
        name for name in GENERATED_METADATA_NAMES if name.casefold() in folded
    )
    for name, type_ in RootQuestion.objects.filter(name__in=names).values_list(
        "name", "type"
    ):
        scope.names.add(name)
        scope.types[name] = type_
    for sub_question in SubQuestion.objects.filter(name__in=names).select_related(
        "root_question", "suffix", "suffix_2"
    ):
        scope.names.add(sub_question.name)
        scope.types[sub_question.name] = sub_question.type
    for name in RepeatSection.objects.filter(name__in=names).values_list(
        "name", flat=True
    ):
        scope.names.add(name)
        scope.types[name] = "repeat"
        scope.repeats[name] = frozenset((name,))

    membership = RepeatSection.questions.through.objects.filter(
        Q(basequestion__root_question__name__in=names)
        | Q(basequestion__sub_question__name__in=names)
    ).values_list(
        "repeatsection__name",
        "basequestion__root_question__name",
        "basequestion__sub_question__name",
    )
    repeats_by_name: dict[str, set[str]] = defaultdict(set)
    for repeat_name, root_name, sub_name in membership:
        repeats_by_name[root_name or sub_name].add(repeat_name)
    for name, repeat_names in repeats_by_name.items():
        scope.repeats[name] = frozenset(repeat_names)
    return scope


def _cycle_edges(
    owner: Mapping[str, Any], values: Mapping[str, Any], question_type: str
) -> list[DependencyEdge]:
    edges = []
    for field_name in sorted(DEPENDENCY_CYCLE_FIELDS):
        for name in sorted(
            cycle_dependency_names(
                values.get(field_name), field_name, owner["name"], question_type
            )
        ):
            edges.append(DependencyEdge(owner["name"], name, owner, field_name))
    return edges


def _load_cycle_expressions(
    names: set[str],
) -> dict[str, tuple[Mapping[str, Any], Mapping[str, Any], str]]:
    fields = ("id", "name", "type", *sorted(DEPENDENCY_CYCLE_FIELDS))
    loaded = {}
    for row in RootQuestion.objects.filter(name__in=names).values(*fields):
        if row["name"] in names:
            owner = {"model": "RootQuestion", "id": row["id"], "name": row["name"]}
            loaded[row["name"]] = (owner, row, row["type"])
    for sub_question in SubQuestion.objects.filter(name__in=names).select_related(
        "root_question", "suffix", "suffix_2"
    ):
        if sub_question.name in names:
            owner = {
                "model": "SubQuestion",
                "id": sub_question.id,
                "name": sub_question.name,
            }
            values = {
                field_name: getattr(sub_question, field_name)
                for field_name in DEPENDENCY_CYCLE_FIELDS
            }
            loaded[sub_question.name] = (owner, values, sub_question.type)
    for row in RepeatSection.objects.filter(name__in=names).values(
        "id", "name", "relevant"
    ):
        if row["name"] in names:
            owner = {"model": "RepeatSection", "id": row["id"], "name": row["name"]}
            loaded.setdefault(row["name"], (owner, {"relevant": row["relevant"]}, ""))
    return loaded


def _dependency_cycle_issues(
    owner: Mapping[str, Any],
    values: Mapping[str, Any],
    question_type: str,
    *,
    previous_name: str | None,
    overrides: Mapping[str, tuple[Mapping[str, Any], Mapping[str, Any], str]],
) -> list[ValidationIssue]:
    name = owner.get("name")
    if not name:
        return []

    aliases = {name, previous_name} - {None}
    edges = _cycle_edges(owner, values, question_type)
    visited = set(aliases)
    frontier = {edge.target for edge in edges} - visited
    while frontier and len(visited) < _MAX_CYCLE_SEARCH_NODES:
        visited.update(frontier)
        loaded = {
            target: overrides[target] for target in frontier if target in overrides
        }
        loaded.update(_load_cycle_expressions(frontier - set(loaded)))
        next_frontier = set()
        for target_owner, target_values, target_type in loaded.values():
            for edge in _cycle_edges(target_owner, target_values, target_type):
                # A rename is propagated to dependants after save.
                target = name if edge.target in aliases else edge.target
                edges.append(
                    DependencyEdge(edge.source, target, edge.owner, edge.field)
                )
                if target not in visited:
                    next_frontier.add(target)
        frontier = next_frontier

    return [
        dependency_cycle_issue(cycle, layer="model")
        for cycle in find_dependency_cycles(edges)
        if cycle[0].source == name
    ]


def validate_expression_fields(
    owner: Mapping[str, Any],
    values: Mapping[str, Any],
    *,
    question_type: str = "",
    repeats: Iterable[str] = (),
    members: Iterable[str] = (),
    previous_name: str | None = None,
    scope: ReferenceScope | None = None,
    cycle_overrides: (
        Mapping[str, tuple[Mapping[str, Any], Mapping[str, Any], str]] | None
    ) = None,
    check_cycles: bool = True,
) -> list[ValidationIssue]:
    """Validate an owner's expression fields against the codebook.

    ``repeats`` are the repeats that contain the owner; a repeat's own fields
    are evaluated outside it, so a repeat passes its ``members`` instead.
    ``scope`` and ``cycle_overrides`` let bulk callers resolve references once
    and include records that are not saved yet, such as other rows of the same
    bulk-import spreadsheet.
    """

    if scope is None:
        scope = load_reference_scope(expression_references(values))
    scope = ReferenceScope(set(scope.names), dict(scope.types), dict(scope.repeats))
    # Calculations are not survey nodes, so their own name never resolves.
    if owner.get("name") and owner.get("model") != "Calculation":
        # A rename is propagated to the owner's own references after save.
        for name in {owner["name"], previous_name} - {None}:
            scope.names.add(name)
            scope.types.setdefault(name, question_type)
            if owner.get("model") != "RepeatSection":
                # The submitted repeat membership replaces what is stored.
                scope.repeats[name] = frozenset(repeats)

    # A calculation has no position in a survey, so repeat context is unknown.
    name_repeats = {} if owner.get("model") == "Calculation" else scope.repeats
    issues: list[ValidationIssue] = []
    valid_values = {}
    for field_name, value in values.items():
        context = ExpressionContext(
            owner=owner,
            field=field_name,
            question_type=question_type,
            available_names=frozenset(scope.names),
            repeats=frozenset(repeats),
            own_members=frozenset(members),
            name_repeats=name_repeats,
            name_types=scope.types,
        )
        field_issues = lint_expression(value, context)
        issues.extend(field_issues)
        if not field_issues:
            valid_values[field_name] = value

    if question_type == "calculate" and "calculation" in values:
        if not str(values.get("calculation") or "").strip():
            issues.append(
                ExpressionContext(owner=owner, field="calculation").issue(
                    "EXPRESSION_CALCULATION_MISSING",
                    "must contain an expression for a calculate question.",
                )
            )

    if check_cycles:
        issues.extend(
            _dependency_cycle_issues(
                owner,
                valid_values,
                question_type,
                previous_name=previous_name,
                overrides=cycle_overrides or {},
            )
        )
    return issues


def _dependency_ids_by_name(names: set[str]) -> dict[str, list[int]]:
    """BaseQuestion ids for each name, matched exactly despite the collation."""

    ids_by_name: dict[str, list[int]] = defaultdict(list)
    if names:
        for base_question in BaseQuestion.objects.filter(
            Q(root_question__name__in=names)
            | Q(sub_question__name__in=names)
            | Q(repeat_section__name__in=names)
        ).select_related("root_question", "sub_question", "repeat_section"):
            if base_question.name in names:
                ids_by_name[base_question.name].append(base_question.id)
    return ids_by_name


def sync_expression_dependencies(instance: Any) -> None:
    """Record exact dependencies for every expression-bearing field."""

    question_type = ""
    if isinstance(instance, (RootQuestion, SubQuestion)):
        question_type = instance.type or ""
    names_by_relation = {
        relation: expression_dependency_names(
            getattr(instance, field_name), field_name, question_type
        )
        for field_name, relation in _DEPENDENCY_RELATIONS[
            instance._meta.concrete_model
        ].items()
    }
    ids_by_name = _dependency_ids_by_name(set().union(*names_by_relation.values()))
    for relation, names in names_by_relation.items():
        getattr(instance, relation).set(
            [id_ for name in names for id_ in ids_by_name.get(name, ())]
        )


__all__ = [
    "GENERATED_METADATA_NAMES",
    "ReferenceScope",
    "expression_references",
    "load_reference_scope",
    "sync_expression_dependencies",
    "validate_expression_fields",
]
