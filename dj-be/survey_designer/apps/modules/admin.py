import nested_admin
from adminsortable2.admin import SortableAdminMixin
from core.admin import AdminUserTrackingMixin, CollationSafeSearchAdminMixin
from core.forms import TranslationForm
from core.utils import get_model_admin_base_url
from django.contrib import admin, messages
from django.contrib.postgres.aggregates import ArrayAgg
from django.db import models
from django.db.models import Q
from django.forms import Textarea
from django.http import HttpResponse
from django.shortcuts import redirect
from django.templatetags.static import static
from django.utils.html import format_html
from dynamic_raw_id.admin import DynamicRawIDMixin
from modules.admin_filters import (
    IndicatorSurveyModeFilter,
    IndicatorSurveyTypeFilter,
    ModuleSurveyCategoryFilter,
    ModuleSurveyModeFilter,
    ModuleSurveyTypeFilter,
    SubmoduleSurveyCategoryFilter,
    SubmoduleSurveyModeFilter,
    SubmoduleSurveyTypeFilter,
)
from modules.forms import (
    IndicatorSurveyModeForm,
    IndicatorSurveyTypeForm,
    MappingSurveyAttributeInlineFormSet,
    MappingSurveyModeInlineFormSet,
    MappingSurveyTypeInlineFormSet,
    SubmoduleMappingForm,
    SubmoduleMappingSurveyCategoryInlineFormSet,
    SubmoduleRequiredGroupInlineFormSet,
    SurveyAttributeForm,
    SurveyCategoryForm,
    SurveyModeForm,
    SurveyTypeForm,
)
from modules.models import (
    Indicator,
    IndicatorArea,
    IndicatorMapping,
    IndicatorMappingSurveyAttribute,
    IndicatorMappingSurveyMode,
    IndicatorMappingSurveyType,
    Module,
    ModuleTranslation,
    Submodule,
    SubmoduleMapping,
    SubmoduleMappingSurveyAttribute,
    SubmoduleMappingSurveyCategory,
    SubmoduleMappingSurveyMode,
    SubmoduleMappingSurveyType,
    SubmoduleRequiredGroup,
    SubmoduleTranslation,
)
from organization.mixins import (
    ChangeFormOrganizationsDisplayMixin,
    FormsetRequestMixin,
    ObjectPermissionMixin,
    RestrictedVisibilityFieldMixin,
)
from organization.models import Organization
from questions.models import BaseQuestion, RootQuestion
from questions.services import QuestionsExport
from surveys.models import SurveyAttribute, SurveyCategory, SurveyMode, SurveyType


class ModuleListFilter(admin.SimpleListFilter):
    title = "Module"
    parameter_name = "module_id"

    def lookups(self, request, model_admin):
        modules = Module.objects.order_by("label")
        return [(module.id, module.label) for module in modules]

    def queryset(self, request, queryset):
        value = self.value()
        if value is not None:
            return queryset.filter(module_id=value)
        return queryset


class OrganizationListFilter(admin.SimpleListFilter):
    title = "Organization"
    parameter_name = "organization"

    def lookups(self, request, model_admin):
        return [
            (organization.id, organization.name)
            for organization in Organization.objects.all()
        ]

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(module__organizations=value)
        return queryset


class FormFieldOverridesMixin:
    formfield_overrides = {
        models.TextField: {"widget": Textarea(attrs={"rows": 2, "cols": 100})},
    }


class ModuleTranslationInline(
    ObjectPermissionMixin,
    FormFieldOverridesMixin,
    nested_admin.NestedTabularInline,
):
    model = ModuleTranslation
    extra = 0
    exclude = ("created_by", "updated_by")
    form = TranslationForm


class SubmoduleTranslationInline(
    ObjectPermissionMixin,
    FormFieldOverridesMixin,
    nested_admin.NestedTabularInline,
):
    model = SubmoduleTranslation
    extra = 0
    exclude = ("created_by", "updated_by")
    form = TranslationForm


