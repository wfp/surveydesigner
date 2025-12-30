import factory
from modules.models import Submodule
from questions.models import RootQuestion, SubQuestion


class SubQuestionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SubQuestion


class RootQuestionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RootQuestion

    @factory.post_generation
    def submodules(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            assert isinstance(extracted, list)
            for submodule_data in extracted:
                submodule = Submodule.objects.filter(
                    id=submodule_data.get("submodule_id"),
                ).first()
                if submodule:
                    self.submodule.add(submodule)

    @factory.post_generation
    def sub_questions(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            assert isinstance(extracted, list)
            for sub_question_data in extracted:
                SubQuestionFactory.create(
                    root_question_id=self.id,
                    suffix_id=sub_question_data.get("suffix_id"),
                    suffix_2_id=sub_question_data.get("suffix_2_id"),
                    recall_period_id=sub_question_data.get("recall_period_id"),
                    label=sub_question_data.get("label", ""),
                )
