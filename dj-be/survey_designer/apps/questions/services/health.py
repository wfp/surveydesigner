"""Bounded, read-only survey health checks for the admin UI.

The health page deliberately uses the same model expression validator as the
authoring forms.  It only reads the four model types that contain expressions;
it does not compose a survey or generate an XForm.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from django.db import DatabaseError, connection, transaction
from django.db.models import F, Q
from django.db.models.functions import Substr
from questions.models import Calculation, RepeatSection, RootQuestion, SubQuestion

from .expression_scope import (
    GENERATED_METADATA_NAMES,
    CycleTraversalLimitExceeded,
    ReferenceScope,
    expression_references,
    validate_expression_fields,
)
from .expression_validation import (
    DEPENDENCY_CYCLE_FIELDS,
    QUESTION_EXPRESSION_FIELDS,
    REPEAT_EXPRESSION_FIELDS,
    analyse_expression,
)
from .form_validation import ValidationIssue

# These values are intentionally conservative.  The browser asks for one page
# at a time, so a slow or unusually large page can be reported as incomplete.
MAX_BATCH_SIZE = 25
MAX_EXPRESSION_LENGTH = 10_000
MAX_REFERENCES_PER_BATCH = 2_000
MAX_ISSUES_PER_BATCH = 250
MAX_ISSUES_PER_OBJECT = 100
MAX_QUERIES_PER_BATCH = 500
MAX_REPEAT_MEMBERS = 1_000
MAX_SCOPE_MEMBERSHIPS = 5_000
MAX_CYCLE_NODES = 100
BATCH_BUDGET_SECONDS = 2.7
CYCLE_LIMIT_REASON = "The dependency graph exceeded the safe health scan limits."


class HealthScanInfrastructureError(Exception):
    """A batch could not be checked reliably."""


class HealthObjectLimitError(Exception):
    def __init__(self, owner: dict[str, Any], code: str, message: str):
        super().__init__(message)
        self.owner = owner
        self.code = code
        self.message = message


class HealthCycleLimitError(Exception):
    def __init__(self, owner: dict[str, Any] | None, code: str, message: str):
        super().__init__(message)
        self.owner = owner
        self.code = code
        self.message = message


class _ScanQueryGuard:
    """Bound database work without changing the shared connection globally.

    Python parser and validator work is checked between objects as a
    cooperative budget; Python cannot safely interrupt a running expression
    parse in the shared web process.
    """

    def __init__(self, started: float):
        self.started = started
        self.query_count = 0

    def __call__(self, execute, sql, params, many, context):
        if time.monotonic() - self.started > BATCH_BUDGET_SECONDS:
            raise HealthScanInfrastructureError(
                "The time budget for this read-only health page was reached."
            )
        self.query_count += 1
        if self.query_count > MAX_QUERIES_PER_BATCH:
            raise HealthScanInfrastructureError(
                "The query budget for this read-only health page was reached."
            )
        return execute(sql, params, many, context)


@dataclass(frozen=True)
class HealthModelSpec:
    key: str
    label: str
    model: type
    expression_fields: tuple[str, ...]


MODEL_SPECS = {
    spec.key: spec
    for spec in (
        HealthModelSpec(
            "root_question", "Root question", RootQuestion, QUESTION_EXPRESSION_FIELDS
        ),
        HealthModelSpec(
            "sub_question", "Sub-question", SubQuestion, QUESTION_EXPRESSION_FIELDS
        ),
        HealthModelSpec(
            "repeat_section", "Repeat section", RepeatSection, REPEAT_EXPRESSION_FIELDS
        ),
        HealthModelSpec("calculation", "Calculation", Calculation, ("calculation",)),
    )
}
MODEL_ORDER = tuple(MODEL_SPECS)

FIELD_LABELS = {
    "relevant": "Relevant",
    "constraint": "Constraint",
    "required": "Required",
    "read_only": "Read only",
    "default": "Default",
    "choice_filter": "Choice filter",
    "calculation": "Calculation",
    "repeat_count": "Repeat count",
}

SUGGESTIONS = {
    "EXPRESSION_REFERENCE_UNRESOLVED": "Check the referenced name and create or restore the matching codebook object before saving.",
    "EXPRESSION_REFERENCE_CASE_MISMATCH": "Use the exact capitalization of the stored codebook name in the expression.",
    "EXPRESSION_REFERENCE_INVALID": "Correct the reference to use ${name} with a valid name.",
    "EXPRESSION_REFERENCE_UNTERMINATED": "Close the ${name} reference and check that its name is complete.",
    "EXPRESSION_REFERENCE_NESTED": "Remove the nested ${...} reference and use a single valid reference.",
    "EXPRESSION_SYNTAX_INVALID": "Review the expression operators, parentheses, quotes, and function names, then save again.",
    "EXPRESSION_INCOMPLETE": "Complete the expression after the reported token or remove the incomplete fragment.",
    "EXPRESSION_REPEAT_CONTEXT_INVALID": "Move the reference into the matching repeat or use an aggregate such as count(), sum(), or indexed-repeat().",
    "EXPRESSION_RESULT_TYPE_INVALID": "Change the expression so its result matches the question or repeat count type.",
    "EXPRESSION_DEPENDENCY_CYCLE": "Break the dependency cycle by changing one of the listed expressions.",
    "EXPRESSION_CALCULATION_MISSING": "Add a calculation expression before saving the calculate question.",
    "CALCULATION_NO_QUESTION_REFERENCES": "Add at least one question reference such as ${question_name} to this calculation.",
    "HEALTH_REPEAT_MEMBERS_LIMIT": "Ask a maintainer to review the scan limits or use a targeted check; no data change is implied by this limit.",
    "HEALTH_INPUT_TOO_LARGE": "Ask a maintainer to review the scan limits or use a targeted check; no data change is implied by this limit.",
    "HEALTH_CYCLE_INPUT_TOO_LARGE": "Ask a maintainer to review the scan limits or use a targeted check; no data change is implied by this limit.",
    "HEALTH_EXPRESSION_UNREADABLE": "Ask a maintainer to review the scan limits or use a targeted check; no data change is implied by this scan error.",
    "HEALTH_REFERENCE_LIMIT": "Ask a maintainer to review the scan limits or use a targeted check; no data change is implied by this limit.",
    "HEALTH_ISSUE_LIMIT": "Ask a maintainer to review the scan limits or use a targeted check; no data change is implied by this limit.",
    "HEALTH_CYCLE_GRAPH_LIMIT": "Ask a maintainer to review the scan limits or use a targeted check; no data change is implied by this limit.",
}


def model_spec(model_key: str) -> HealthModelSpec:
    try:
        return MODEL_SPECS[model_key]
    except KeyError as error:
        raise HealthScanInfrastructureError("Unknown survey health model.") from error


def _bounded_repeat_members(relation):
    return list(relation.only("id", "name")[: MAX_REPEAT_MEMBERS + 1])


def _bounded_base_questions(relation):
    return list(
        relation.select_related("root_question", "sub_question", "repeat_section").only(
            "id",
            "root_question__id",
            "root_question__name",
            "sub_question__id",
            "sub_question__name",
            "repeat_section__id",
            "repeat_section__name",
        )[: MAX_REPEAT_MEMBERS + 1]
    )


def _oversized_fields(values):
    return [
        field
        for field, value in values.items()
        if len(str(value)) > MAX_EXPRESSION_LENGTH
    ]


def _question_type(root_type, suffix_type, suffix_2_type):
    """Match the model property: suffix_2, suffix, then root."""

    return (
        suffix_2_type
        if suffix_2_type is not None
        else suffix_type if suffix_type is not None else root_type
    ) or ""


def _health_expression_annotations(fields):
    return {
        f"_health_{field}": Substr(field, 1, MAX_EXPRESSION_LENGTH + 1)
        for field in fields
    }


def _objects_queryset(spec: HealthModelSpec, after_pk: int, limit: int):
    queryset = (
        spec.model.objects.annotate(
            **_health_expression_annotations(spec.expression_fields)
        )
        .filter(pk__gt=after_pk)
        .order_by("pk")
    )
    if spec.key == "root_question":
        queryset = queryset.select_related("base_question").only(
            "id", "name", "is_active", "type", "base_question__id"
        )
    elif spec.key == "sub_question":
        queryset = queryset.select_related(
            "root_question", "root_question__base_question", "suffix", "suffix_2"
        ).only(
            "id",
            "name",
            "is_active",
            "root_question__id",
            "root_question__name",
            "root_question__type",
            "root_question__base_question__id",
            "suffix__id",
            "suffix__type",
            "suffix_2__id",
            "suffix_2__type",
        )
    elif spec.key in {"repeat_section", "calculation"}:
        queryset = queryset.only("id", "name", "is_active")
    return list(queryset[:limit])


def _repeat_names(relation, owner):
    repeat_sections = _bounded_repeat_members(relation)
    if len(repeat_sections) > MAX_REPEAT_MEMBERS:
        raise HealthObjectLimitError(
            owner,
            "HEALTH_REPEAT_MEMBERS_LIMIT",
            "The object belongs to more repeats than the scan can load safely.",
        )
    return {repeat.name for repeat in repeat_sections}


def _owner_data(
    spec: HealthModelSpec, obj: Any
) -> tuple[dict[str, Any], dict[str, str], set[str], set[str]]:
    owner = {
        "model": spec.model.__name__,
        "model_key": spec.key,
        "model_label": spec.label,
        "id": obj.pk,
        "name": obj.name,
        "is_active": bool(getattr(obj, "is_active", True)),
    }
    values = {
        field: getattr(obj, f"_health_{field}") or ""
        for field in spec.expression_fields
    }
    if spec.key in {"root_question", "sub_question"}:
        # The SubQuestion admin form submits the root question's repeat
        # membership as the owner's context.  Keep that save-time behavior
        # here; the reference scope still resolves each stored name normally.
        base_question = (
            obj.base_question
            if spec.key == "root_question"
            else obj.root_question.base_question
        )
        return owner, values, _repeat_names(base_question.repeat_sections, owner), set()
    if spec.key == "repeat_section":
        base_questions = _bounded_base_questions(obj.questions)
        if len(base_questions) > MAX_REPEAT_MEMBERS:
            raise HealthObjectLimitError(
                owner,
                "HEALTH_REPEAT_MEMBERS_LIMIT",
                "The repeat contains more question members than the scan can load safely.",
            )
        members = {base_question.name for base_question in base_questions}
        return owner, values, set(), members
    return owner, values, set(), set()


def _configure_read_only_transaction() -> None:
    if connection.vendor != "postgresql":
        return
    with connection.cursor() as cursor:
        # SET TRANSACTION must be the first statement in the transaction.
        cursor.execute("SET TRANSACTION READ ONLY")
        cursor.execute("SET LOCAL statement_timeout = '3000ms'")
        cursor.execute("SET LOCAL lock_timeout = '500ms'")
        cursor.execute("SET LOCAL work_mem = '4MB'")
        cursor.execute("SET LOCAL max_parallel_workers_per_gather = 0")


def count_totals() -> dict[str, int]:
    """Count the four scanned model tables without loading any rows."""

    started = time.monotonic()
    guard = _ScanQueryGuard(started)
    try:
        with connection.execute_wrapper(guard):
            with transaction.atomic():
                _configure_read_only_transaction()
                totals = {
                    spec.key: spec.model.objects.count()
                    for spec in (MODEL_SPECS[key] for key in MODEL_ORDER)
                }
                if time.monotonic() - started > BATCH_BUDGET_SECONDS:
                    raise HealthScanInfrastructureError(
                        "The time budget for health progress totals was reached."
                    )
                return totals
    except HealthScanInfrastructureError:
        raise
    except DatabaseError as error:
        raise HealthScanInfrastructureError(
            "The database could not complete the read-only health totals."
        ) from error
    except Exception as error:
        raise HealthScanInfrastructureError(
            "The health totals could not be prepared."
        ) from error


def _load_bounded_reference_scope(names):
    """Load only the reference metadata needed by the health validator."""

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

    sub_rows = (
        SubQuestion.objects.filter(name__in=names)
        .annotate(
            _health_root_type=F("root_question__type"),
            _health_suffix_type=F("suffix__type"),
            _health_suffix_2_type=F("suffix_2__type"),
        )
        .values(
            "name",
            "_health_root_type",
            "_health_suffix_type",
            "_health_suffix_2_type",
        )
    )
    for row in sub_rows:
        name = row["name"]
        scope.names.add(name)
        scope.types[name] = _question_type(
            row["_health_root_type"],
            row["_health_suffix_type"],
            row["_health_suffix_2_type"],
        )

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
    if membership.count() > MAX_SCOPE_MEMBERSHIPS:
        raise HealthScanInfrastructureError(
            "The referenced repeat membership is too large for this health page."
        )
    repeats_by_name: dict[str, set[str]] = defaultdict(set)
    for repeat_name, root_name, sub_name in membership:
        referenced_name = root_name or sub_name
        repeats_by_name[referenced_name].add(repeat_name)
    for name, repeat_names in repeats_by_name.items():
        scope.repeats[name] = frozenset(repeat_names)
    return scope


def _health_cycle_loader(names):
    """Load a bounded dependency graph projection for health checks.

    The normal validator keeps its legacy loader. This loader is supplied only
    by the health page and uses SQL substring projections so oversized legacy
    expressions are detected before they reach the parser.
    """

    names = {name for name in names if name}
    if not names:
        return {}
    loaded = {}
    for model_key in ("root_question", "sub_question", "repeat_section"):
        spec = MODEL_SPECS[model_key]
        fields = (
            ("relevant",)
            if model_key == "repeat_section"
            else tuple(sorted(DEPENDENCY_CYCLE_FIELDS))
        )
        aliases = {field: f"_health_cycle_{field}" for field in fields}
        projected = {
            alias: Substr(field, 1, MAX_EXPRESSION_LENGTH + 1)
            for field, alias in aliases.items()
        }
        queryset = spec.model.objects.filter(name__in=names).annotate(**projected)
        if model_key == "root_question":
            rows = queryset.values("id", "name", "is_active", "type", *aliases.values())
        elif model_key == "sub_question":
            rows = queryset.annotate(
                _health_cycle_root_type=F("root_question__type"),
                _health_cycle_suffix_type=F("suffix__type"),
                _health_cycle_suffix_2_type=F("suffix_2__type"),
            ).values(
                "id",
                "name",
                "is_active",
                "_health_cycle_root_type",
                "_health_cycle_suffix_type",
                "_health_cycle_suffix_2_type",
                *aliases.values(),
            )
        else:
            rows = queryset.values("id", "name", "is_active", *aliases.values())

        for row in rows:
            if row["name"] not in names:
                continue
            values = {field: row[alias] or "" for field, alias in aliases.items()}
            owner = {
                "model": spec.model.__name__,
                "model_key": model_key,
                "model_label": spec.label,
                "id": row["id"],
                "name": row["name"],
                "is_active": bool(row["is_active"]),
            }
            oversized = _oversized_fields(values)
            if oversized:
                raise HealthCycleLimitError(
                    owner,
                    "HEALTH_CYCLE_INPUT_TOO_LARGE",
                    f"A dependency expression is larger than the {MAX_EXPRESSION_LENGTH:,} character scan limit ({', '.join(oversized)}).",
                )
            if model_key == "root_question":
                question_type = row["type"] or ""
            elif model_key == "sub_question":
                question_type = _question_type(
                    row["_health_cycle_root_type"],
                    row["_health_cycle_suffix_type"],
                    row["_health_cycle_suffix_2_type"],
                )
            else:
                question_type = ""
            record = (owner, values, question_type)
            if model_key == "repeat_section":
                loaded.setdefault(row["name"], record)
            else:
                loaded[row["name"]] = record
    return loaded


def _scan_error(
    owner: dict[str, Any] | None, code: str, message: str
) -> dict[str, Any]:
    return {
        **_owner_payload(owner),
        "code": code,
        "message": message,
        "suggestion": SUGGESTIONS.get(
            code,
            "Review the object and run the health check again after making a safe correction.",
        ),
    }


def _owner_payload(owner: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "model": owner.get("model_key") if owner else None,
        "model_label": owner.get("model_label") if owner else None,
        "id": owner.get("id") if owner else None,
        "name": owner.get("name") if owner else None,
        "is_active": owner.get("is_active") if owner else None,
    }


def _issue_payload(
    issue: Any, owner: dict[str, Any], values: dict[str, str]
) -> dict[str, Any]:
    field = issue.field or ""
    expression = values.get(field, "")
    return {
        **_owner_payload(owner),
        "field": field,
        "field_label": FIELD_LABELS.get(field, field),
        "code": issue.code,
        "message": str(issue.message)[:2_000],
        "suggestion": SUGGESTIONS.get(
            issue.code,
            "Review the expression and the referenced codebook objects, then save the object again.",
        ),
        "expression": str(expression)[:1_000],
    }


def _decorate(payload, objects, model_key, decorate):
    if decorate:
        decorate(payload, {(model_key, obj.pk): obj for obj in objects})


def scan_batch(
    model_key: str,
    after_pk: int = 0,
    requested_limit: int = MAX_BATCH_SIZE,
    *,
    decorate=None,
) -> dict[str, Any]:
    """Scan one capped page and return JSON-ready data.

    The caller must add request-specific edit URLs.  This keeps the service
    independent of admin permissions and makes it safe to reuse in a view.
    """

    spec = model_spec(model_key)
    try:
        after_pk = max(0, int(after_pk))
    except (TypeError, ValueError) as error:
        raise HealthScanInfrastructureError("Invalid survey health cursor.") from error
    try:
        limit = min(MAX_BATCH_SIZE, max(1, int(requested_limit)))
    except (TypeError, ValueError) as error:
        raise HealthScanInfrastructureError(
            "Invalid survey health page size."
        ) from error

    started = time.monotonic()
    guard = _ScanQueryGuard(started)
    try:
        with connection.execute_wrapper(guard):
            with transaction.atomic():
                _configure_read_only_transaction()
                objects = _objects_queryset(spec, after_pk, limit)
                records: list[
                    tuple[Any, dict[str, Any], dict[str, str], set[str], set[str]]
                ] = []
                scan_errors: list[dict[str, Any]] = []

                reference_names: set[str] = set()
                for obj in objects:
                    try:
                        owner, values, repeats, members = _owner_data(spec, obj)
                    except HealthObjectLimitError as error:
                        scan_errors.append(
                            _scan_error(error.owner, error.code, error.message)
                        )
                        continue
                    too_large = _oversized_fields(values)
                    if too_large:
                        scan_errors.append(
                            _scan_error(
                                owner,
                                "HEALTH_INPUT_TOO_LARGE",
                                f"The expression value is larger than the {MAX_EXPRESSION_LENGTH:,} character scan limit ({', '.join(too_large)}).",
                            )
                        )
                        continue
                    try:
                        reference_names.update(expression_references(values))
                    except (MemoryError, RecursionError):
                        scan_errors.append(
                            _scan_error(
                                owner,
                                "HEALTH_EXPRESSION_UNREADABLE",
                                "The expression could not be analysed within the scan limits.",
                            )
                        )
                        continue
                    records.append((obj, owner, values, repeats, members))

                if len(reference_names) > MAX_REFERENCES_PER_BATCH:
                    payload = {
                        "model": model_key,
                        "model_label": spec.label,
                        "items": [],
                        "issues": [],
                        "scan_errors": scan_errors
                        + [
                            _scan_error(
                                None,
                                "HEALTH_REFERENCE_LIMIT",
                                "This page references more names than the scan limit allows; the run is incomplete.",
                            )
                        ],
                        "checked_objects": 0,
                        "failing_objects": 0,
                        "issue_count": 0,
                        "next_cursor": None,
                        "has_more": True,
                        "page_processed": False,
                        "complete": False,
                        "clean": False,
                        "incomplete_reason": "Reference scope limit reached.",
                    }
                    _decorate(payload, objects, model_key, decorate)
                    return payload

                scope = _load_bounded_reference_scope(reference_names)
                issues: list[dict[str, Any]] = []
                checked_objects = 0
                failing_objects = 0
                incomplete_reason = None
                for obj, owner, values, repeats, members in records:
                    if time.monotonic() - started > BATCH_BUDGET_SECONDS:
                        incomplete_reason = "The time budget for this page was reached before every object was checked."
                        break
                    try:
                        validation_issues = validate_expression_fields(
                            owner,
                            values,
                            question_type=(
                                (getattr(obj, "type", "") or "")
                                if spec.key in {"root_question", "sub_question"}
                                else ""
                            ),
                            repeats=repeats,
                            members=members,
                            scope=scope,
                            check_cycles=spec.key != "calculation",
                            cycle_loader=(
                                _health_cycle_loader
                                if spec.key != "calculation"
                                else None
                            ),
                            cycle_search_limit=(
                                MAX_CYCLE_NODES if spec.key != "calculation" else None
                            ),
                        )
                        if spec.key == "calculation" and not validation_issues:
                            # This is the existing CalculationAdminModelForm rule,
                            # reported with its own code so the source is clear.
                            if not analyse_expression(
                                values["calculation"].strip()
                            ).references:
                                validation_issues = [
                                    ValidationIssue(
                                        field="calculation",
                                        code="CALCULATION_NO_QUESTION_REFERENCES",
                                        layer="model",
                                        severity="error",
                                        message=f"Calculation '{owner['name']}' field 'calculation' has no question references.",
                                    )
                                ]
                    except HealthCycleLimitError as error:
                        scan_errors.append(
                            _scan_error(error.owner or owner, error.code, error.message)
                        )
                        incomplete_reason = CYCLE_LIMIT_REASON
                        break
                    except CycleTraversalLimitExceeded as error:
                        scan_errors.append(
                            _scan_error(
                                owner,
                                "HEALTH_CYCLE_GRAPH_LIMIT",
                                str(error),
                            )
                        )
                        incomplete_reason = CYCLE_LIMIT_REASON
                        break
                    except (MemoryError, RecursionError):
                        scan_errors.append(
                            _scan_error(
                                owner,
                                "HEALTH_EXPRESSION_UNREADABLE",
                                "The expression could not be validated within the scan limits.",
                            )
                        )
                        continue
                    checked_objects += 1
                    if validation_issues:
                        failing_objects += 1
                        if len(validation_issues) > MAX_ISSUES_PER_OBJECT:
                            scan_errors.append(
                                _scan_error(
                                    owner,
                                    "HEALTH_ISSUE_LIMIT",
                                    "The object produced more issues than the scan output limit.",
                                )
                            )
                            incomplete_reason = (
                                "An object exceeded the issue output limit."
                            )
                            break
                        for issue in validation_issues:
                            if len(issues) >= MAX_ISSUES_PER_BATCH:
                                incomplete_reason = (
                                    "The page exceeded the issue output limit."
                                )
                                break
                            issues.append(_issue_payload(issue, owner, values))
                        if incomplete_reason:
                            break

                if (
                    incomplete_reason is None
                    and time.monotonic() - started > BATCH_BUDGET_SECONDS
                ):
                    incomplete_reason = (
                        "The time budget for this page was reached after validation."
                    )

                payload = {
                    "model": model_key,
                    "model_label": spec.label,
                    "items": [
                        {
                            "id": owner["id"],
                            "name": owner["name"],
                            "is_active": bool(getattr(obj, "is_active", True)),
                        }
                        for obj, owner, _values, _repeats, _members in records
                    ],
                    "issues": issues,
                    "scan_errors": scan_errors,
                    "checked_objects": checked_objects,
                    "failing_objects": failing_objects,
                    "issue_count": len(issues),
                    "next_cursor": (
                        objects[-1].pk
                        if objects and incomplete_reason is None
                        else None
                    ),
                    "has_more": bool(
                        objects and incomplete_reason is None and len(objects) == limit
                    ),
                    "page_processed": incomplete_reason is None,
                    "complete": incomplete_reason is None and not scan_errors,
                    "clean": incomplete_reason is None and not scan_errors,
                    "incomplete_reason": incomplete_reason,
                }
                _decorate(payload, objects, model_key, decorate)
                if (
                    payload["page_processed"]
                    and time.monotonic() - started > BATCH_BUDGET_SECONDS
                ):
                    payload["page_processed"] = False
                    payload["complete"] = False
                    payload["clean"] = False
                    payload["has_more"] = False
                    payload["next_cursor"] = None
                    payload["incomplete_reason"] = (
                        "The time budget for this page was reached after the result was prepared."
                    )
                return payload
    except HealthScanInfrastructureError:
        raise
    except DatabaseError as error:
        raise HealthScanInfrastructureError(
            "The database could not complete this read-only health page."
        ) from error
    except Exception as error:
        raise HealthScanInfrastructureError(
            "The health page could not complete this read-only health page."
        ) from error


__all__ = [
    "BATCH_BUDGET_SECONDS",
    "FIELD_LABELS",
    "MAX_BATCH_SIZE",
    "MODEL_ORDER",
    "MODEL_SPECS",
    "HealthScanInfrastructureError",
    "count_totals",
    "model_spec",
    "scan_batch",
]