class SubmoduleInline(
    ObjectPermissionMixin,
    DynamicRawIDMixin,
    FormFieldOverridesMixin,
    nested_admin.NestedStackedInline,
):
    model = Submodule
    extra = 0
    inlines = (SubmoduleTranslationInline,)
    exclude = ("created_by", "updated_by", "relevant_dependencies")
    dynamic_raw_id_fields = ("mapping",)


@admin.register(Module)
class ModuleAdmin(
    CollationSafeSearchAdminMixin,
    ObjectPermissionMixin,
    ChangeFormOrganizationsDisplayMixin,
    SortableAdminMixin,
    AdminUserTrackingMixin,
    FormFieldOverridesMixin,
    DynamicRawIDMixin,
    RestrictedVisibilityFieldMixin,
    nested_admin.NestedModelAdmin,
):
    restricted_visibility_fields = ["organizations"]
    exclude = ("created_by", "updated_by")
    list_display = (
        "name",
        "label",
        "description",
        "modified_by",
        "modified_on",
        "order_display",
        "organizations_display",
    )
    inlines = (SubmoduleInline, ModuleTranslationInline)
    search_fields = ("label", "name", "description")
    actions = (
        "add_submodule_mapping",
        "export_action",
    )
    dynamic_raw_id_fields = ("default_submodule_mapping",)
    list_filter = (
        "organizations",
        ModuleSurveyTypeFilter,
        ModuleSurveyCategoryFilter,
        ModuleSurveyModeFilter,
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(
            module_organizations=ArrayAgg("organizations__name", distinct=True)
        )

    @admin.display(description="Order")
    def order_display(self, obj):
        return obj.order

    @admin.display(description="Organizations")
    def organizations_display(self, obj):
        if not obj.module_organizations or not any(obj.module_organizations):
            return ""
        return ", ".join(obj.module_organizations)

    @admin.action(
        description="Export Questions as XLS",
        permissions=("add", "change", "delete"),
    )
    def export_action(self, request, queryset):
        q_export = QuestionsExport()
        submodules_prefetch = models.Prefetch(
            "submodules", q_export.get_optimized_submodule_qs(Submodule.objects.all())
        )
        xlsx = q_export.generate_from_modules(
            queryset.prefetch_related(submodules_prefetch)
        )

        response = HttpResponse(
            xlsx,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = "attachment; filename=export.xlsx"
        return response

    @admin.action(
        description="Add Submodule Mapping",
        permissions=("add", "change"),
    )
    def add_submodule_mapping(self, request, queryset):
        queryset = queryset.visible_for_user(request.user)
        ids = ",".join([str(id_) for id_ in queryset.values_list("id", flat=True)])
        url = f"{get_model_admin_base_url(SubmoduleMapping, '_add')}?module_ids={ids}"
        return redirect(url)


class SubmoduleRequiredGroupInline(
    ObjectPermissionMixin,
    nested_admin.NestedTabularInline,
):
    model = SubmoduleRequiredGroup
    formset = SubmoduleRequiredGroupInlineFormSet
    extra = 0


@admin.register(Submodule)
class SubmoduleAdmin(
    CollationSafeSearchAdminMixin,
    RestrictedVisibilityFieldMixin,
    ObjectPermissionMixin,
    ChangeFormOrganizationsDisplayMixin,
    SortableAdminMixin,
    AdminUserTrackingMixin,
    FormFieldOverridesMixin,
    DynamicRawIDMixin,
    nested_admin.NestedModelAdmin,
):
    exclude = ("created_by", "updated_by", "relevant_dependencies")
    list_display = (
        "name",
        "label",
        "description",
        "module_display",
        "question_list_button",
        "modified_by",
        "modified_on",
        "order_display",
        "organizations_display",
    )
    # autocomplete_fields = ("module",)
    list_filter = (
        OrganizationListFilter,
        SubmoduleSurveyTypeFilter,
        SubmoduleSurveyCategoryFilter,
        SubmoduleSurveyModeFilter,
        ModuleListFilter,
    )
    restricted_visibility_fields = ["module"]
    list_select_related = ("module",)
    search_fields = ("label", "name", "description")
    inlines = (SubmoduleRequiredGroupInline, SubmoduleTranslationInline)
    readonly_fields = ("question_list_button",)
    dynamic_raw_id_fields = ("mapping",)
    actions = (
        "add_submodule_mapping",
        "export_action",
    )

    fieldsets = (
        (
            "Related",
            {"fields": ("question_list_button",)},
        ),
        (
            "-",
            {
                "fields": (
                    "is_active",
                    "module",
                    "name",
                    "label",
                    "description",
                    "mapping",
                    "url",
                    "appearance",
                    "relevant",
                )
            },
        ),
    )

    class Media:
        css = {"all": (static("js/tribute/tribute.css"),)}
        js = [static("js/tribute/tribute.js"), static("js/admin/submodule.js")]

    @admin.display(description="Organizations")
    def organizations_display(self, obj):
        if not obj.organizations or not any(obj.organizations):
            return ""
        return ", ".join(obj.organizations)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.relevant:
            names = BaseQuestion.get_question_names(obj.relevant)
            base_questions = BaseQuestion.get_base_questions(names)
            obj.relevant_dependencies.set(question.id for question in base_questions)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        queryset = queryset.annotate(
            question_count=models.Count("root_questions"),
            organizations=ArrayAgg("module__organizations__name", distinct=True),
        )

        if admin.options.TO_FIELD_VAR in request.GET:
            queryset = queryset.visible_for_user(request.user)

        return queryset.order_by("order")

    @admin.display(description="Module")
    def module_display(self, obj):
        return obj.module.label

    @admin.display(description="Order")
    def order_display(self, obj):
        return obj.order

    @admin.display(
        description="Number of Questions",
        ordering="question_count",
    )
    def question_list_button(self, obj):
        if not obj.id:
            return "-"
        question_count = getattr(obj, "question_count", "-")
        query_params = f"?submodule__pk={obj.id}"  # submodule__pk param is related to SubmoduleFilter parameter_name
        url = get_model_admin_base_url(RootQuestion, "_changelist") + query_params
        on_click = f"window.open('{url}', 'popup', 'width=1200,height=600')"
        return format_html(
            "<button class='button' type='button' target='popup' onClick='{on_click}'>{display}</button>",
            on_click=on_click,
            display=f"{question_count}",
        )

    @admin.action(
        description="Export Questions as XLS",
        permissions=("add", "change", "delete"),
    )
    def export_action(self, request, queryset):
        q_export = QuestionsExport()
        queryset = q_export.get_optimized_submodule_qs(queryset)
        xlsx = q_export.generate_from_submodules(queryset)

        response = HttpResponse(
            xlsx,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = "attachment; filename=export.xlsx"
        return response


class SubmoduleMappingSurveyCategoryInline(
    FormsetRequestMixin,
    nested_admin.NestedTabularInline,
):
    form = SurveyCategoryForm
    template = "modules/mapping_category.html"
    model = SubmoduleMappingSurveyCategory
    formset = SubmoduleMappingSurveyCategoryInlineFormSet

    def get_queryset(self, request):
        queryset = SubmoduleMappingSurveyCategory.objects.prefetch_related(
            "survey_category__organizations"
        )
        if request.user.is_global_admins_member or request.user.is_superuser:
            return queryset
        return queryset.filter(
            survey_category__in=SurveyCategory.objects.visible_for_user(request.user)
        )

    def get_extra(self, request, obj=None, **kwargs):
        if obj:
            return SurveyCategory.objects.count() - obj.survey_categories.count()
        return SurveyCategory.objects.count()


class SubmoduleMappingSurveyModeInline(
    FormsetRequestMixin, nested_admin.NestedTabularInline
):
    form = SurveyModeForm
    model = SubmoduleMappingSurveyMode
    formset = MappingSurveyModeInlineFormSet

    def get_queryset(self, request):
        queryset = SubmoduleMappingSurveyMode.objects.prefetch_related(
            "survey_mode__organizations"
        )
        if request.user.is_global_admins_member or request.user.is_superuser:
            return queryset
        return queryset.filter(
            survey_mode__in=SurveyMode.objects.visible_for_user(request.user)
        )

    def get_extra(self, request, obj=None, **kwargs):
        if obj and obj.pk:
            return SurveyMode.objects.count() - obj.modes.count()
        return SurveyMode.objects.count()


class SubmoduleMappingSurveyTypeInline(
    FormsetRequestMixin, nested_admin.NestedTabularInline
):
    model = SubmoduleMappingSurveyType
    form = SurveyTypeForm
    formset = MappingSurveyTypeInlineFormSet
    template = "modules/mapping_type.html"
    inlines = [SubmoduleMappingSurveyModeInline]

    def get_queryset(self, request):
        queryset = SubmoduleMappingSurveyType.objects.prefetch_related(
            "survey_type__organizations"
        )
        if request.user.is_global_admins_member or request.user.is_superuser:
            return queryset
        return queryset.filter(
            survey_type__in=SurveyType.objects.visible_for_user(request.user)
        )

    def get_extra(self, request, obj=None, **kwargs):
        if obj:
            return SurveyType.objects.count() - obj.survey_types.count()
        return SurveyType.objects.count()


class SubmoduleMappingSurveyAttributeInline(
    FormsetRequestMixin, nested_admin.NestedTabularInline
):
    form = SurveyAttributeForm
    template = "modules/mapping_attribute.html"
    model = SubmoduleMappingSurveyAttribute
    formset = MappingSurveyAttributeInlineFormSet

    def get_queryset(self, request):
        queryset = SubmoduleMappingSurveyAttribute.objects.prefetch_related(
            "survey_attribute__organizations"
        )
        if request.user.is_global_admins_member or request.user.is_superuser:
            return queryset
        return queryset.filter(
            survey_attribute__in=SurveyAttribute.objects.visible_for_user(request.user)
        )

    def get_extra(self, request, obj=None, **kwargs):
        if obj:
            return SurveyAttribute.objects.count() - obj.survey_attributes.count()
        return SurveyAttribute.objects.count()


@admin.register(SubmoduleMapping)
class SubmoduleMappingAdmin(AdminUserTrackingMixin, nested_admin.NestedModelAdmin):
    form = SubmoduleMappingForm
    list_display = (
        "id",
        "module_display",
        "submodule_display",
        "modified_by",
        "modified_on",
    )
    list_select_related = ("submodule", "module")
    exclude = ("created_by", "updated_by")
    inlines = (
        SubmoduleMappingSurveyCategoryInline,
        SubmoduleMappingSurveyTypeInline,
        SubmoduleMappingSurveyAttributeInline,
    )

    class Media:
        js = [static("js/mapping.js")]

    def get_inlines(self, request, obj):
        inlines = super().get_inlines(request, obj)
        for inline in inlines:
            inline.form.user = request.user
        return inlines

    def get_model_perms(self, request):
        """Hide model from Admin index"""
        return {}

    @admin.display(
        description="Submodule",
        ordering="submodule",
    )
    def submodule_display(self, obj):
        if not hasattr(obj, "submodule"):
            return "-"

        url = get_model_admin_base_url(Submodule, "_change", [obj.submodule.id])
        return format_html(
            "<a href='{url}' target='_blank'>{display}</a>",
            url=url,
            display=str(obj.submodule.label),
        )

    @admin.display(
        description="Module",
        ordering="Module",
    )
    def module_display(self, obj):
        if not hasattr(obj, "module"):
            return "-"

        url = get_model_admin_base_url(Module, "_change", [obj.module.id])
        return format_html(
            "<a href='{url}' target='_blank'>{display}</a>",
            url=url,
            display=str(obj.module.label),
        )

    @staticmethod
    def save_many(request, submodule_mapping, submodule_ids, module_ids):
        updated_submodules = []
        updated_modules = []
        original_mapping_used = False

        user = request.user

        if submodule_ids or module_ids:
            submodules = (
                Submodule.objects.filter(
                    Q(id__in=submodule_ids) | Q(module_id__in=module_ids), mapping=None
                )
                .visible_for_user(user)
                .distinct()
            )
            for submodule in submodules:
                if original_mapping_used:
                    mapping_to_set = submodule_mapping.duplicate()
                else:
                    mapping_to_set = submodule_mapping
                    original_mapping_used = True

                submodule.mapping = mapping_to_set
                submodule.save()
                updated_submodules.append(submodule.name)

            if module_ids:
                modules = Module.objects.filter(
                    id__in=module_ids, default_submodule_mapping=None
                ).visible_for_user(user)
                for module in modules:
                    if original_mapping_used:
                        mapping_to_set = submodule_mapping.duplicate()
                    else:
                        mapping_to_set = submodule_mapping
                        original_mapping_used = True

                    module.default_submodule_mapping = mapping_to_set
                    module.save()
                    updated_modules.append(module.name)

            if updated_submodules:
                messages.success(
                    request, f"Updated submodules: {', '.join(updated_submodules)}"
                )
            else:
                messages.success(request, "Submobules already have a mappings.")

            if updated_modules:
                messages.success(
                    request,
                    f"Updated modules with new default submodule mapping: {', '.join(updated_modules)}",
                )

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        if not change:
            submodule_ids = (
                request.GET.get("submodule_ids", "").replace(",", " ").split()
            )
            module_ids = request.GET.get("module_ids", "").replace(",", " ").split()
            self.save_many(request, form.instance, submodule_ids, module_ids)


@admin.register(IndicatorArea)
class IndicatorAreaAdmin(
    CollationSafeSearchAdminMixin,
    AdminUserTrackingMixin,
    FormFieldOverridesMixin,
    admin.ModelAdmin,
):
    list_display = (
        "name",
        "label",
        "order",
        "modified_by",
        "modified_on",
    )
    exclude = ("created_by", "updated_by")
    search_fields = ("name", "label")


@admin.register(Indicator)
class IndicatorAdmin(
    CollationSafeSearchAdminMixin,
    ObjectPermissionMixin,
    SortableAdminMixin,
    AdminUserTrackingMixin,
    FormFieldOverridesMixin,
    DynamicRawIDMixin,
    nested_admin.NestedModelAdmin,
):
    exclude = ("created_by", "updated_by")
    # autocomplete_fields = ("questions", "survey_types")
    search_fields = ("name", "label", "description")
    list_display = (
        "name",
        "description",
        "question_list_button",
        "modified_by",
        "modified_on",
        "order_display",
        "indicator_area_display",
    )
    list_filter = (IndicatorSurveyTypeFilter, IndicatorSurveyModeFilter)
    actions = ("export_action",)
    dynamic_raw_id_fields = ("mapping",)
    filter_horizontal = ("questions",)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(question_count=models.Count("questions"))

    @admin.display(
        description="Number of Questions",
        ordering="question_count",
    )
    def question_list_button(self, obj):
        if not obj.id:
            return "-"
        question_count = getattr(obj, "question_count", "-")
        query_params = f"?indicators__pk={obj.id}"
        url = get_model_admin_base_url(BaseQuestion, "_changelist") + query_params
        on_click = f"window.open('{url}', 'popup', 'width=1200,height=600')"
        return format_html(
            "<button class='button' type='button' target='popup' onClick='{on_click}'>{display}</button>",
            on_click=on_click,
            display=f"{question_count}",
        )

    @admin.display(
        description="Indicator Areas",
        ordering="indicator_area__label",
    )
    def indicator_area_display(self, obj):
        if not obj.indicator_area:
            return "-"

        url = get_model_admin_base_url(
            IndicatorArea, "_change", [obj.indicator_area.id]
        )
        return format_html(
            "<a href='{url}' target='_blank'>{display}</a>",
            url=url,
            display=str(obj.indicator_area.label),
        )

    @admin.display(description="Order")
    def order_display(self, obj):
        return obj.order

    @admin.action(
        description="Export Questions as XLS",
        permissions=("add", "change", "delete"),
    )
    def export_action(self, request, queryset):
        q_export = QuestionsExport()
        xlsx = q_export.generate_from_indicators(queryset)

        response = HttpResponse(
            xlsx,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = "attachment; filename=export.xlsx"
        return response


class IndicatorMappingSurveyModeInline(
    FormsetRequestMixin, nested_admin.NestedTabularInline
):
    form = IndicatorSurveyModeForm
    model = IndicatorMappingSurveyMode
    formset = MappingSurveyModeInlineFormSet

    def get_queryset(self, request):
        queryset = IndicatorMappingSurveyMode.objects.prefetch_related(
            "survey_mode__organizations"
        )
        if request.user.is_global_admins_member or request.user.is_superuser:
            return queryset
        return queryset.filter(
            survey_mode__in=SurveyMode.objects.visible_for_user(request.user)
        )

    def get_extra(self, request, obj=None, **kwargs):
        if obj and obj.pk:
            return SurveyMode.objects.count() - obj.modes.count()
        return SurveyMode.objects.count()


class IndicatorMappingSurveyTypeInline(
    FormsetRequestMixin, nested_admin.NestedTabularInline
):
    model = IndicatorMappingSurveyType
    form = IndicatorSurveyTypeForm
    formset = MappingSurveyTypeInlineFormSet
    inlines = [IndicatorMappingSurveyModeInline]
    template = "modules/mapping_type.html"

    def get_queryset(self, request):
        queryset = IndicatorMappingSurveyType.objects.prefetch_related(
            "survey_type__organizations"
        )
        if request.user.is_global_admins_member or request.user.is_superuser:
            return queryset
        return queryset.filter(
            survey_type__in=SurveyType.objects.visible_for_user(request.user)
        )

    def get_extra(self, request, obj=None, **kwargs):
        if obj:
            return SurveyType.objects.count() - obj.survey_types.count()
        return SurveyType.objects.count()


class IndicatorMappingSurveyAttributeInline(
    FormsetRequestMixin, nested_admin.NestedTabularInline
):
    form = SurveyAttributeForm
    template = "modules/mapping_attribute.html"
    model = IndicatorMappingSurveyAttribute
    formset = MappingSurveyAttributeInlineFormSet

    def get_queryset(self, request):
        queryset = IndicatorMappingSurveyAttribute.objects.prefetch_related(
            "survey_attribute__organizations"
        )
        if request.user.is_global_admins_member or request.user.is_superuser:
            return queryset
        return queryset.filter(
            survey_attribute__in=SurveyAttribute.objects.visible_for_user(request.user)
        )

    def get_extra(self, request, obj=None, **kwargs):
        if obj:
            return SurveyAttribute.objects.count() - obj.survey_attributes.count()
        return SurveyAttribute.objects.count()


@admin.register(IndicatorMapping)
class IndicatorMappingAdmin(AdminUserTrackingMixin, nested_admin.NestedModelAdmin):
    exclude = ("created_by", "updated_by")
    inlines = [
        IndicatorMappingSurveyTypeInline,
        IndicatorMappingSurveyAttributeInline,
    ]

    def get_inlines(self, request, obj):
        inlines = super().get_inlines(request, obj)
        for inline in inlines:
            inline.form.user = request.user
        return inlines

    def get_model_perms(self, request):
        """Hide model from Admin index"""
        return {}
