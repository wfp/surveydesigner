from collections import defaultdict
from itertools import chain

from django.db.models import Prefetch
from modules.models import Indicator, Submodule
from questions.models import BaseQuestion, RepeatSection, RootQuestion


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
        self._submodules = None
        self._available_submodules_by_root_question = None
        self._indicator_root_question_ids = None

    def get_root_question_queryset(self):
        dependency_queryset = BaseQuestion.objects.select_related("root_question")
        return RootQuestion.objects.prefetch_related(
            Prefetch(
                "relevant_dependencies",
                queryset=dependency_queryset,
                to_attr="prefetched_relevant_dependencies",
            ),
            Prefetch(
                "constraint_dependencies",
                queryset=dependency_queryset,
                to_attr="prefetched_constraint_dependencies",
            ),
            Prefetch(
                "calculation_dependencies",
                queryset=dependency_queryset,
                to_attr="prefetched_calculation_dependencies",
            ),
        )

    def get_submodules(self):
        if self._submodules is None:
            submodules = list(
                Submodule.objects.filter(id__in=self.submodule_ids).prefetch_related(
                    Prefetch(
                        "root_questions",
                        queryset=self.get_root_question_queryset(),
                        to_attr="prefetched_root_questions",
                    ),
                    Prefetch(
                        "repeat_sections",
                        queryset=RepeatSection.objects.only("id"),
                        to_attr="prefetched_repeat_sections",
                    ),
                )
            )
            submodules.sort(key=lambda submodule: self.submodule_order[submodule.id])
            self._submodules = submodules
        return self._submodules

    def get_available_submodules_by_root_question(self):
        if self._available_submodules_by_root_question is None:
            related_submodules = defaultdict(set)
            all_submodules = Submodule.objects.filter(
                id__in=self.all_submodule_ids
            ).exclude(id__in=self.submodule_ids).prefetch_related(
                Prefetch(
                    "root_questions",
                    queryset=RootQuestion.objects.only("id"),
                    to_attr="prefetched_root_questions",
                )
            )
            for submodule in all_submodules:
                for question in submodule.prefetched_root_questions:
                    related_submodules[question.id].add(submodule)
            self._available_submodules_by_root_question = related_submodules
        return self._available_submodules_by_root_question

    def get_indicator_root_question_ids(self):
        if self._indicator_root_question_ids is None:
            self._indicator_root_question_ids = {
                root_question_id
                for root_question_id in Indicator.objects.filter(
                    id__in=self.indicator_ids
                ).values_list("questions__root_question", flat=True)
                if root_question_id is not None
            }
        return self._indicator_root_question_ids

    def get_messages(self):
        messages = []
        if self.dependent_submodules_result:
            for (
                submodule,
                dependent_submodules,
            ) in self.dependent_submodules_result.items():
                dependent_labels = [sm.label for sm in dependent_submodules]
                messages.append(
                    f"{submodule.label} contains questions from: {', '.join(dependent_labels)}. Select only one of these submodules."
                )
        if self.dependencies_result:
            for submodule, dependent_submodules in self.dependencies_result.items():
                related_submodules = dependent_submodules["related_submodules"]
                dependencies = dependent_submodules["dependencies"]
                related_submodules_labels = ", ".join(
                    [sm.label for sm in related_submodules]
                )
                dependencies_labels = ", ".join([sm.name for sm in dependencies])
                submodule_text = (
                    "submodule" if len(related_submodules) == 1 else "submodules"
                )
                question_text = "question" if len(dependencies) == 1 else "questions"
                messages.append(
                    f"The {submodule.label} submodule cannot be previewed if the {dependencies_labels} {question_text} in the {related_submodules_labels} {submodule_text} is not integrated"
                )
        return messages

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

    def process_relevant_dependencies(self):
        indicator_root_question_ids = self.get_indicator_root_question_ids()
        available_submodules_by_root_question = (
            self.get_available_submodules_by_root_question()
        )

        for submodule in self.get_submodules():
            submodule_root_question_ids = {
                question.id for question in submodule.prefetched_root_questions
            }
            all_related_submodules = set()
            all_dependencies = {}

            for question in submodule.prefetched_root_questions:
                question_related_submodules = set()
                question_dependencies = []

                for dependency in chain(
                    question.prefetched_relevant_dependencies,
                    question.prefetched_constraint_dependencies,
                    question.prefetched_calculation_dependencies,
                ):
                    dependency_root_question_id = dependency.root_question_id

                    if dependency.id == question.id:
                        continue
                    if dependency_root_question_id in submodule_root_question_ids:
                        continue
                    if dependency_root_question_id in indicator_root_question_ids:
                        continue

                    question_dependencies.append(dependency)
                    if dependency_root_question_id is not None:
                        question_related_submodules.update(
                            available_submodules_by_root_question.get(
                                dependency_root_question_id, set()
                            )
                        )

                if question_related_submodules:
                    all_related_submodules.update(question_related_submodules)
                    for dependency in question_dependencies:
                        all_dependencies.setdefault(dependency.id, dependency)

            if all_related_submodules:
                self.dependencies_result[submodule] = {
                    "related_submodules": all_related_submodules,
                    "dependencies": list(all_dependencies.values()),
                }
        return self.dependencies_result

    def process(self):
        self.process_dependent_submodules()
        self.process_relevant_dependencies()
