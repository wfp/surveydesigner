import uuid

from core.models import TimestampMixin
from django.core.exceptions import ValidationError
from django.db import models


class SavedSurvey(TimestampMixin):
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey("accounts.User", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    organizations = models.ManyToManyField(
        "organization.Organization", related_name="saved_surveys", blank=True
    )
    survey_category = models.ForeignKey(
        "surveys.SurveyCategory",
        related_name="saved_surveys",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    survey_type = models.ForeignKey(
        "surveys.SurveyType",
        related_name="saved_surveys",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    survey_mode = models.ForeignKey(
        "surveys.SurveyMode",
        related_name="saved_surveys",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    indicators = models.ManyToManyField(
        "modules.Indicator", related_name="saved_surveys", blank=True
    )
    submodules = models.ManyToManyField(
        "modules.Submodule", related_name="saved_surveys"
    )
    attributes = models.ManyToManyField(
        "surveys.SurveyAttribute", related_name="saved_surveys", blank=True
    )
    languages = models.JSONField(
        null=True, blank=True, help_text="Select multiple languages"
    )

    def clean_survey_category(self):
        if (
            self.survey_category
            and self.survey_category.organizations != self.organizations
        ):
            raise ValidationError(
                "Survey category must belong to the same organization as the saved survey."
            )

    def clean_survey_type(self):
        if self.survey_type and self.survey_type.category != self.survey_category:
            raise ValidationError(
                "Survey type must belong to the same category as the saved survey."
            )

    def clean_survey_mode(self):
        if self.survey_mode and self.survey_mode.organizations != self.organizations:
            raise ValidationError(
                "Survey mode must belong to the same organization as the saved survey."
            )

    def clean_attributes(self):
        for attribute in self.attributes.all():
            if attribute not in self.survey_type.attributes.all():
                raise ValidationError(
                    "Attribute must belong to the same type as the saved survey."
                )

    def clean(self):
        self.clean_survey_category()
        self.clean_survey_type()
        self.clean_survey_mode()
        self.clean_attributes()

    def __str__(self):
        return self.name


class SubQuestionSubmodule(models.Model):
    saved_survey = models.ForeignKey(
        "saved_surveys.SavedSurvey",
        related_name="subquestions_submodules",
        on_delete=models.CASCADE,
    )
    subquestion = models.ForeignKey(
        "questions.Subquestion", related_name="submodules", on_delete=models.CASCADE
    )
    submodule = models.ForeignKey(
        "modules.Submodule", related_name="subquestions", on_delete=models.CASCADE
    )


class SubModuleOrder(models.Model):
    saved_survey = models.ForeignKey(
        "saved_surveys.SavedSurvey",
        related_name="submodule_orders",
        on_delete=models.CASCADE,
    )
    submodule = models.ForeignKey("modules.Submodule", on_delete=models.CASCADE)
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ["order"]
        unique_together = ["saved_survey", "submodule"]
