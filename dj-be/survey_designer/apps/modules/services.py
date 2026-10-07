from collections import defaultdict

from django.db.models import Prefetch, Q
from modules.models import Indicator, Module, Submodule
from questions.models import BaseQuestion, RepeatSection, RootQuestion, SubQuestion
from questions.services.expression_validation import QUESTION_EXPRESSION_FIELDS
from questions.services.form_validation import (
    ValidationIssue,
    expression_question_references,
)


class SubmoduleCompositionValidator:
    def __init__(self, submodule_ids, indicator_ids, all_submodule_ids):
        self.submodule_ids = [int(id_) for id_ in submodule_ids]
        self.indicator_ids = [int(id_) for id_ in indicator_ids]
        self.all_submodule_ids = [int(id_) for id_ in all_submodule_ids]
        self.selected_submodule_ids = set(self.submodule_ids)
        self.submodule_order = {
            submodule_id: index for index, submodule_id in enumerate(self.submodule_ids)
        }
        self.compatibility_results = {}
        self.dependency_results = {}
        self.dependency_issues = []
        self._submodules = None
        self._scope_submodules = None
        self._indicator_questions = None
        self._owner_submodules = {}

    def get_root_question_queryset(self):
        return RootQuestion.objects.select_related("base_question")

    def get_submodules(self):
        if self._submodules is None:
            submodules = list(
                Submodule.objects.filter(id__in=self.submodule_ids)
                .select_related("module")
                .prefetch_related(
                    Prefetch(
                        "root_questions",
                        queryset=self.get_root_question_queryset(),
                        to_attr="prefetched_root_questions",
                    ),
                    Prefetch(
                        "repeat_sections",
                        queryset=RepeatSection.objects.select_related("base_question"),
                        to_attr="prefetched_repeat_sections",
                    ),
                )
            )
            submodules.sort(key=lambda submodule: self.submodule_order[submodule.id])
            self._submodules = submodules
        return self._submodules

    def get_indicator_questions(self):
        if self._indicator_questions is None:
            self._indicator_questions = list(
                BaseQuestion.objects.filter(indicators__id__in=self.indicator_ids)
                .select_related("root_question", "sub_question", "repeat_section")
                .distinct()
            )
        return self._indicator_questions

    def get_scope_submodules(self):
        if self._scope_submodules is None:
            indicator_submodule_ids = Indicator.objects.filter(
                id__in=self.indicator_ids
            ).values_list("questions__root_question__submodule", flat=True)
            scope_ids = self.selected_submodule_ids | {
                submodule_id
                for submodule_id in indicator_submodule_ids
                if submodule_id in self.all_submodule_ids
            }
            self._scope_submodules = list(
                Submodule.objects.filter(id__in=scope_ids).select_related("module")
            )
        return self._scope_submodules

    def get_messages(self):
        return [issue.message for issue in self.get_issues()]

    def get_issues(self):
        issues = []
        for submodule, conflicting_submodules in sorted(
            self.compatibility_results.items(), key=lambda item: item[0].id
        ):
            labels = ", ".join(
                submodule.label
                for submodule in sorted(
                    conflicting_submodules, key=lambda item: item.id
                )
            )
            issues.append(
                ValidationIssue(
                    code="SELECTED_SCOPE_SUBMODULE_CONFLICT",
                    layer="composition",
                    severity="error",
                    message=f"{submodule.label} contains questions from: {labels}. Select only one of these submodules.",
                    owner=self._owner(submodule),
                    submodule=self._submodule(submodule),
                    dependency={
                        "status": "conflict",
                        "submodules": [
                            self._submodule(conflicting_submodule)
                            for conflicting_submodule in sorted(
                                conflicting_submodules,
                                key=lambda item: item.id,
                            )
                        ],
                    },
                    field="submodules",
                )
            )
        issues.extend(self.dependency_issues)
        return issues

    def validate_compatibility(self):
        self.compatibility_results = {}
        submodules_by_root_question = defaultdict(set)
        submodules_by_repeat_section = defaultdict(set)

        for submodule in self.get_submodules():
            for question in submodule.prefetched_root_questions:
                submodules_by_root_question[question.id].add(submodule)
            for repeat_section in submodule.prefetched_repeat_sections:
                submodules_by_repeat_section[repeat_section.id].add(submodule)

        processed_submodules = set()
        for submodule in self.get_submodules():
            next_submodules = set()
            for question in submodule.prefetched_root_questions:
                next_submodules.update(submodules_by_root_question[question.id])
            for repeat_section in submodule.prefetched_repeat_sections:
                next_submodules.update(submodules_by_repeat_section[repeat_section.id])

            next_submodules.discard(submodule)
            intersection = next_submodules.intersection(processed_submodules)
            if intersection:
                self.compatibility_results[submodule] = intersection

            processed_submodules.add(submodule)

        return self.compatibility_results

    @staticmethod
    def _expression_fields(owner):
        if isinstance(owner, (Module, Submodule)):
            return ("relevant",)
        if isinstance(owner, (RootQuestion, SubQuestion)):
            return QUESTION_EXPRESSION_FIELDS
        if isinstance(owner, RepeatSection):
            return ("relevant", "repeat_count")
        return ()

    @staticmethod
    def _owner(owner):
        return {
            "model": owner.__class__.__name__,
            "id": owner.id,
            "name": owner.name,
        }

    @staticmethod
    def _submodule(submodule):
        return {
            "model": "Submodule",
            "id": submodule.id,
            "name": submodule.name,
            "label": submodule.label,
        }

    def _add_owner_submodule(self, owner, submodule):
        key = (owner.__class__, owner.id)
        self._owner_submodules.setdefault(key, {})[submodule.id] = submodule

    def _affected_submodule(self, owner):
        submodules = self._owner_submodules.get((owner.__class__, owner.id), {})
        if not submodules:
            return None
        submodule = min(
            submodules.values(),
            key=lambda item: (
                self.submodule_order.get(item.id, len(self.submodule_order)),
                item.id,
            ),
        )
        return self._submodule(submodule)

    def _scope_expression_owners(self):
        owners = {}
        self._owner_submodules = {}

        def add(owner, submodule=None):
            owners[(owner.__class__, owner.id)] = owner
            if submodule is not None:
                self._add_owner_submodule(owner, submodule)

        for submodule in self.get_scope_submodules():
            add(submodule.module, submodule)
            add(submodule, submodule)
        for submodule in self.get_submodules():
            for question in submodule.prefetched_root_questions:
                add(question, submodule)
            for repeat_section in submodule.prefetched_repeat_sections:
                add(repeat_section, submodule)
        for base_question in self.get_indicator_questions():
            owner = base_question.instance
            if isinstance(owner, (RootQuestion, SubQuestion, RepeatSection)):
                add(owner)

        owner_order = {
            Module: 0,
            Submodule: 1,
            RootQuestion: 2,
            SubQuestion: 3,
            RepeatSection: 4,
        }
        return sorted(
            owners.values(),
            key=lambda owner: (owner_order[owner.__class__], owner.id),
        )

    def _dependency_submodules(self, dependencies):
        available_submodule_ids = (
            set(self.all_submodule_ids) | self.selected_submodule_ids
        )
        related_ids = defaultdict(set)
        root_ids = set()
        subquestion_ids = set()
        repeat_ids = set()
        for dependency in dependencies:
            if dependency.root_question_id:
                root_ids.add(dependency.id)
            elif dependency.sub_question_id:
                subquestion_ids.add(dependency.id)
            elif dependency.repeat_section_id:
                repeat_ids.add(dependency.id)

        querysets = []
        if root_ids:
            querysets.append(
                RootQuestion.objects.filter(
                    base_question__id__in=root_ids,
                    submodule__id__in=available_submodule_ids,
                ).values_list("base_question__id", "submodule__id")
            )
        if subquestion_ids:
            querysets.append(
                SubQuestion.objects.filter(
                    base_question__id__in=subquestion_ids,
                    root_question__submodule__id__in=available_submodule_ids,
                ).values_list("base_question__id", "root_question__submodule__id")
            )
        if repeat_ids:
            querysets.append(
                RepeatSection.objects.filter(
                    base_question__id__in=repeat_ids,
                    submodule__id__in=available_submodule_ids,
                ).values_list("base_question__id", "submodule__id")
            )
        for queryset in querysets:
            for dependency_id, submodule_id in queryset:
                related_ids[dependency_id].add(submodule_id)

        submodules = Submodule.objects.in_bulk(
            set().union(*related_ids.values()) if related_ids else set()
        )
        return {
            dependency_id: [
                submodules[submodule_id]
                for submodule_id in sorted(submodule_ids)
                if submodule_id in submodules
            ]
            for dependency_id, submodule_ids in related_ids.items()
        }

    def _record_dependency_result(self, owner, dependency, related_submodules):
        for submodule in self.get_submodules():
            owns_expression = owner == submodule or owner == submodule.module
            owns_expression = owns_expression or owner in (
                *submodule.prefetched_root_questions,
                *submodule.prefetched_repeat_sections,
            )
            if not owns_expression:
                continue
            result = self.dependency_results.setdefault(
                submodule,
                {"related_submodules": set(), "dependencies": []},
            )
            result["related_submodules"].update(related_submodules)
            if dependency not in result["dependencies"]:
                result["dependencies"].append(dependency)

    @staticmethod
    def _dependency_description(dependency):
        instance = dependency.instance
        return f"{instance.__class__.__name__} #{instance.id}"

    def _dependency_issue(
        self, owner, field, referenced_name, code, detail, dependency
    ):
        owner_data = self._owner(owner)
        return ValidationIssue(
            code=code,
            layer="composition",
            severity="error",
            message=(
                f"{owner_data['model']} '{owner.name}' field '{field}' references "
                f"question '{referenced_name}', {detail}"
            ),
            owner=owner_data,
            submodule=self._affected_submodule(owner),
            dependency=dependency,
            field=field,
        )

    def validate_dependencies(self):
        owners = self._scope_expression_owners()
        references = []
        for owner in owners:
            for field in self._expression_fields(owner):
                for name in sorted(
                    expression_question_references(getattr(owner, field, "") or "")
                ):
                    references.append((owner, field, name))

        referenced_names = {name for _, _, name in references}
        dependencies = list(
            BaseQuestion.objects.filter(
                Q(root_question__name__in=referenced_names)
                | Q(sub_question__name__in=referenced_names)
                | Q(repeat_section__name__in=referenced_names)
            )
            .select_related("root_question", "sub_question", "repeat_section")
            .distinct()
        )
        dependencies_by_casefold = defaultdict(list)
        for dependency in dependencies:
            dependencies_by_casefold[dependency.name.casefold()].append(dependency)

        emitted_base_question_ids = {
            question.base_question.id
            for question in owners
            if isinstance(question, (RootQuestion, RepeatSection))
        }
        indicator_base_question_ids = {
            question.id for question in self.get_indicator_questions()
        }
        emitted_base_question_ids.update(indicator_base_question_ids)
        dependency_sources = {
            question.id: question
            for question in (*dependencies, *self.get_indicator_questions())
        }
        dependency_submodules = self._dependency_submodules(dependency_sources.values())
        for base_question in self.get_indicator_questions():
            owner = base_question.instance
            for submodule in dependency_submodules.get(base_question.id, []):
                self._add_owner_submodule(owner, submodule)
        available_dependency_ids = (
            set(dependency_submodules) | indicator_base_question_ids
        )

        self.dependency_issues = []
        self.dependency_results = {}
        for owner, field, referenced_name in references:
            casefold_matches = dependencies_by_casefold.get(
                referenced_name.casefold(), []
            )
            available_matches = [
                dependency
                for dependency in casefold_matches
                if dependency.id in available_dependency_ids
            ]
            matches = [
                dependency
                for dependency in available_matches
                if dependency.name == referenced_name
            ]

            if not matches:
                available_names = sorted(
                    {dependency.name for dependency in available_matches}
                )
                if available_names:
                    rendered_names = ", ".join(f"'{name}'" for name in available_names)
                    issue = self._dependency_issue(
                        owner,
                        field,
                        referenced_name,
                        "SELECTED_SCOPE_DEPENDENCY_CASE_MISMATCH",
                        "but references are case-sensitive; available exact name: "
                        f"{rendered_names}.",
                        {
                            "name": referenced_name,
                            "status": "case_mismatch",
                            "available_names": available_names,
                        },
                    )
                elif casefold_matches:
                    issue = self._dependency_issue(
                        owner,
                        field,
                        referenced_name,
                        "SELECTED_SCOPE_DEPENDENCY_UNAVAILABLE",
                        "but that question is unavailable in the current survey scope.",
                        {
                            "name": referenced_name,
                            "status": "unavailable",
                        },
                    )
                else:
                    issue = self._dependency_issue(
                        owner,
                        field,
                        referenced_name,
                        "SELECTED_SCOPE_DEPENDENCY_UNRESOLVED",
                        "but no question with that exact name exists.",
                        {
                            "name": referenced_name,
                            "status": "unresolved",
                        },
                    )
                self.dependency_issues.append(issue)
                continue

            if len(matches) > 1:
                descriptions = ", ".join(
                    self._dependency_description(dependency)
                    for dependency in sorted(
                        matches,
                        key=lambda dependency: (
                            dependency.instance.__class__.__name__,
                            dependency.instance.id,
                        ),
                    )
                )
                self.dependency_issues.append(
                    self._dependency_issue(
                        owner,
                        field,
                        referenced_name,
                        "SELECTED_SCOPE_DEPENDENCY_AMBIGUOUS",
                        f"but that name matches multiple questions: {descriptions}.",
                        {
                            "name": referenced_name,
                            "status": "ambiguous",
                            "candidates": [
                                self._owner(dependency.instance)
                                for dependency in sorted(
                                    matches,
                                    key=lambda dependency: (
                                        dependency.instance.__class__.__name__,
                                        dependency.instance.id,
                                    ),
                                )
                            ],
                        },
                    )
                )
                continue

            dependency = matches[0]
            if not dependency.instance.is_active:
                self.dependency_issues.append(
                    self._dependency_issue(
                        owner,
                        field,
                        referenced_name,
                        "SELECTED_SCOPE_DEPENDENCY_INVALID",
                        f"but the referenced {self._dependency_description(dependency)} is inactive.",
                        {
                            "name": referenced_name,
                            "status": "invalid",
                            "reason": "inactive",
                            "target": self._owner(dependency.instance),
                        },
                    )
                )
                continue

            if dependency.id in emitted_base_question_ids:
                continue

            # A subquestion can still be selected in Step 3 when its parent
            # submodule is already selected. Final-artifact validation remains
            # responsible for confirming that it was actually selected.
            if dependency.sub_question_id and any(
                submodule.id in self.selected_submodule_ids
                for submodule in dependency_submodules.get(dependency.id, [])
            ):
                continue

            related_submodules = sorted(
                {
                    submodule
                    for submodule in dependency_submodules.get(dependency.id, [])
                    if submodule.id not in self.selected_submodule_ids
                },
                key=lambda submodule: submodule.id,
            )
            owner_data = self._owner(owner)
            message = (
                f"{owner_data['model']} '{owner.name}' field '{field}' references "
                f"question '{referenced_name}', but it is not emitted by the selected survey."
            )
            if related_submodules:
                labels = ", ".join(submodule.label for submodule in related_submodules)
                message += f" Select one of these submodules: {labels}."
            self._record_dependency_result(owner, dependency, related_submodules)

            self.dependency_issues.append(
                ValidationIssue(
                    code="SELECTED_SCOPE_DEPENDENCY_NOT_EMITTED",
                    layer="composition",
                    severity="error",
                    message=message,
                    owner=owner_data,
                    submodule=self._affected_submodule(owner),
                    dependency={
                        "name": referenced_name,
                        "status": "not_emitted",
                        "target": self._owner(dependency.instance),
                        "available_submodules": [
                            self._submodule(submodule)
                            for submodule in related_submodules
                        ],
                    },
                    field=field,
                )
            )

        return self.dependency_results

    def validate(self):
        self.validate_compatibility()
        self.validate_dependencies()
        return self.get_issues()
