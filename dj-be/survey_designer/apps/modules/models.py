from core.models import (
    BaseTranslationMixin,
    BaseWFPModelMixin,
    OrderFieldMixin,
    OrganizationsModelMixin,
    TimestampMixin,
    UserTrackingMixin,
)
from django.contrib.postgres.aggregates import ArrayAgg
from django.db import models
from questions.models import BaseQuestion


class ModuleQueryset(models.QuerySet):
    def visible_for_user(self, user):
        if user.is_global_admins_member or user.is_superuser:
            return self
        return self.filter(organizations=user.organization)

    def invisible_for_user(self, user):
        return self.exclude(id__in=self.visible_for_user(user))

    def _annotate_organization_ids(self):
        return self.annotate(organization_ids=ArrayAgg("organizations__id"))

    def exclude_by_organization_ids(self, organization_ids: list[int]):
        return self._annotate_organization_ids().exclude(
            organization_ids=organization_ids
        )


class Module(BaseWFPModelMixin, OrganizationsModelMixin, OrderFieldMixin):
    url = models.URLField(blank=True)
    default_submodule_mapping = models.OneToOneField(
        "modules.SubmoduleMapping",
        help_text="This mapping will be used for newly created submodules.",
        related_name="module",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    objects = ModuleQueryset.as_manager()

    class Meta:
        ordering = ("order",)

    def __str__(self):
        return self.label


class SubmoduleQueryset(models.QuerySet):
    def visible_for_user(self, user):
        if user.is_global_admins_member or user.is_superuser:
            return self
        return self.filter(module__organizations=user.organization)


class Submodule(BaseWFPModelMixin, OrderFieldMixin):
    module = models.ForeignKey(
        Module, related_name="submodules", on_delete=models.CASCADE
    )
    mapping = models.OneToOneField(
        "modules.SubmoduleMapping",
        related_name="submodule",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    url = models.URLField(blank=True)
    appearance = models.CharField(blank=True, max_length=255)
    relevant = models.TextField(blank=True)
    relevant_dependencies = models.ManyToManyField(
        BaseQuestion, related_name="submodule_relevant_dependencies", blank=True
    )

    objects = SubmoduleQueryset.as_manager()

    def __str__(self):
        return f"{self.module.label} - {self.label}"

    class Meta:
        unique_together = ("module", "name")
        ordering = ("order",)

    def save(self, *args, **kwargs):
        if not self.mapping and self.module and self.module.default_submodule_mapping:
            self.mapping = self.module.default_submodule_mapping.duplicate()
        super().save(*args, **kwargs)


class BaseMappingItem(models.Model):
    submodule_mapping = models.ForeignKey(
        "modules.SubmoduleMapping", on_delete=models.CASCADE
    )
    is_mandatory = models.BooleanField(default=False)

    class Meta:
        abstract = True


class SubmoduleMappingSurveyCategory(BaseMappingItem):
    survey_category = models.ForeignKey(
        "surveys.SurveyCategory", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ("submodule_mapping", "survey_category")


class SubmoduleMappingSurveyType(BaseMappingItem):
    survey_type = models.ForeignKey("surveys.SurveyType", on_delete=models.CASCADE)

    class Meta:
        unique_together = ("submodule_mapping", "survey_type")


class SubmoduleMappingSurveyMode(models.Model):
    is_mandatory = models.BooleanField(default=False)
    survey_mode = models.ForeignKey("surveys.SurveyMode", on_delete=models.CASCADE)
    survey_type = models.ForeignKey(
        "modules.SubmoduleMappingSurveyType",
        related_name="modes",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    class Meta:
        unique_together = ("survey_type", "survey_mode")


class SubmoduleMappingSurveyAttribute(BaseMappingItem):
    survey_attribute = models.ForeignKey(
        "surveys.SurveyAttribute", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ("submodule_mapping", "survey_attribute")


class SubmoduleRequiredGroup(models.Model):
    submodule = models.ForeignKey(
        Submodule,
        on_delete=models.CASCADE,
        related_name="required_groups",
        null=True,
    )
    required_suffix = models.ForeignKey(
        "questions.Suffix",
        on_delete=models.CASCADE,
        related_name="required_group_mappings",
        blank=True,
        null=True,
    )
    required_nested_suffix = models.ForeignKey(
        "questions.Suffix",
        on_delete=models.CASCADE,
        related_name="required_group_mappings_as_second",
        blank=True,
        null=True,
    )
    required_recall_period = models.ForeignKey(
        "questions.RecallPeriod",
        on_delete=models.CASCADE,
        related_name="required_group_mappings",
        blank=True,
        null=True,
    )

    class Meta:
        unique_together = (
            "submodule",
            "required_suffix",
            "required_nested_suffix",
            "required_recall_period",
        )


class SubmoduleMapping(UserTrackingMixin, TimestampMixin):
    survey_categories = models.ManyToManyField(
        "surveys.SurveyCategory",
        related_name="submodule_mappings",
        blank=True,
        through=SubmoduleMappingSurveyCategory,
    )
    survey_types = models.ManyToManyField(
        "surveys.SurveyType",
        related_name="submodule_mappings",
        blank=True,
        through=SubmoduleMappingSurveyType,
    )
    survey_attributes = models.ManyToManyField(
        "surveys.SurveyAttribute",
        related_name="submodule_mappings",
        blank=True,
        through=SubmoduleMappingSurveyAttribute,
    )

    @property
    def has_submodule(self):
        return hasattr(self, "submodule")

    def __str__(self):
        if self.has_submodule:
            return f"{self.submodule.label} - mapping"
        return f"Submodule mapping ({self.id})"

    def duplicate_mapping_items(self, mapping_through_cls, new_submodule_mapping):
        for mapping_item in mapping_through_cls.objects.filter(submodule_mapping=self):
            mapping_item.id = None
            mapping_item.submodule_mapping = new_submodule_mapping
            mapping_item.save()

    def duplicate(self):
        new_submodule_mapping = SubmoduleMapping.objects.create(
            created_by=self.created_by,
            updated_by=self.updated_by,
        )
        for through_model in (
            SubmoduleMappingSurveyCategory,
            SubmoduleMappingSurveyAttribute,
        ):
            self.duplicate_mapping_items(through_model, new_submodule_mapping)

        # Duplicate survey types and keep a mapping so we can copy their modes
        survey_type_mapping = {}
        for mapping_type in SubmoduleMappingSurveyType.objects.filter(
            submodule_mapping=self
        ):
            old_id = mapping_type.id
            mapping_type.id = None
            mapping_type.submodule_mapping = new_submodule_mapping
            mapping_type.save()
            survey_type_mapping[old_id] = mapping_type

        for old_type_id, new_type in survey_type_mapping.items():
            for mode in SubmoduleMappingSurveyMode.objects.filter(
                survey_type_id=old_type_id
            ):
                SubmoduleMappingSurveyMode.objects.create(
                    survey_type=new_type,
                    survey_mode=mode.survey_mode,
                    is_mandatory=mode.is_mandatory,
                )
        return new_submodule_mapping


class IndicatorArea(BaseWFPModelMixin, OrderFieldMixin):
    url = models.URLField(blank=True)

    class Meta:
        ordering = ("order",)


class Indicator(BaseWFPModelMixin, OrderFieldMixin):
    questions = models.ManyToManyField(
        BaseQuestion,
        related_name="indicators",
        blank=True,
    )
    mapping = models.OneToOneField(
        "modules.IndicatorMapping",
        related_name="indicator",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    indicator_area = models.ForeignKey(
        "modules.IndicatorArea",
        related_name="indicators",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    url = models.URLField(blank=True)

    @property
    def submodules(self):
        ids = (
            self.questions.exclude(root_question__submodule=None)
            .values_list("root_question__submodule", flat=True)
            .distinct()
        )
        return Submodule.objects.filter(id__in=ids)

    class Meta:
        ordering = ("order",)


class BaseIndicatorMappingItem(models.Model):
    indicator_mapping = models.ForeignKey(
        "modules.IndicatorMapping", on_delete=models.CASCADE
    )
    is_mandatory = models.BooleanField(default=False)

    class Meta:
        abstract = True


class IndicatorMappingSurveyType(BaseIndicatorMappingItem):
    survey_type = models.ForeignKey("surveys.SurveyType", on_delete=models.CASCADE)

    class Meta:
        unique_together = ("indicator_mapping", "survey_type")


class IndicatorMappingSurveyMode(models.Model):
    is_mandatory = models.BooleanField(default=False)
    survey_mode = models.ForeignKey("surveys.SurveyMode", on_delete=models.CASCADE)
    survey_type = models.ForeignKey(
        "modules.IndicatorMappingSurveyType",
        related_name="modes",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    class Meta:
        unique_together = ("survey_mode", "survey_type")


class IndicatorMappingSurveyAttribute(BaseIndicatorMappingItem):
    survey_attribute = models.ForeignKey(
        "surveys.SurveyAttribute", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ("indicator_mapping", "survey_attribute")


class IndicatorMapping(UserTrackingMixin, TimestampMixin):
    survey_types = models.ManyToManyField(
        "surveys.SurveyType",
        related_name="indicator_mappings",
        blank=True,
        through=IndicatorMappingSurveyType,
    )
    survey_attributes = models.ManyToManyField(
        "surveys.SurveyAttribute",
        related_name="indicator_mappings",
        blank=True,
        through=IndicatorMappingSurveyAttribute,
    )

    @property
    def has_indicator(self):
        return hasattr(self, "indicator")

    def __str__(self):
        if self.has_indicator:
            return f"{self.indicator.label} - mapping"
        return f"Indicator mapping ({self.id})"


class ModuleTranslation(BaseTranslationMixin):
    module = models.ForeignKey(
        Module, related_name="translations", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ("module", "language")


class SubmoduleTranslation(BaseTranslationMixin):
    submodule = models.ForeignKey(
        Submodule, related_name="translations", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ("submodule", "language")
