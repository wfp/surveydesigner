from core.models import BaseTranslationMixin, BaseWFPModelMixin, OrganizationsModelMixin
from django.conf import settings
from django.db import models
from surveys.managers import (
    SurveyAttributeQuerySet,
    SurveyCategoryQuerySet,
    SurveyModeQuerySet,
    SurveyTypeQuerySet,
)


class SurveyCategory(BaseWFPModelMixin, OrganizationsModelMixin):
    order = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        verbose_name = "Survey Category"
        verbose_name_plural = "Survey Categories"
        ordering = ("order", "id")

    def __str__(self):
        return self.label

    objects = SurveyCategoryQuerySet.as_manager()


class SurveyType(BaseWFPModelMixin, OrganizationsModelMixin):
    order = models.PositiveIntegerField(null=True, blank=True)

    category = models.ForeignKey(
        SurveyCategory, related_name="survey_types", on_delete=models.CASCADE
    )
    attributes = models.ManyToManyField(
        "surveys.SurveyAttribute", related_name="survey_types", blank=True
    )
    password_protected = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Survey Type"
        ordering = ("order", "id")

    def __str__(self):
        return self.label

    objects = SurveyTypeQuerySet.as_manager()


class SurveyMode(BaseWFPModelMixin, OrganizationsModelMixin):
    order = models.PositiveIntegerField(null=True, blank=True)
    attributes = models.ManyToManyField(
        "surveys.SurveyAttribute", related_name="survey_modes", blank=True
    )

    class Meta:
        verbose_name = "Survey Mode"
        ordering = ("order", "id")

    def __str__(self):
        return self.label

    objects = SurveyModeQuerySet.as_manager()


class SurveyAttribute(BaseWFPModelMixin, OrganizationsModelMixin):
    order = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        verbose_name = "Survey Context"
        verbose_name_plural = "Survey Context"
        ordering = ("order", "id")

    def __str__(self):
        return self.label

    objects = SurveyAttributeQuerySet.as_manager()


class Survey(models.Model):
    file = models.FileField()

    def get_enketo_preview_url(self):
        if settings.DEBUG:
            return self.file.url
        return f"{settings.ENKETO_PREVIEW_URL}{self.file.url}"


# Translations:


class SurveyCategoryTranslation(BaseTranslationMixin):
    category = models.ForeignKey(
        SurveyCategory, related_name="translations", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ["category", "language"]


class SurveyTypeTranslation(BaseTranslationMixin):
    type = models.ForeignKey(
        SurveyType, related_name="translations", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ["type", "language"]


class SurveyModeTranslation(BaseTranslationMixin):
    mode = models.ForeignKey(
        SurveyMode, related_name="translations", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ["mode", "language"]


class SurveyAttributeTranslation(BaseTranslationMixin):
    attribute = models.ForeignKey(
        SurveyAttribute, related_name="translations", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ["attribute", "language"]
