from adminsortable2.admin import SortableAdminMixin
from core.admin import (
    AdminUserTrackingMixin,
    CollationSafeSearchAdminMixin,
    FormFieldOverridesMixin,
)
from core.forms import TranslationForm
from core.utils import get_model_admin_base_url
from django.contrib import admin
from django.contrib.postgres.aggregates import ArrayAgg
from django.utils.html import format_html
from organization.mixins import (
    ChangeFormOrganizationsDisplayMixin,
    ObjectPermissionMixin,
    RestrictedVisibilityFieldMixin,
)
from surveys.forms import SurveyAttributesAdminModelForm
from surveys.models import (
    SurveyAttribute,
    SurveyAttributeTranslation,
    SurveyCategory,
    SurveyCategoryTranslation,
    SurveyMode,
    SurveyModeTranslation,
    SurveyType,
    SurveyTypeTranslation,
)


class SurveyCategoryTranslationInline(FormFieldOverridesMixin, admin.TabularInline):
    model = SurveyCategoryTranslation
    extra = 0
    exclude = ("created_by", "updated_by")
    form = TranslationForm


class SurveyModeTranslationInline(FormFieldOverridesMixin, admin.TabularInline):
    model = SurveyModeTranslation
    extra = 0
    exclude = ("created_by", "updated_by")
    form = TranslationForm


class SurveyTypeTranslationInline(FormFieldOverridesMixin, admin.TabularInline):
    model = SurveyTypeTranslation
    extra = 0
    exclude = ("created_by", "updated_by")
    form = TranslationForm


class SurveyAttributeTranslationInline(FormFieldOverridesMixin, admin.TabularInline):
    model = SurveyAttributeTranslation
    extra = 0
    exclude = ("created_by", "updated_by")
    form = TranslationForm


@admin.register(SurveyCategory)
class SurveyCategoryAdmin(
    CollationSafeSearchAdminMixin,
    RestrictedVisibilityFieldMixin,
    ObjectPermissionMixin,
    ChangeFormOrganizationsDisplayMixin,
    AdminUserTrackingMixin,
    FormFieldOverridesMixin,
    admin.ModelAdmin,
):
    list_display = (
        "name",
        "label",
        "description",
        "order",
        "modified_by",
        "modified_on",
        "organizations_display",
    )
    exclude = ("created_by", "updated_by")
    search_fields = ("name", "label", "description")
    inlines = (SurveyCategoryTranslationInline,)
    list_filter = ("organizations",)
    restricted_visibility_fields = ["organizations"]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(organization_names=ArrayAgg("organizations__name"))

    @admin.display(description="Organizations")
    def organizations_display(self, obj):
        if not obj.organization_names or not any(obj.organization_names):
            return ""
        return ",".join(obj.organization_names)


@admin.register(SurveyMode)
class SurveyModeAdmin(
    CollationSafeSearchAdminMixin,
    RestrictedVisibilityFieldMixin,
    ObjectPermissionMixin,
    ChangeFormOrganizationsDisplayMixin,
    AdminUserTrackingMixin,
    FormFieldOverridesMixin,
    admin.ModelAdmin,
):
    list_display = (
        "name",
        "label",
        "description",
        "order",
        "modified_by",
        "modified_on",
        "organizations_display",
    )
    exclude = ("created_by", "updated_by")
    search_fields = ("name", "label", "description")
    inlines = (SurveyModeTranslationInline,)
    list_filter = ("organizations",)
    restricted_visibility_fields = ["organizations"]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(organization_names=ArrayAgg("organizations__name"))

    @admin.display(description="Organizations")
    def organizations_display(self, obj):
        if not obj.organization_names or not any(obj.organization_names):
            return ""
        return ",".join(obj.organization_names)


@admin.register(SurveyType)
class SurveyTypeAdmin(
    CollationSafeSearchAdminMixin,
    RestrictedVisibilityFieldMixin,
    ObjectPermissionMixin,
    ChangeFormOrganizationsDisplayMixin,
    AdminUserTrackingMixin,
    FormFieldOverridesMixin,
    SortableAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "name",
        "label",
        "description",
        "category_display",
        "order_display",
        "modified_by",
        "modified_on",
        "organizations_display",
        "password_protected",
    )
    exclude = ("created_by", "updated_by")
    # autocomplete_fields = ("category", "attributes")
    list_select_related = ("category",)
    search_fields = ("name", "label", "description")
    inlines = (SurveyTypeTranslationInline,)
    list_filter = ("organizations",)
    restricted_visibility_fields = ["organizations", "category", "attributes"]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(organization_names=ArrayAgg("organizations__name"))

    @admin.display(description="Organizations")
    def organizations_display(self, obj):
        if not obj.organization_names or not any(obj.organization_names):
            return ""
        return ",".join(obj.organization_names)

    @admin.display(description="Order")
    def order_display(self, obj):
        return obj.order

    @admin.display(
        description="Category",
        ordering="category_id",
    )
    def category_display(self, obj):
        if not obj.category_id:
            return "-"

        url = get_model_admin_base_url(SurveyCategory, "_change", [obj.category_id])
        return format_html(
            "<a href='{url}' target='_blank'>{display}</a>",
            url=url,
            display=str(obj.category.label),
        )


@admin.register(SurveyAttribute)
class SurveyAttributeAdmin(
    CollationSafeSearchAdminMixin,
    RestrictedVisibilityFieldMixin,
    ObjectPermissionMixin,
    ChangeFormOrganizationsDisplayMixin,
    AdminUserTrackingMixin,
    FormFieldOverridesMixin,
    admin.ModelAdmin,
):
    list_display = (
        "name",
        "label",
        "description",
        "order",
        "modified_by",
        "modified_on",
        "organizations_display",
    )
    form = SurveyAttributesAdminModelForm
    exclude = ("created_by", "updated_by")
    search_fields = ("name", "label", "description")
    inlines = (SurveyAttributeTranslationInline,)
    list_filter = ("organizations",)
    restricted_visibility_fields = ["organizations"]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        survey_types = form.cleaned_data.get("survey_types", [])
        current_survey_types = set(SurveyType.objects.filter(attributes=obj))

        for survey_type in survey_types:
            if survey_type in current_survey_types:
                current_survey_types.remove(survey_type)
            else:
                survey_type.attributes.add(obj)

        for survey_type in current_survey_types:
            survey_type.attributes.remove(obj)

        survey_modes = form.cleaned_data.get("survey_modes", [])
        current_survey_modes = set(SurveyMode.objects.filter(attributes=obj))
        for mode in survey_modes:
            if mode in current_survey_modes:
                current_survey_modes.remove(mode)
            else:
                mode.attributes.add(obj)
        for mode in current_survey_modes:
            mode.attributes.remove(obj)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(organization_names=ArrayAgg("organizations__name"))

    @admin.display(description="Organizations")
    def organizations_display(self, obj):
        if not obj.organization_names or not any(obj.organization_names):
            return ""
        return ",".join(obj.organization_names)
