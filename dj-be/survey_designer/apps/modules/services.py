from collections import defaultdict

from django.db.models import Prefetch, Q
from modules.models import Indicator, Module, Submodule
from questions.models import BaseQuestion, RepeatSection, RootQuestion, SubQuestion
from questions.services.form_validation import (
    ValidationIssue,
    expression_question_references,
)


class SubmodulesOrderValidator:
    def __init__(self, submodule_ids, indicator_ids, all_submodule_ids):
        self.submodule_ids = [int(id_) for id_ in submodule_ids]
        self.indicator_ids = [int(id_) for id_ in indicator_ids]
        self.all_submodule_ids = [int(id_) for id_ in all_submodule_ids]
        self.selected_submodule_ids = set(self.submodule_ids)
        self.submodule_order = {
            submodule_id: index for index, submodule_id in enumerate(self.submodule_ids)
        }
        self.dependent_submodules_result = {}
        self.dependencies_result = {}
        self.scope_issues = []
        self._submodules = None
        self._scope_submodules = None
        self._indicator_questions = None

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
            self.dependent_submodules_result.items(), key=lambda item: item[0].id
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
                    owner={
                        "model": "Submodule",
                        "id": submodule.id,
                        "name": submodule.name,
                    },
                    field="submodules",
                )
            )
        issues.extend(self.scope_issues)
        return issues

    def process_dependent_submodules(self):
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
                self.dependent_submodules_result[submodule] = intersection

            processed_submodules.add(submodule)

        return self.dependent_submodules_result

    @staticmethod
    def _expression_fields(owner):
        if isinstance(owner, (Module, Submodule)):
            return ("relevant",)
        if isinstance(owner, RootQuestion):
            return ("relevant", "constraint", "calculation", "choice_filter")
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

    def _scope_expression_owners(self):
        owners = {}

        def add(owner):
            owners[(owner.__class__, owner.id)] = owner

        for submodule in self.get_scope_submodules():
            add(submodule.module)
            add(submodule)
        for submodule in self.get_submodules():
            for question in submodule.prefetched_root_questions:
                add(question)
            for repeat_section in submodule.prefetched_repeat_sections:
                add(repeat_section)
        for base_question in self.get_indicator_questions():
            owner = base_question.instance
            if isinstance(owner, (RootQuestion, RepeatSection)):
                add(owner)

        owner_order = {
            Module: 0,
            Submodule: 1,
            RootQuestion: 2,
            RepeatSection: 3,
        }
        return sorted(
            owners.values(),
            key=lambda owner: (owner_order[owner.__class__], owner.id),
        )

    def _dependency_submodules(self, dependencies):
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
                    submodule__id__in=self.all_submodule_ids,
                ).values_list("base_question__id", "submodule__id")
            )
        if subquestion_ids:
            querysets.append(
                SubQuestion.objects.filter(
                    base_question__id__in=subquestion_ids,
                    root_question__submodule__id__in=self.all_submodule_ids,
                ).values_list("base_question__id", "root_question__submodule__id")
            )
        if repeat_ids:
            querysets.append(
                RepeatSection.objects.filter(
                    base_question__id__in=repeat_ids,
                    submodule__id__in=self.all_submodule_ids,
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
            result = self.dependencies_result.setdefault(
                submodule,
                {"related_submodules": set(), "dependencies": []},
            )
            result["related_submodules"].update(related_submodules)
            if dependency not in result["dependencies"]:
                result["dependencies"].append(dependency)

    def process_relevant_dependencies(self):
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
        exact_dependencies = defaultdict(list)
        for dependency in dependencies:
            exact_dependencies[dependency.name].append(dependency)

        emitted_base_question_ids = {
            question.base_question.id
            for question in owners
            if isinstance(question, (RootQuestion, RepeatSection))
        }
        dependency_submodules = self._dependency_submodules(dependencies)

        self.scope_issues = []
        self.dependencies_result = {}
        for owner, field, referenced_name in references:
            matches = exact_dependencies.get(referenced_name, [])
            if any(
                dependency.id in emitted_base_question_ids for dependency in matches
            ):
                continue

            # A subquestion can still be selected in Step 3 when its parent
            # submodule is already selected. Final-artifact validation remains
            # responsible for confirming that it was actually selected.
            if any(
                dependency.sub_question_id
                and any(
                    submodule.id in self.selected_submodule_ids
                    for submodule in dependency_submodules.get(dependency.id, [])
                )
                for dependency in matches
            ):
                continue

            related_submodules = sorted(
                {
                    submodule
                    for dependency in matches
                    for submodule in dependency_submodules.get(dependency.id, [])
                    if submodule.id not in self.selected_submodule_ids
                },
                key=lambda submodule: submodule.id,
            )
            owner_data = self._owner(owner)
            if matches:
                message = (
                    f"{owner_data['model']} '{owner.name}' field '{field}' references "
                    f"question '{referenced_name}', but it is not emitted by the selected survey."
                )
                if related_submodules:
                    labels = ", ".join(
                        submodule.label for submodule in related_submodules
                    )
                    message += f" Select one of these submodules: {labels}."
                code = "SELECTED_SCOPE_DEPENDENCY_NOT_EMITTED"
                for dependency in matches:
                    self._record_dependency_result(
                        owner, dependency, related_submodules
                    )
            else:
                message = (
                    f"{owner_data['model']} '{owner.name}' field '{field}' references "
                    f"question '{referenced_name}', but no exact question with that name exists."
                )
                code = "SELECTED_SCOPE_DEPENDENCY_UNRESOLVED"

            self.scope_issues.append(
                ValidationIssue(
                    code=code,
                    layer="composition",
                    severity="error",
                    message=message,
                    owner=owner_data,
                    field=field,
                )
            )

        return self.dependencies_result

    def process(self):
        self.process_dependent_submodules()
        self.process_relevant_dependencies()
