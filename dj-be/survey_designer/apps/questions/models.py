import os
import re

from core.models import (
    BaseTranslationMixin,
    BaseWFPModelMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UserTrackingMixin,
)
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.functional import cached_property

from .const import QuestionType
from .managers import BaseQuestionQuerySet


class QuestionFieldsMixin(models.Model):
    """
    Contains fields common to both root and sub questions.
    """

    hint = models.TextField("Hint (en)", blank=True)
    relevant = models.TextField(blank=True)
    constraint = models.TextField(blank=True)
    constraint_message = models.TextField("Constraint Message (en)", blank=True)
    appearance = models.CharField(blank=True, max_length=255)
    required = models.TextField(blank=True)
    parameters = models.TextField(blank=True)
    disabled = models.TextField(blank=True)
    read_only = models.TextField(blank=True)
    default = models.TextField(blank=True)
    choice_filter = models.TextField(blank=True)
    calculation = models.TextField(blank=True)

    class Meta:
        abstract = True


# Questions:


class BaseQuestion(models.Model):
    root_question = models.OneToOneField(
        "questions.RootQuestion",
        related_name="base_question",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    sub_question = models.OneToOneField(
        "questions.SubQuestion",
        related_name="base_question",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    repeat_section = models.OneToOneField(
        "questions.RepeatSection",
        related_name="base_question",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    order = models.PositiveIntegerField(default=0, blank=False, null=False)

    objects = BaseQuestionQuerySet.as_manager()

    class Meta:
        verbose_name = "Question"
        permissions = [("can_bulk_upload", "Can bulk upload")]
        ordering = ("-order",)
        indexes = [models.Index(fields=["order"])]

    def __str__(self):
        return self.instance.name

    @cached_property
    def instance(self):
        return self.root_question or self.sub_question or self.repeat_section

    @cached_property
    def real_root_question(self):
        return self.root_question or (
            self.sub_question.root_question if self.sub_question else None
        )

    @cached_property
    def name(self):
        return self.instance.name

    @cached_property
    def constraint(self):
        return (
            self.instance.constraint
            if not isinstance(self.instance, RepeatSection)
            else None
        )

    @cached_property
    def type(self):
        return (
            self.instance.type if not isinstance(self.instance, RepeatSection) else None
        )

    def get_type_display(self):
        return self.instance.get_type_display()

    @cached_property
    def description(self):
        return self.instance.description

    @staticmethod
    def get_question_names(formula: str):
        return re.findall(r"\$\{(.+?)\}", formula)

    @classmethod
    def get_base_questions(cls, names: list):
        return cls.objects.filter_by_names(names)

    def set_instance_constraint_dependencies(self, base_questions):
        self.instance.constraint_dependencies.set(
            question.id for question in base_questions
        )

    def set_instance_relevant_dependencies(self, base_questions):
        self.instance.relevant_dependencies.set(
            question.id for question in base_questions
        )


class RootQuestion(BaseWFPModelMixin, QuestionFieldsMixin):
    submodule = models.ManyToManyField(
        "modules.Submodule",
        related_name="root_questions",
    )
    type = models.CharField(max_length=255, choices=QuestionType.choices)
    choices = models.ForeignKey(
        "ChoiceGroup",
        related_name="root_questions",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    choices_file = models.ForeignKey(
        "ChoiceGroupFile",
        related_name="root_questions",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    relevant_dependencies = models.ManyToManyField(
        BaseQuestion, related_name="root_question_relevant_dependencies", blank=True
    )
    constraint_dependencies = models.ManyToManyField(
        BaseQuestion, related_name="root_question_constraint_dependencies", blank=True
    )
    choice_filter_dependencies = models.ManyToManyField(
        BaseQuestion,
        related_name="root_question_choice_filter_dependencies",
        blank=True,
    )
    calculation_dependencies = models.ManyToManyField(
        BaseQuestion, related_name="root_question_calculation_dependencies", blank=True
    )

    class Meta:
        verbose_name = "Root Question"
        ordering = ("base_question__order",)
        indexes = [models.Index(fields=["type"])]

    def clean(self):
        if self.type in (
            QuestionType.SELECT_ONE_FROM_FILE,
            QuestionType.SELECT_MULTIPLE_FROM_FILE,
        ):
            if not self.choices_file:
                raise ValidationError(
                    f"choices_file is required for question type '{self.type}'."
                )
            if self.choices:
                raise ValidationError(
                    "Cannot set both 'choices' and 'choices_file'. Use 'choices_file' for file-based question types."
                )
        elif self.type in (QuestionType.SELECT_ONE, QuestionType.SELECT_MULTIPLE):
            if not self.choices:
                raise ValidationError(
                    f"choices is required for question type '{self.type}'."
                )
            if self.choices_file:
                raise ValidationError(
                    "Cannot set both 'choices' and 'choices_file'. Use 'choices' for regular question types."
                )
        super().clean()

    def get_xls_type(self):
        if (
            self.type in (QuestionType.SELECT_ONE, QuestionType.SELECT_MULTIPLE)
            and self.choices
        ):
            return f"{self.type} {self.choices.name}"
        elif self.type in (
            QuestionType.SELECT_ONE_FROM_FILE,
            QuestionType.SELECT_MULTIPLE_FROM_FILE,
        ):
            if self.choices_file and self.choices_file.csv_file:
                filename = os.path.basename(self.choices_file.csv_file.name)
                return f"{self.type} {filename}"
        return self.type

    def duplicate(self):
        prefix = self.name.casefold()
        duplicates_count = sum(
            1
            for existing_name in RootQuestion.objects.values_list("name", flat=True)
            if existing_name.casefold().startswith(prefix)
        )

        translations = self.translations.all()
        sub_questions = self.sub_questions.all()

        new_question = self
        new_question.id = None
        new_question.name = f"{new_question.name}_{duplicates_count}"
        new_question.save()

        for translation in translations:
            translation.id = None
            translation.root_question = new_question
            translation.save()

        for sub_question in sub_questions:
            sub_question_translations = sub_question.translations.all()
            new_sub_question = sub_question
            new_sub_question.id = None
            new_sub_question.root_question = new_question
            new_sub_question.save()

            for sub_question_translation in sub_question_translations:
                sub_question_translation.id = None
                sub_question_translation.sub_question = new_sub_question
                sub_question_translation.save()

        return new_question


class SubQuestion(BaseWFPModelMixin, QuestionFieldsMixin):
    root_question = models.ForeignKey(
        RootQuestion, related_name="sub_questions", on_delete=models.CASCADE
    )
    suffix = models.ForeignKey(
        "questions.Suffix",
        related_name="sub_questions",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    suffix_2 = models.ForeignKey(
        "questions.Suffix",
        related_name="sub_questions_as_second",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    recall_period = models.ForeignKey(
        "questions.RecallPeriod",
        related_name="sub_questions",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    relevant_dependencies = models.ManyToManyField(
        BaseQuestion, related_name="sub_question_relevant_dependencies", blank=True
    )
    constraint_dependencies = models.ManyToManyField(
        BaseQuestion, related_name="sub_question_constraint_dependencies", blank=True
    )
    choice_filter_dependencies = models.ManyToManyField(
        BaseQuestion, related_name="sub_question_choice_filter_dependencies", blank=True
    )
    calculation_dependencies = models.ManyToManyField(
        BaseQuestion, related_name="sub_question_calculation_dependencies", blank=True
    )

    class Meta:
        ordering = ("base_question__order",)
        unique_together = ["root_question", "suffix", "suffix_2", "recall_period"]
        verbose_name = "Question"

    def save(self, *args, **kwargs):
        self.name = self.build_name()
        super().save(*args, **kwargs)

    def build_name(self):
        suffix_name = self.suffix.name if self.suffix_id else ""
        suffix_2_name = self.suffix_2.name if self.suffix_2_id else ""
        recall_period_name = self.recall_period.name if self.recall_period_id else ""
        return (
            f"{self.root_question.name}{suffix_name}{suffix_2_name}{recall_period_name}"
        )

    @property
    def type(self):
        if self.suffix_2:
            return self.suffix_2.type
        if self.suffix:
            return self.suffix.type
        return self.root_question.type

    @cached_property
    def choices(self):
        if self.suffix_2:
            if self.suffix_2.choices_file:
                return self.suffix_2.choices_file
            return self.suffix_2.choices
        if self.suffix:
            if self.suffix.choices_file:
                return self.suffix.choices_file
            return self.suffix.choices
        if self.root_question.choices_file:
            return self.root_question.choices_file
        return self.root_question.choices

    def get_type_display(self):
        if self.suffix_2:
            return self.suffix_2.get_type_display()
        if self.suffix:
            return self.suffix.get_type_display()
        return self.root_question.get_type_display()

    def get_xls_type(self):
        if (
            self.type in (QuestionType.SELECT_ONE, QuestionType.SELECT_MULTIPLE)
            and self.choices
        ):
            return f"{self.type} {self.choices.name}"
        elif self.type in (
            QuestionType.SELECT_ONE_FROM_FILE,
            QuestionType.SELECT_MULTIPLE_FROM_FILE,
        ):
            if (
                self.choices
                and hasattr(self.choices, "csv_file")
                and self.choices.csv_file
            ):
                filename = os.path.basename(self.choices.csv_file.name)
                return f"{self.type} {filename}"
        return self.type


class SubQuestionProxy(SubQuestion):
    class Meta:
        proxy = True
        verbose_name = "Sub Question"


class RecallPeriod(BaseWFPModelMixin):
    label = ""  # override BaseWFPModelMixin label field
    description_markdown = models.TextField(blank=True)


class Suffix(BaseWFPModelMixin):
    label = ""  # override BaseWFPModelMixin label field
    type = models.CharField(max_length=255, choices=QuestionType.choices)
    choices = models.ForeignKey(
        "ChoiceGroup",
        related_name="suffixes",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    choices_file = models.ForeignKey(
        "ChoiceGroupFile",
        related_name="suffixes",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    nested_suffixes = models.ManyToManyField(
        "self", symmetrical=False, related_name="parent_suffixes", blank=True
    )

    class Meta:
        verbose_name_plural = "Suffixes"
        indexes = [models.Index(fields=["type"])]


class NestedSuffix(Suffix):
    class Meta:
        proxy = True
        verbose_name_plural = "Nested Suffixes"


class ChoiceGroup(BaseWFPModelMixin):
    label = ""  # override BaseWFPModelMixin label field
    description_markdown = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    choice_filter_list = models.ForeignKey(
        "self",
        related_name="choice_filter_lists",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Choice list"

    def clean(self):
        if self.choice_filter_list == self:
            raise ValidationError(
                "A ChoiceGroup cannot select itself as its choice_filter_list."
            )
        super().clean()


class ChoiceGroupFile(BaseWFPModelMixin):
    label = ""
    csv_file = models.FileField(upload_to="choice_lists/")
    description_markdown = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Choice list with external file"

    def clean(self):

        if self.csv_file:
            filename = os.path.basename(self.csv_file.name)

            if hasattr(self.csv_file, "size"):
                max_size = 10 * 1024 * 1024
                if self.csv_file.size > max_size:
                    raise ValidationError(
                        f"File size exceeds the maximum allowed size of 10MB. Current file size: {self.csv_file.size / (1024 * 1024):.2f}MB"
                    )

            existing = ChoiceGroupFile.objects.exclude(pk=self.pk if self.pk else None)
            for existing_file in existing:
                if existing_file.csv_file:
                    existing_filename = os.path.basename(existing_file.csv_file.name)
                    if existing_filename.lower() == filename.lower():
                        raise ValidationError(
                            f"A ChoiceGroupFile with the CSV filename '{filename}' already exists."
                        )
        super().clean()

    def save(self, *args, **kwargs):
        if hasattr(self, "_request_user") and self._request_user:
            self.updated_by = self._request_user
        super().save(*args, **kwargs)


class Choice(UserTrackingMixin, TimestampMixin, SoftDeleteMixin):
    choice_group = models.ForeignKey(
        ChoiceGroup, related_name="choices", on_delete=models.CASCADE
    )
    name = models.CharField(
        "Option Code",
        max_length=255,
    )
    label = models.TextField()
    choice_filter_name = models.ForeignKey(
        "self",
        related_name="choice_filter_names",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Select a choice filter. Displayed as 'option_code': 'label' for the choice.",
    )
    order = models.PositiveIntegerField(default=0, blank=False, null=False)

    class Meta:
        ordering = (
            "order",
            "id",
        )
        unique_together = ["choice_group", "name"]

    def __str__(self):
        return f"{self.name}: {self.label}"


class Calculation(BaseWFPModelMixin):
    # submodule = models.ForeignKey(
    #     "modules.Submodule", related_name="calculations", on_delete=models.CASCADE
    # )
    calculation = models.TextField()
    related_questions = models.ManyToManyField(
        BaseQuestion, related_name="calculations", blank=True
    )

    @staticmethod
    def get_question_names(calculation: str):
        return re.findall(r"\$\{(.+?)\}", calculation)

    @staticmethod
    def get_base_questions(names: list):
        return BaseQuestion.objects.filter_by_names(names)

    def set_related_questions(self):
        names = self.get_question_names(self.calculation)
        questions = self.get_base_questions(names)
        self.related_questions.set(question.id for question in questions)


class RepeatSection(BaseWFPModelMixin):
    submodule = models.ManyToManyField(
        "modules.Submodule",
        related_name="repeat_sections",
    )
    questions = models.ManyToManyField(
        BaseQuestion,
        related_name="repeat_sections",
    )
    repeat_count = models.TextField()
    repeat_count_dependencies = models.ManyToManyField(
        BaseQuestion, related_name="repeat_count_dependencies", blank=True
    )
    relevant = models.TextField(blank=True)
    relevant_dependencies = models.ManyToManyField(
        BaseQuestion, related_name="repeat_section_relevant_dependencies", blank=True
    )

    @staticmethod
    def get_question_names(calculation: str):
        return re.findall(r"\$\{(.+?)\}", calculation)

    @staticmethod
    def get_base_questions(names: list):
        return BaseQuestion.objects.filter_by_names(names)

    def set_repeat_count_dependencies(self):
        names = self.get_question_names(self.repeat_count)
        questions = self.get_base_questions(names)
        self.repeat_count_dependencies.set(question.id for question in questions)


# Translations:


class RootQuestionTranslation(BaseTranslationMixin):
    root_question = models.ForeignKey(
        RootQuestion, related_name="translations", on_delete=models.CASCADE
    )
    hint = models.TextField(blank=True)

    class Meta:
        unique_together = ["root_question", "language"]


class SubQuestionTranslation(BaseTranslationMixin):
    sub_question = models.ForeignKey(
        SubQuestion, related_name="translations", on_delete=models.CASCADE
    )
    hint = models.TextField(blank=True)

    class Meta:
        unique_together = ["sub_question", "language"]


class ChoiceTranslation(BaseTranslationMixin):
    choice = models.ForeignKey(
        Choice, related_name="translations", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ["choice", "language"]


class RootQuestionConstraintMessageTranslation(BaseTranslationMixin):
    root_question = models.ForeignKey(
        RootQuestion, related_name="constraint_translations", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ["root_question", "language"]


class SubQuestionConstraintMessageTranslation(BaseTranslationMixin):
    sub_question = models.ForeignKey(
        SubQuestion, related_name="constraint_translations", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ["sub_question", "language"]


class RepeatSectionTranslation(BaseTranslationMixin):
    repeat_section = models.ForeignKey(
        RepeatSection, related_name="translations", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ["repeat_section", "language"]
