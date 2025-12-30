from django.db.models import Prefetch, Q
from modules.models import Indicator, Submodule
from questions.models import RepeatSection, RootQuestion


class SubmodulesOrderValidator:
    def __init__(self, submodule_ids, indicator_ids, all_submodule_ids):
        self.submodule_ids = submodule_ids
        self.indicator_ids = indicator_ids
        self.all_submodule_ids = all_submodule_ids
        self.dependent_submodules_result = {}
        self.dependencies_result = {}

    def get_submodules(self):
        return sorted(
            Submodule.objects.filter(id__in=self.submodule_ids),
            key=lambda submodule: self.submodule_ids.index(submodule.id),
        )

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
        processed_submodules = set()
        for submodule in self.get_submodules():
            next_submodules = set(self.get_next_submodules(submodule))
            intersection = next_submodules.intersection(processed_submodules)
            if intersection:
                self.dependent_submodules_result[submodule] = intersection

            processed_submodules.add(submodule)

        return self.dependent_submodules_result

    def process_relevant_dependencies(self):
        submodules = Submodule.objects.filter(
            id__in=self.submodule_ids
        ).prefetch_related(
            Prefetch(
                "root_questions",
                queryset=RootQuestion.objects.prefetch_related(
                    "relevant_dependencies__root_question__submodule",
                    "constraint_dependencies__root_question__submodule",
                    "calculation_dependencies__root_question__submodule",
                ),
            )
        )
        indicator_root_question_ids = [
            ind
            for ind in Indicator.objects.filter(id__in=self.indicator_ids).values_list(
                "questions__root_question", flat=True
            )
            if ind is not None
        ]
        all_submodules = Submodule.objects.filter(id__in=self.all_submodule_ids)
        for submodule in submodules:
            all_related_submodules = set()
            all_dependencies = RootQuestion.objects.none()  # empty queryset
            for question in submodule.root_questions.all():
                # filter out questions and dependencies that exist in the submodule already
                relevant_dependencies = question.relevant_dependencies.all().exclude(
                    Q(id=question.id)
                    | Q(root_question__submodule=submodule)
                    | Q(root_question__id__in=indicator_root_question_ids)
                )
                constraint_dependencies = (
                    question.constraint_dependencies.all().exclude(
                        Q(id=question.id)
                        | Q(root_question__submodule=submodule)
                        | Q(root_question__id__in=indicator_root_question_ids)
                    )
                )
                calculation_dependencies = (
                    question.calculation_dependencies.all().exclude(
                        Q(id=question.id)
                        | Q(root_question__submodule=submodule)
                        | Q(root_question__id__in=indicator_root_question_ids)
                    )
                )
                dependencies = relevant_dependencies.union(
                    constraint_dependencies, calculation_dependencies
                )
                related_submodules = set(
                    all_submodules.filter(
                        Q(
                            root_questions__in=dependencies.values_list(
                                "root_question__id", flat=True
                            )
                        )
                    ).exclude(id__in=self.submodule_ids)
                )
                if related_submodules:
                    all_related_submodules.update(related_submodules)
                    all_dependencies = all_dependencies.union(dependencies)

            if all_related_submodules:
                self.dependencies_result[submodule] = {
                    "related_submodules": all_related_submodules,
                    "dependencies": all_dependencies,
                }
        return self.dependencies_result

    def process(self):
        self.process_dependent_submodules()
        self.process_relevant_dependencies()

    def get_next_submodules(self, submodule):
        id_ = submodule.id
        ids = list(self.submodule_ids)
        ids.remove(id_)

        # Get RootQuestion and RepeatSection IDs related to the Submodule
        root_question_ids = RootQuestion.objects.filter(
            submodule=submodule
        ).values_list("id", flat=True)
        repeat_section_ids = RepeatSection.objects.filter(
            submodule=submodule
        ).values_list("id", flat=True)

        return Submodule.objects.filter(
            Q(root_questions__id__in=root_question_ids)
            | Q(repeat_sections__id__in=repeat_section_ids),
            id__in=ids,
        ).distinct()
