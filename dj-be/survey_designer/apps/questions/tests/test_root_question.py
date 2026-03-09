import pytest
from django.test import TestCase
from modules.models import Module, Submodule
from organization.models import Organization
from questions.const import QuestionType
from questions.models import RootQuestion, SubQuestion, Suffix


def test_root_question_duplication(
    root_question_1, sub_question_1, sub_question_2, sub_question_4
):
    assert root_question_1.duplicate()


@pytest.mark.django_db
def test_root_question_duplication_counts_case_variant_existing_names(
    root_question_1, submodule_1, sub_question_1, sub_question_2, sub_question_4
):
    original_name = root_question_1.name
    existing_case_variant = RootQuestion.objects.create(
        name=f"{original_name.lower()}_legacy",
        label="Legacy variant",
        type=QuestionType.INTEGER,
        appearance="test",
    )
    existing_case_variant.submodule.add(submodule_1)

    duplicate = root_question_1.duplicate()

    assert duplicate.name == f"{original_name}_2"
    assert RootQuestion.objects.filter(name=original_name).count() == 1
    assert RootQuestion.objects.filter(name=f"{original_name}_2").count() == 1


class TestCaseInsensitiveRootQuestionDuplication(TestCase):
    def setUp(self):
        organization = Organization.objects.create(name="Duplication Org")
        module = Module.objects.create(name="TestModule", label="Test Module")
        module.organizations.add(organization)
        self.submodule = Submodule.objects.create(
            name="TestSubmodule",
            label="Test Submodule",
            module=module,
            appearance="test",
        )
        self.root_question = RootQuestion.objects.create(
            name="TestQuestion1",
            label="Test Question 1",
            type=QuestionType.INTEGER,
            appearance="test",
        )
        self.root_question.submodule.add(self.submodule)
        self.suffix = Suffix.objects.create(
            name="Suffix1",
            description="Suffix 1",
            type=QuestionType.TEXT,
        )
        SubQuestion.objects.create(
            root_question=self.root_question,
            suffix=self.suffix,
            label="SubQuestion 1",
        )

    def test_duplication_counts_case_variant_existing_names(self):
        original_name = self.root_question.name
        existing_case_variant = RootQuestion.objects.create(
            name=f"{original_name.lower()}_legacy",
            label="Legacy variant",
            type=QuestionType.INTEGER,
            appearance="test",
        )
        existing_case_variant.submodule.add(self.submodule)

        duplicate = self.root_question.duplicate()

        self.assertEqual(duplicate.name, f"{original_name}_2")
        self.assertEqual(RootQuestion.objects.filter(name=original_name).count(), 1)
        self.assertEqual(
            RootQuestion.objects.filter(name=f"{original_name}_2").count(), 1
        )
