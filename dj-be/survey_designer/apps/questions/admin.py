from collections import Counter
from functools import update_wrapper

import nested_admin
from adminsortable2.admin import SortableAdminMixin
from core.admin import (
    AdminUserTrackingMixin,
    CollationSafeSearchAdminMixin,
    FormFieldOverridesMixin,
    SafeDynamicRawIDMixin,
)
from core.forms import TranslationForm
from core.utils import get_model_admin_base_url
from django.contrib import admin, messages
from django.contrib.admin.options import IS_POPUP_VAR
from django.contrib.postgres.aggregates import ArrayAgg
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Count, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce
from django.forms.models import BaseInlineFormSet
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, reverse
from django.templatetags.static import static
from django.utils.html import format_html, format_html_join
from django.utils.translation import ngettext
from django.views.generic import RedirectView
from modules.models import Indicator, Module, Submodule
from organization.mixins import (
    ChangeFormOrganizationsDisplayMixin,
    ObjectPermissionMixin,
    OrganizationOwnedParentFieldMixin,
    RequestUserFormMixin,
)
from questions.admin_filters import (
    ChoiceListFilter,
    ParentSuffixListFilter,
    QuestionChoiceFileFilter,
    QuestionChoiceFilter,
    QuestionIndicatorFilter,
    QuestionLevelFilter,
    QuestionModuleFilter,
    QuestionOrganizationFilter,
    QuestionRecallPeriodFilter,
    QuestionSubmoduleFilter,
    QuestionSuffix2Filter,
    QuestionSuffixFilter,
    QuestionTranslationFilter,
    QuestionTypeFilter,
    RecallPeriodListFilter,
    SuffixListFilter,
)
from questions.forms import (
    CalculationAdminModelForm,
    ChoiceGroupFileAdminModelForm,
    NestedSuffixForm,
    RootQuestionAdminModelForm,
    SubQuestionAdminModelForm,
    SubQuestionProxyForm,
    SubQuestionProxyTranslationFormset,
    SuffixAdminForm,
)
from questions.models import (
    BaseQuestion,
    Calculation,
    Choice,
    ChoiceGroup,
    ChoiceGroupFile,
    ChoiceTranslation,
    NestedSuffix,
    RecallPeriod,
    RepeatSection,
    RepeatSectionTranslation,
    RootQuestion,
    RootQuestionConstraintMessageTranslation,
    RootQuestionTranslation,
    SubQuestion,
    SubQuestionConstraintMessageTranslation,
    SubQuestionProxy,
    SubQuestionTranslation,
    Suffix,
)
from questions.recall_period_ordering import (
    order_recall_period_queryset,
    recall_period_ordering_expression,
)
from questions.services import QuestionsExport
from questions.views import BaseQuestionAutocomplete


class BaseQuestionOrderInline(ObjectPermissionMixin, nested_admin.NestedStackedInline):
    model = BaseQuestion
    fields = ("order",)
    can_delete = False


class ChoiceTranslationInline(
    ObjectPermissionMixin,
    FormFieldOverridesMixin,
    nested_admin.NestedTabularInline,
):
    model = ChoiceTranslation
    extra = 0
    exclude = ("created_by", "updated_by")
    form = TranslationForm


class ChoiceInlineFormset(BaseInlineFormSet):
    def clean(self):
        super().clean()

        active_count = 0
        seen_orders = set()
        orders_errors = []
        for form in self.forms:
            # Ignore empty forms or those marked for deletion
            if not form.cleaned_data or form.cleaned_data.get("DELETE", False):
                continue

            if form.cleaned_data.get("is_active", False):
                active_count += 1

            # Order checks
            order = form.cleaned_data.get("order")
            if order is None or not isinstance(order, int) or order <= 0:
                orders_errors.append("Order must be a positive integer (1 or higher).")
            elif order in seen_orders:
                orders_errors.append(f"Duplicate order value: {order}")
            else:
                seen_orders.add(order)

        if active_count == 0:
            raise ValidationError("At least one choice must be active.")
        if orders_errors:
            raise ValidationError(orders_errors)


class ChoiceInline(
    ObjectPermissionMixin,
    FormFieldOverridesMixin,
    nested_admin.NestedTabularInline,
):
    formset = ChoiceInlineFormset
    model = Choice
    extra = 0
    inlines = [ChoiceTranslationInline]
    exclude = ("created_by", "updated_by")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "choice_filter_name":
            if request._obj_ is not None:
                kwargs["queryset"] = Choice.objects.filter(
                    choice_group=request._obj_.choice_filter_list
                )
            else:
                kwargs["queryset"] = Choice.objects.none()

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_formset(self, request, obj=None, **kwargs):
        request._obj_ = obj
        return super().get_formset(request, obj, **kwargs)


class RootQuestionTranslationInline(
    ObjectPermissionMixin,
    FormFieldOverridesMixin,
    nested_admin.NestedTabularInline,
):
    model = RootQuestionTranslation
    extra = 0
    exclude = ("created_by", "updated_by")
    form = TranslationForm


class SubQuestionTranslationInline(
    ObjectPermissionMixin,
    FormFieldOverridesMixin,
    nested_admin.NestedTabularInline,
):
    model = SubQuestionTranslation
    extra = 0
    exclude = ("created_by", "updated_by")
    form = TranslationForm


class RepeatSectionTranslationInline(
    ObjectPermissionMixin,
    FormFieldOverridesMixin,
    nested_admin.NestedTabularInline,
):
    model = RepeatSectionTranslation
    extra = 0
    exclude = ("created_by", "updated_by")
    form = TranslationForm


class RootQuestionConstraintMessageTranslationInline(
    ObjectPermissionMixin,
    FormFieldOverridesMixin,
    nested_admin.NestedTabularInline,
):
    model = RootQuestionConstraintMessageTranslation
    extra = 0
    exclude = ("created_by", "updated_by")
    form = TranslationForm


class SubQuestionConstraintMessageTranslationInline(
    ObjectPermissionMixin,
    FormFieldOverridesMixin,
    nested_admin.NestedTabularInline,
):
    model = SubQuestionConstraintMessageTranslation
    extra = 0
    exclude = ("created_by", "updated_by")
    classes = ["sub_question_constraint_translations-group"]
    form = TranslationForm


class SubQuestionInline(
    ObjectPermissionMixin,
    FormFieldOverridesMixin,
    nested_admin.NestedStackedInline,
):
    model = SubQuestion
    form = SubQuestionAdminModelForm
    extra = 0
    inlines = (
        SubQuestionConstraintMessageTranslationInline,
        SubQuestionTranslationInline,
    )
    # autocomplete_fields = ["suffix", "suffix_2", "recall_period"]
    fk_name = "root_question"
    exclude = (
        "created_by",
        "updated_by",
        "name",
        "constraint_dependencies",
        "relevant_dependencies",
        "choice_filter_dependencies",
        "calculation_dependencies",
    )


@admin.register(ChoiceGroup)
class ChoiceGroupAdmin(
    CollationSafeSearchAdminMixin,
    ObjectPermissionMixin,
    ChangeFormOrganizationsDisplayMixin,
    AdminUserTrackingMixin,
    FormFieldOverridesMixin,
    nested_admin.NestedModelAdmin,
):
    exclude = ("created_by", "updated_by")
    list_display = (
        "name",
        "description",
        "translations",
        "notes",
        "question_list_button",
        "modified_by",
        "modified_on",
    )
    inlines = (ChoiceInline,)
    search_fields = ("name",)

    class Media:
        js = [static("js/admin/jquery-bridge.js")]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        # using subqueries not to inflate translation_languages
        question_count = (
            self.model.objects.filter(id=OuterRef("id"))
            .annotate(
                question_count=(
                    Count("root_questions", distinct=True)
                    + Count("suffixes__sub_questions", distinct=True)
                    + Count("suffixes__sub_questions_as_second", distinct=True)
                )
            )
            .values("question_count")[:1]
        )

        choices_count = (
            self.model.objects.filter(id=OuterRef("id"))
            .annotate(choices_count=Count("choices", distinct=True))
            .values("choices_count")[:1]
        )

        return queryset.annotate(
            question_count=Subquery(question_count),
            choices_count=Subquery(choices_count),
            translation_languages=ArrayAgg("choices__translations__language"),
        )

    @admin.display(description="Languages Available")
    def translations(self, obj):
        translations_counter = Counter(obj.translation_languages)
        translations_counter.pop(None, None)
        display_list = []
        for lang, count in translations_counter.items():
            if count < obj.choices_count:
                display_list.append(f"{lang} (incomplete)")
            else:
                display_list.append(lang)

        return ", ".join(display_list)

    @admin.display(
        description="Number of Questions",
        ordering="question_count",
    )
    def question_list_button(self, obj):
        if not obj.id:
            return "-"
        question_count = getattr(obj, "question_count", "-")
        query_params = f"?{ChoiceListFilter.parameter_name}={obj.id}"
        url = get_model_admin_base_url(BaseQuestion, "_changelist") + query_params
        on_click = f"window.open('{url}', 'popup', 'width=1200,height=600')"
        return format_html(
            "<button class='button' type='button' target='popup' onClick='{on_click}'>{display}</button>",
            on_click=on_click,
            display=f"{question_count}",
        )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "choice_filter_list":
            kwargs["queryset"] = ChoiceGroup.objects.order_by("name")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(ChoiceGroupFile)
class ChoiceGroupFileAdmin(
    CollationSafeSearchAdminMixin,
    ObjectPermissionMixin,
    AdminUserTrackingMixin,
    FormFieldOverridesMixin,
    admin.ModelAdmin,
):
    form = ChoiceGroupFileAdminModelForm
    exclude = ("created_by", "updated_by")
    list_display = (
        "name",
        "description",
        "csv_file",
        "notes",
        "question_list_button",
        "modified_by",
        "modified_on",
    )
    search_fields = ("name",)
    list_filter = ("date_updated",)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        question_count = (
            BaseQuestion.objects.filter(
                Q(root_question__choices_file=OuterRef("pk"))
                | Q(sub_question__suffix__choices_file=OuterRef("pk"))
                | Q(sub_question__suffix_2__choices_file=OuterRef("pk"))
            )
            .order_by()
            .annotate(group_marker=Value(1))
            .values("group_marker")
            .annotate(count=Count("pk", distinct=True))
            .values("count")[:1]
        )

        return queryset.annotate(
            question_count=Coalesce(
                Subquery(question_count),
                0,
                output_field=models.IntegerField(),
            )
        )

    @admin.display(
        description="Number of Questions",
        ordering="question_count",
    )
    def question_list_button(self, obj):
        if not obj.id:
            return "-"
        question_count = getattr(obj, "question_count", "-")
        query_params = f"?{QuestionChoiceFileFilter.parameter_name}={obj.id}"
        url = get_model_admin_base_url(BaseQuestion, "_changelist") + query_params
        on_click = f"window.open('{url}', 'popup', 'width=1200,height=600')"
        return format_html(
            "<button class='button' type='button' target='popup' onClick='{on_click}'>{display}</button>",
            on_click=on_click,
            display=f"{question_count}",
        )

    def save_model(self, request, obj, form, change):
        obj._request_user = request.user
        super().save_model(request, obj, form, change)


@admin.register(RootQuestion)
class RootQuestionAdmin(
    CollationSafeSearchAdminMixin,
    OrganizationOwnedParentFieldMixin,
    ObjectPermissionMixin,
    ChangeFormOrganizationsDisplayMixin,
    RequestUserFormMixin,
    AdminUserTrackingMixin,
    SafeDynamicRawIDMixin,
    FormFieldOverridesMixin,
    nested_admin.NestedModelAdmin,
):
    organization_owned_parent_fields = ["submodule"]
    form = RootQuestionAdminModelForm
    exclude = ("created_by", "updated_by")
    list_display = (
        "name",
        "description",
        "module_display",
        "submodule_display",
        "sub_question_list_button",
        "modified_by",
        "modified_on",
    )
    dynamic_raw_id_fields = ("submodule",)
    # autocomplete_fields = ("choices",)
    inlines = (
        BaseQuestionOrderInline,
        RootQuestionConstraintMessageTranslationInline,
        RootQuestionTranslationInline,
        SubQuestionInline,
    )
    list_filter = (
        # SubmoduleFilter,
        # ModuleFilter,
        # ChoiceListFilter,
        # SuffixListFilter,
        # Suffix2ListFilter,
        # RecallPeriodListFilter,
    )
    actions = ("duplicate",)
    search_fields = ("name", "label", "description")

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "submodule",
                    "name",
                    "description",
                    "type",
                    "calculation",
                    "choices",
                    "choices_file",
                    "label",
                    "hint",
                    "relevant",
                    "constraint",
                    "constraint_message",
                    "appearance",
                    "repeat_sections",
                    "indicators",
                    "required",
                    "disabled",
                    "read_only",
                    "default",
                    "choice_filter",
                    "parameters",
                )
            },
        ),
    )

    class Media:
        css = {"all": (static("js/tribute/tribute.css"),)}
        js = [static("js/tribute/tribute.js"), static("js/admin/question.js")]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.constraint:
            names = BaseQuestion.get_question_names(obj.constraint)
            base_questions = BaseQuestion.get_base_questions(names)
            obj.constraint_dependencies.set(question.id for question in base_questions)
        else:
            obj.constraint_dependencies.clear()
        if obj.relevant:
            names = BaseQuestion.get_question_names(obj.relevant)
            base_questions = BaseQuestion.get_base_questions(names)
            obj.relevant_dependencies.set(question.id for question in base_questions)
        else:
            obj.relevant_dependencies.clear()
        if obj.choice_filter:
            names = BaseQuestion.get_question_names(obj.choice_filter)
            base_questions = BaseQuestion.get_base_questions(names)
            obj.choice_filter_dependencies.set(
                question.id for question in base_questions
            )
        else:
            obj.choice_filter_dependencies.clear()
        if obj.calculation:
            names = BaseQuestion.get_question_names(obj.calculation)
            base_questions = BaseQuestion.get_base_questions(names)
            obj.calculation_dependencies.set(question.id for question in base_questions)
        else:
            obj.calculation_dependencies.clear()

        repeat_sections = form.cleaned_data.get("repeat_sections", [])
        indicators = form.cleaned_data.get("indicators", [])
        base_question = obj.base_question
        current_repeat_sections = set(
            RepeatSection.objects.filter(questions=base_question)
        )
        current_indicators = set(Indicator.objects.filter(questions=base_question))

        for repeat_section in repeat_sections:
            if repeat_section in current_repeat_sections:
                current_repeat_sections.remove(repeat_section)
            else:
                repeat_section.questions.add(base_question)

        for repeat_section in current_repeat_sections:
            repeat_section.questions.remove(base_question)

        for indicator in indicators:
            if indicator in current_indicators:
                current_indicators.remove(indicator)
            else:
                indicator.questions.add(base_question)

        for indicator in current_indicators:
            indicator.questions.remove(base_question)

    def get_model_perms(self, request):
        """Hide model from Admin index"""
        return {}

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(
            sub_question_count=models.Count("sub_questions", distinct=True)
        )

    def changelist_view(self, request, extra_context=None):
        if request.GET:
            return super().changelist_view(request, extra_context=extra_context)
        return HttpResponseRedirect(
            get_model_admin_base_url(BaseQuestion, "_changelist")
        )

    @admin.display(
        description="Number of Subquestions",
        ordering="sub_question_count",
    )
    def sub_question_list_button(self, obj):
        if not obj.id:
            return "-"
        sub_question_count = getattr(obj, "sub_question_count", "-")
        # query_params = f"?{RootQuestionListFilter.parameter_name}={obj.id}"
        url = get_model_admin_base_url(SubQuestion, "_changelist")  # + query_params
        on_click = f"window.open('{url}', 'popup', 'width=1200,height=600')"
        return format_html(
            "<button class='button' type='button' target='popup' onClick='{on_click}'>{display}</button>",
            on_click=on_click,
            display=f"{sub_question_count}",
        )

    @admin.display(description="Module")
    def module_display(self, obj):
        if not obj.submodule.count():
            return "-"

        module_ids = obj.submodule.values_list("module", flat=True)

        return format_html_join(
            ",\n",
            "<a href='{}' target='_blank'>{}</a>",
            (
                (get_model_admin_base_url(Module, "_change", [m.id]), m.label)
                for m in Module.objects.filter(id__in=module_ids)
            ),
        )

    @admin.display(description="Submodules")
    def submodule_display(self, obj):
        if not obj.submodule.count():
            return "-"

        return format_html_join(
            ",\n",
            "<a href='{}' target='_blank'>{}</a>",
            (
                (get_model_admin_base_url(Submodule, "_change", [s.id]), s.label)
                for s in obj.submodule.all()
            ),
        )

    @admin.action(
        description="Duplicate selected questions",
        permissions=("add",),
    )
    def duplicate(self, request, queryset):
        question_count = 0
        for question in queryset.prefetch_related(
            "translations", "sub_questions__translations"
        ):
            question_count += 1
            question.duplicate()

        message = ngettext(
            "Duplicate successfully created.",
            "Duplicates successfully created.",
            question_count,
        )
        messages.success(request, message)


@admin.register(RecallPeriod)
class RecallPeriodAdmin(
    CollationSafeSearchAdminMixin,
    AdminUserTrackingMixin,
    FormFieldOverridesMixin,
    admin.ModelAdmin,
):
    exclude = ("created_by", "updated_by")
    list_display = (
        "name",
        "description",
        "question_list_button",
        "modified_by",
        "modified_on",
    )
    search_fields = ("name", "description")

    def get_ordering(self, request):
        return (recall_period_ordering_expression("name"), "pk")

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return order_recall_period_queryset(
            queryset.annotate(
                question_count=models.Count("sub_questions__root_question")
            )
        )

    def has_change_permission(self, request, obj=None):
        user = request.user
        return user.is_global_admins_member or user.is_superuser

    def has_delete_permission(self, request, obj=None):
        user = request.user
        return user.is_global_admins_member or user.is_superuser

    @admin.display(
        description="Number of Questions",
        ordering="question_count",
    )
    def question_list_button(self, obj):
        if not obj.id:
            return "-"
        question_count = getattr(obj, "question_count", "-")
        query_params = f"?{RecallPeriodListFilter.parameter_name}={obj.id}"
        url = get_model_admin_base_url(SubQuestion, "_changelist") + query_params
        on_click = f"window.open('{url}', 'popup', 'width=1200,height=600')"
        return format_html(
            "<button class='button' type='button' target='popup' onClick='{on_click}'>{display}</button>",
            on_click=on_click,
            display=f"{question_count}",
        )


@admin.register(Suffix)
class SuffixAdmin(
    CollationSafeSearchAdminMixin,
    ObjectPermissionMixin,
    ChangeFormOrganizationsDisplayMixin,
    AdminUserTrackingMixin,
    FormFieldOverridesMixin,
    admin.ModelAdmin,
):
    exclude = ("created_by", "updated_by")
    form = SuffixAdminForm
    list_display = (
        "name",
        "description",
        "type",
        "choices",
        "question_list_button",
        "nested_suffix_list_button",
        "modified_by",
        "modified_on",
    )
    list_select_related = ("choices",)
    # autocomplete_fields = ("choices", "nested_suffixes")
    search_fields = ("name", "description")
    actions = ("add_nested_suffix",)
    list_filter = (ParentSuffixListFilter,)

    class Media:
        js = [static("js/admin/question.js"), static("js/admin/suffix-edit.js")]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(
            question_count=models.Count("sub_questions__root_question", distinct=True),
            nested_suffix_count=models.Count("nested_suffixes", distinct=True),
        )

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(
            request, queryset, search_term
        )
        sfxs = request.GET.get("exclude_sfxs", "").split(",")
        if sfxs:
            queryset = queryset.exclude(name__in=sfxs)

        parent_id = request.GET.get("parent_id", "")
        if parent_id.isdigit():
            queryset = queryset.filter(parent_suffixes=int(parent_id))
        return queryset, use_distinct

    @admin.display(
        description="Number of Questions",
        ordering="question_count",
    )
    def question_list_button(self, obj):
        if not obj.id:
            return "-"
        question_count = getattr(obj, "question_count", "-")
        query_params = f"?{SuffixListFilter.parameter_name}={obj.id}"
        url = get_model_admin_base_url(BaseQuestion, "_changelist") + query_params
        on_click = f"window.open('{url}', 'popup', 'width=1200,height=600')"
        return format_html(
            "<button class='button' type='button' target='popup' onClick='{on_click}'>{display}</button>",
            on_click=on_click,
            display=f"{question_count}",
        )

    @admin.display(
        description="# of nested suffixes",
        ordering="nested_suffix_count",
    )
    def nested_suffix_list_button(self, obj):
        if not obj.id:
            return "-"
        nested_suffix_count = getattr(obj, "nested_suffix_count", "-")
        query_params = f"?{ParentSuffixListFilter.parameter_name}={obj.id}"
        url = get_model_admin_base_url(Suffix, "_changelist") + query_params
        on_click = f"window.open('{url}', 'popup', 'width=1200,height=600')"
        return format_html(
            "<button class='button' type='button' target='popup' onClick='{on_click}'>{display}</button>",
            on_click=on_click,
            display=f"{nested_suffix_count}",
        )

    @admin.action(
        description="Add nested Suffix",
        permissions=("add",),
    )
    def add_nested_suffix(self, request, queryset):
        names = queryset.values_list("name", flat=True)
        url = f"{get_model_admin_base_url(NestedSuffix, '_add')}?sfxs={','.join(names)}"
        return redirect(url)


@admin.register(SubQuestion)
class SubQuestionAdmin(
    CollationSafeSearchAdminMixin,
    OrganizationOwnedParentFieldMixin,
    ObjectPermissionMixin,
    ChangeFormOrganizationsDisplayMixin,
    AdminUserTrackingMixin,
    SafeDynamicRawIDMixin,
    FormFieldOverridesMixin,
    nested_admin.NestedModelAdmin,
):
    organization_owned_parent_fields = ["root_question"]
    exclude = (
        "created_by",
        "updated_by",
        "name",
        "constraint_dependencies",
        "relevant_dependencies",
        "choice_filter_dependencies",
        "calculation_dependencies",
    )
    form = SubQuestionAdminModelForm
    list_display = (
        "name",
        "root_question_url",
        "suffix_url",
        "suffix_2_url",
        "recall_period_url",
        "label",
        "modified_by",
        "modified_on",
    )
    dynamic_raw_id_fields = ("root_question",)
    # autocomplete_fields = ("suffix", "suffix_2", "recall_period")
    list_select_related = ("root_question", "suffix", "suffix_2", "recall_period")
    inlines = (
        BaseQuestionOrderInline,
        SubQuestionConstraintMessageTranslationInline,
        SubQuestionTranslationInline,
    )
    # list_filter = (RootQuestionListFilter,)
    list_filter = (RecallPeriodListFilter,)
    search_fields = ("name", "label", "description")

    class Media:
        css = {"all": (static("js/tribute/tribute.css"),)}
        js = [
            static("js/tribute/tribute.js"),
            static("js/admin/sub-question-edit.js"),
        ]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        if obj.constraint:
            names = BaseQuestion.get_question_names(obj.constraint)
            base_questions = BaseQuestion.get_base_questions(names)
            obj.constraint_dependencies.set(question.id for question in base_questions)
        else:
            obj.constraint_dependencies.clear()
        if obj.relevant:
            names = BaseQuestion.get_question_names(obj.relevant)
            base_questions = BaseQuestion.get_base_questions(names)
            obj.relevant_dependencies.set(question.id for question in base_questions)
        else:
            obj.relevant_dependencies.clear()
        if obj.choice_filter:
            names = BaseQuestion.get_question_names(obj.choice_filter)
            base_questions = BaseQuestion.get_base_questions(names)
            obj.choice_filter_dependencies.set(
                question.id for question in base_questions
            )
        else:
            obj.choice_filter_dependencies.clear()
        if obj.calculation:
            names = BaseQuestion.get_question_names(obj.calculation)
            base_questions = BaseQuestion.get_base_questions(names)
            obj.calculation_dependencies.set(question.id for question in base_questions)
        else:
            obj.calculation_dependencies.clear()
        repeat_sections = form.cleaned_data.get("repeat_sections", [])
        indicators = form.cleaned_data.get("indicators", [])
        base_question = obj.base_question
        current_repeat_sections = set(
            RepeatSection.objects.filter(questions=base_question)
        )
        current_indicators = set(Indicator.objects.filter(questions=base_question))

        for repeat_section in repeat_sections:
            if repeat_section in current_repeat_sections:
                current_repeat_sections.remove(repeat_section)
            else:
                repeat_section.questions.add(base_question)

        for repeat_section in current_repeat_sections:
            repeat_section.questions.remove(base_question)

        for indicator in indicators:
            if indicator in current_indicators:
                current_indicators.remove(indicator)
            else:
                indicator.questions.add(base_question)
        for indicator in current_indicators:
            indicator.questions.remove(base_question)

    def get_model_perms(self, request):
        """Hide model from Admin index"""
        return {}

    def changelist_view(self, request, extra_context=None):
        if request.GET:
            return super().changelist_view(request, extra_context=extra_context)
        return HttpResponseRedirect(
            get_model_admin_base_url(BaseQuestion, "_changelist")
        )

    @admin.display(
        description="Suffix",
        ordering="suffix__name",
    )
    def suffix_url(self, obj):
        if not obj.suffix_id:
            return "-"

        url = get_model_admin_base_url(Suffix, "_change", [obj.suffix_id])

        return format_html(
            "<a href='{url}' target='_blank'>{display}</a>",
            url=url,
            display=str(obj.suffix),
        )

    @admin.display(
        description="Suffix 2",
        ordering="suffix_2__name",
    )
    def suffix_2_url(self, obj):
        if not obj.suffix_2_id:
            return "-"

        url = get_model_admin_base_url(Suffix, "_change", [obj.suffix_2_id])

        return format_html(
            "<a href='{url}' target='_blank'>{display}</a>",
            url=url,
            display=str(obj.suffix_2),
        )

    @admin.display(
        description="Recall Period",
        ordering=recall_period_ordering_expression("recall_period__name"),
    )
    def recall_period_url(self, obj):
        if not obj.recall_period_id:
            return "-"
        url = get_model_admin_base_url(RecallPeriod, "_change", [obj.recall_period_id])

        return format_html(
            "<a href='{url}' target='_blank'>{display}</a>",
            url=url,
            display=str(obj.recall_period),
        )

    @admin.display(description="Root Question")
    def root_question_url(self, obj):
        url = get_model_admin_base_url(RootQuestion, "_change", [obj.root_question_id])

        return format_html(
            "<a href='{url}' target='_blank'>{display}</a>",
            url=url,
            display=obj.root_question.name,
        )


@admin.register(BaseQuestion)
class BaseQuestionAdmin(
    CollationSafeSearchAdminMixin,
    ObjectPermissionMixin,
    SortableAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "name",
        "description_display",
        "module_display",
        "submodule_display",
        "organizations_display",
        "sub_question_list_button",
        "type",
        "modified_by",
        "modified_on",
        "order_display",
        "constraint_display",
    )
    search_fields = (
        "root_question__name",
        "sub_question__name",
        "repeat_section__name",
        "root_question__label",
        "sub_question__label",
        "repeat_section__label",
        "root_question__description",
        "sub_question__description",
        "repeat_section__description",
    )
    list_filter = (
        QuestionLevelFilter,
        QuestionTypeFilter,
        # Temporary filters until autocomplete is replaced ====================
        QuestionSubmoduleFilter,
        QuestionModuleFilter,
        QuestionChoiceFilter,
        QuestionChoiceFileFilter,
        QuestionSuffixFilter,
        QuestionSuffix2Filter,
        QuestionRecallPeriodFilter,
        # =====================================================================
        # BaseQuestionSubmoduleFilter,
        # BaseQuestionModuleFilter,
        # BaseQuestionChoiceListFilter,
        # BaseQuestionSuffixListFilter,
        # BaseQuestionSuffix2ListFilter,
        # BaseQuestionRecallPeriodListFilter,
        QuestionTranslationFilter,
        QuestionIndicatorFilter,
        QuestionOrganizationFilter,
    )
    actions = (
        "duplicate",
        "add_suffix_recall_period",
        "add_constraint",
        "add_relevant",
        "export_action",
    )

    @admin.display(description="Constraint")
    def constraint_display(self, obj):
        return obj.constraint

    @admin.display(description="Organizations")
    def organizations_display(self, obj):
        if not obj.organizations or not any(obj.organizations):
            return ""
        return ", ".join(o for o in obj.organizations)

    def delete_queryset(self, request, queryset):
        for base_question in queryset:
            base_question.instance.delete()

    def get_actions(self, request):
        actions = super().get_actions(request)

        if request.user.read_only_member:
            export_action_name = "export_action"
            export_action = actions.get(export_action_name)
            if export_action:
                actions = {export_action_name: export_action}
            else:
                actions = {}
        return actions

    def get_list_display(self, request):
        list_display = list(super().get_list_display(request))
        if request.user.read_only_member and "_reorder_" in list_display:
            list_display.remove("_reorder_")
        if IS_POPUP_VAR not in request.GET:
            # Use default rendering for popups, otherwise use our
            # custom display. This is so that the indicator admin page
            # can use a popup to select related questions.
            name_display_index = list_display.index("name")
            list_display[name_display_index] = "name_display"
        return list_display

    def get_urls(self):
        from django.urls import path

        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)

            wrapper.model_admin = self
            return update_wrapper(wrapper, view)

        info = self.model._meta.app_label, self.model._meta.model_name
        root_question_info = RootQuestion._meta.app_label, RootQuestion._meta.model_name

        return [
            path(
                "adminsortable2_update/",
                self.admin_site.admin_view(self.update_order),
                name=self._get_update_url_name(),
            ),
            path("", wrap(self.changelist_view), name="%s_%s_changelist" % info),
            path(
                "add/",
                wrap(
                    RedirectView.as_view(
                        pattern_name="%s:%s_%s_add"
                        % ((self.admin_site.name,) + root_question_info)
                    )
                ),
                name="%s_%s_add" % info,
            ),
            path(
                "autocomplete/",
                wrap(BaseQuestionAutocomplete.as_view()),
                name="%s_%s_autocomplete" % info,
            ),
            path(
                "<path:object_id>/history/",
                wrap(self.history_view),
                name="%s_%s_history" % info,
            ),
            path(
                "<path:object_id>/delete/",
                wrap(self.delete_view),
                name="%s_%s_delete" % info,
            ),
            path(
                "<path:object_id>/change/",
                wrap(self.change_view),
                name="%s_%s_change" % info,
            ),
            # For backwards compatibility (was the change url before 1.9)
            path(
                "<path:object_id>/",
                wrap(
                    RedirectView.as_view(
                        pattern_name="%s:%s_%s_change"
                        % ((self.admin_site.name,) + info)
                    )
                ),
            ),
        ]

    def get_queryset(self, request):
        submodule_prefetch = models.Prefetch(
            "submodule",
            queryset=Submodule.objects.select_related("module").order_by("order", "pk"),
        )
        queryset = super().get_queryset(request)
        return (
            queryset.select_related(
                "root_question",
                "root_question__updated_by",
                "sub_question",
                "sub_question__updated_by",
                "sub_question__root_question",
                "sub_question__suffix",
                "sub_question__suffix_2",
                "repeat_section",
                "repeat_section__updated_by",
            )
            .prefetch_related(
                models.Prefetch(
                    "root_question__submodule", queryset=submodule_prefetch.queryset
                ),
                models.Prefetch(
                    "sub_question__root_question__submodule",
                    queryset=submodule_prefetch.queryset,
                ),
                models.Prefetch(
                    "repeat_section__submodule",
                    queryset=submodule_prefetch.queryset,
                ),
            )
            .annotate(
                sub_question_count=models.Count(
                    "root_question__sub_questions", distinct=True
                ),
                annotated_name=Coalesce(
                    "root_question__name",
                    "sub_question__name",
                    "repeat_section__name",
                ),
                annotated_date_updated=Coalesce(
                    "root_question__date_updated",
                    "sub_question__date_updated",
                    "repeat_section__date_updated",
                ),
                organizations=ArrayAgg(
                    Coalesce(
                        "root_question__submodule__module__organizations__name",
                        "sub_question__root_question__submodule__module__organizations__name",
                    ),
                    distinct=True,
                ),
            )
            .order_by("order", "pk")
        )

    def _get_related_submodules(self, obj):
        if obj.repeat_section_id:
            return list(obj.repeat_section.submodule.all())

        root_question = obj.real_root_question
        if not root_question:
            return []

        return list(root_question.submodule.all())

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(
            request, queryset, search_term
        )

        types = request.GET.get("types", "")
        if types:
            types = types.split(",")
            queryset = queryset.filter_by_types(types, annotate_type=True)

        return queryset, use_distinct

    @admin.display(
        description="Name",
        ordering="annotated_name",
    )
    def name_display(self, obj):
        url = "#"

        if obj.root_question_id:
            url = get_model_admin_base_url(
                RootQuestion, "_change", [obj.root_question_id]
            )
        elif obj.sub_question_id:
            url = get_model_admin_base_url(
                SubQuestion, "_change", [obj.sub_question_id]
            )
        elif obj.repeat_section_id:
            url = get_model_admin_base_url(
                RepeatSection, "_change", [obj.repeat_section_id]
            )

        return format_html(
            "<a class='bold-link' href='{url}'>{display}</a>",
            url=url,
            display=obj.name,
        )

    @admin.display(description="Order")
    def order_display(self, obj):
        return obj.order

    @admin.display(description="Description")
    def description_display(self, obj):
        return obj.description

    @admin.display(description="Modules")
    def module_display(self, obj):
        submodules = self._get_related_submodules(obj)
        if not submodules:
            return "-"

        modules = {}
        for submodule in submodules:
            if submodule.module_id:
                modules[submodule.module_id] = submodule.module

        return format_html_join(
            ",\n",
            "<a href='{}' target='_blank'>{}</a>",
            (
                (get_model_admin_base_url(Module, "_change", [m.id]), m.label)
                for m in modules.values()
            ),
        )

    @admin.display(description="Submodules")
    def submodule_display(self, obj):
        submodules = self._get_related_submodules(obj)
        if not submodules:
            return "-"

        return format_html_join(
            ",\n",
            "<a href='{}' target='_blank'>{}</a>",
            [
                (get_model_admin_base_url(Submodule, "_change", [s.id]), s.label)
                for s in submodules
            ],
        )

    @admin.display(
        description="Modified On",
        ordering="annotated_date_updated",
    )
    def modified_on(self, obj):
        return obj.annotated_date_updated

    @admin.display(description="Modified By")
    def modified_by(self, obj):
        return obj.instance.updated_by

    @admin.display(
        description="Number of Subquestions",
        ordering="sub_question_count",
    )
    def sub_question_list_button(self, obj):
        if not obj.id or obj.sub_question_id or obj.repeat_section:
            return "-"
        sub_question_count = getattr(obj, "sub_question_count", "-")
        query_params = f"?root_question__pk={obj.root_question_id}"
        url = get_model_admin_base_url(SubQuestion, "_changelist") + query_params
        on_click = f"window.open('{url}', 'popup', 'width=1200,height=600')"
        return format_html(
            "<button class='button' type='button' target='popup' onClick='{on_click}'>{display}</button>",
            on_click=on_click,
            display=f"{sub_question_count}",
        )

    @admin.action(
        description="Duplicate selected questions",
        permissions=("add",),
    )
    def duplicate(self, request, queryset):
        question_count = 0
        for question in queryset:
            if question.root_question_id:
                question.root_question.duplicate()
                question_count += 1

        message = ngettext(
            "Duplicate successfully created.",
            "Duplicates successfully created.",
            question_count,
        )
        messages.success(request, message)

    @admin.action(
        description="Add Suffix/Recall Period",
        permissions=("add",),
    )
    def add_suffix_recall_period(self, request, queryset):
        ids = []
        names = []
        root_question_count = 0
        for base_question in queryset.filter(root_question__isnull=False):
            root_question = base_question.root_question
            root_question_count += 1
            ids.append(root_question.id)
            names.append(root_question.name)

        if not root_question_count:
            self.message_user(
                request,
                "Please select at least one Root Question",
                level=messages.ERROR,
            )
            return HttpResponseRedirect(
                get_model_admin_base_url(BaseQuestion, "_changelist")
            )

        url = (
            f"{get_model_admin_base_url(SubQuestionProxy, '_add')}"
            f"?ids={','.join(str(id_) for id_ in ids)}"
            f"&names={','.join(names)}"
        )
        return HttpResponseRedirect(url)

    @admin.action(
        description="Add Constraint",
        permissions=("add",),
    )
    def add_constraint(self, request, queryset):
        ids = []
        types = set()
        questions_with_constraint = []
        has_error = False

        for base_question in queryset:
            if base_question.instance.constraint:
                questions_with_constraint.append(base_question.name)

            ids.append(base_question.id)
            types.add(base_question.type)

        if questions_with_constraint:
            has_error = True
            self.message_user(
                request,
                f"Questions with constraint: {', '.join(questions_with_constraint)}",
                level=messages.ERROR,
            )

        if len(types) != 1:
            has_error = True
            self.message_user(
                request,
                "Questions do not have the same types.",
                level=messages.ERROR,
            )

        if has_error:
            return

        url = f"{reverse('constraint')}?ids={','.join(str(id_) for id_ in ids)}"
        return HttpResponseRedirect(url)

    @admin.action(
        description="Add Relevant",
        permissions=("add",),
    )
    def add_relevant(self, request, queryset):
        ids = []
        counter = 0
        questions_with_relevant = []
        has_error = False

        for base_question in queryset:
            if base_question.instance.relevant:
                questions_with_relevant.append(base_question.name)

            ids.append(base_question.id)
            counter += 1

        if questions_with_relevant:
            has_error = True
            self.message_user(
                request,
                f"Questions with relevant: {', '.join(questions_with_relevant)}",
                level=messages.ERROR,
            )

        if has_error:
            return

        url = f"{reverse('relevant')}?ids={','.join(str(id_) for id_ in ids)}"
        return HttpResponseRedirect(url)

    @admin.action(description="Export as XLS", permissions=("view",))
    def export_action(self, request, queryset):
        q_export = QuestionsExport()
        queryset = q_export.get_optimized_base_question_qs(queryset)
        xlsx = q_export.generate_from_questions(queryset)

        response = HttpResponse(
            xlsx,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = "attachment; filename=export.xlsx"
        return response


@admin.register(Calculation)
class CalculationAdmin(
    CollationSafeSearchAdminMixin,
    ObjectPermissionMixin,
    ChangeFormOrganizationsDisplayMixin,
    AdminUserTrackingMixin,
    FormFieldOverridesMixin,
    admin.ModelAdmin,
):
    form = CalculationAdminModelForm
    exclude = ("created_by", "updated_by", "related_questions")
    list_display = (
        "name",
        "label",
        "description",
        "modified_by",
        "modified_on",
    )
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "description",
                    "label",
                    "calculation",
                )
            },
        ),
    )
    search_fields = ("name", "label", "description")

    class Media:
        css = {"all": (static("js/tribute/tribute.css"),)}
        js = [
            static("js/tribute/tribute.js"),
            static("js/admin/calculations.js"),
        ]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        obj.set_related_questions()


@admin.register(NestedSuffix)
class NestedSuffixAdmin(RequestUserFormMixin, ObjectPermissionMixin, admin.ModelAdmin):
    exclude = (
        "created_by",
        "updated_by",
        "name",
        "description",
        "type",
        "choices",
        "is_active",
    )
    form = NestedSuffixForm
    # autocomplete_fields = ("nested_suffixes",)

    class Media:
        js = [static("js/admin/nested-suffix.js")]

    def get_model_perms(self, request):
        """Hide model from Admin index"""
        return {}

    def save_model(self, request, obj, form, change):
        pass

    def save_related(self, request, form, formsets, change):
        pass

    def log_addition(self, request, object, message):
        suffixes, nested_suffix_names = object
        message = f"Added nested suffixes: {nested_suffix_names}"
        for suffix in suffixes:
            self.log_change(request, suffix, message)

    def response_add(self, request, obj, post_url_continue=None):
        suffixes, nested_suffix_names = obj
        self.message_user(
            request, f"Nested suffixes added: {nested_suffix_names}", messages.SUCCESS
        )
        return HttpResponseRedirect(get_model_admin_base_url(Suffix, "_changelist"))

    def changelist_view(self, request, extra_context=None):
        return HttpResponseRedirect(get_model_admin_base_url(Suffix, "_changelist"))


class SubQuestionProxyTranslationInline(FormFieldOverridesMixin, admin.TabularInline):
    model = SubQuestionTranslation
    formset = SubQuestionProxyTranslationFormset
    extra = 0
    exclude = ("created_by", "updated_by")


@admin.register(SubQuestionProxy)
class SubQuestionProxyAdmin(
    RequestUserFormMixin, ObjectPermissionMixin, admin.ModelAdmin
):
    form = SubQuestionProxyForm
    exclude = (
        "created_by",
        "updated_by",
        "root_question",
        "name",
        "is_active",
        "relevant_dependencies",
        "constraint_dependencies",
        "choice_filter_dependencies",
        "calculation_dependencies",
    )
    # autocomplete_fields = ("suffix", "suffix_2", "recall_period")
    inlines = (SubQuestionProxyTranslationInline,)

    class Media:
        js = [static("js/admin/sub_question_action.js")]

    def get_model_perms(self, request):
        """Hide model from Admin index"""
        return {}

    def save_model(self, request, obj, form, change):
        pass

    def save_form(self, request, form, change):
        form.user = request.user
        saved_object = form.save(commit=False)
        form.sub_questions_created, form.root_questions = saved_object
        return saved_object

    def _create_translations(self, sub_questions, translation_data):
        translations = {}
        if not sub_questions:
            return translations

        for sub_question in sub_questions:
            translations[sub_question] = []
            for data in translation_data:
                if data.get("DELETE") is False:
                    translation = SubQuestionTranslation.objects.create(
                        sub_question=sub_question,
                        language=data["language"],
                        label=data["label"],
                    )
                    translations[sub_question].append(translation)

        return translations

    def save_related(self, request, form, formsets, change):
        for formset in formsets:
            if isinstance(formset, SubQuestionProxyTranslationFormset):
                translation_map = self._create_translations(
                    getattr(form, "sub_questions_created", formset._sub_questions),
                    formset.cleaned_data,
                )
                formset._created_translations = translation_map

    def construct_change_message(self, request, form, formsets, add=False):
        change_message = {}
        for formset in formsets:
            if isinstance(formset, SubQuestionProxyTranslationFormset):
                for sub_question, translations in formset._created_translations.items():
                    change_message[sub_question] = [{"added": {}}]

                    for translation in translations:
                        change_message[sub_question].append(
                            {
                                "added": {
                                    "name": str(translation._meta.verbose_name),
                                    "object": str(translation),
                                }
                            }
                        )

        return change_message

    def log_addition(self, request, object, message):
        sub_questions_created, root_questions = object
        for sub_question in sub_questions_created:
            sub_question_message = message[sub_question]
            super().log_addition(request, sub_question, sub_question_message)

    def response_add(self, request, obj, post_url_continue=None):
        sub_questions_created, root_questions = obj
        self.message_user(
            request,
            f"{len(sub_questions_created)} subquestions created.",
            messages.SUCCESS,
        )
        return HttpResponseRedirect(
            get_model_admin_base_url(BaseQuestion, "_changelist")
        )

    def changelist_view(self, request, extra_context=None):
        return HttpResponseRedirect(
            get_model_admin_base_url(BaseQuestion, "_changelist")
        )


@admin.register(RepeatSection)
class RepeatSectionAdmin(
    CollationSafeSearchAdminMixin,
    OrganizationOwnedParentFieldMixin,
    ObjectPermissionMixin,
    ChangeFormOrganizationsDisplayMixin,
    AdminUserTrackingMixin,
    SafeDynamicRawIDMixin,
    FormFieldOverridesMixin,
    nested_admin.NestedModelAdmin,
):
    organization_owned_parent_fields = ["submodule"]
    exclude = (
        "created_by",
        "updated_by",
        "repeat_count_dependencies",
        "relevant_dependencies",
    )
    list_display = (
        "name",
        "description",
        "submodule_display",
        "modified_by",
        "modified_on",
    )
    autocomplete_fields = ("questions",)
    dynamic_raw_id_fields = ("submodule",)
    search_fields = ("name", "label", "description")
    inlines = (RepeatSectionTranslationInline,)

    class Media:
        css = {"all": (static("js/tribute/tribute.css"),)}
        js = [static("js/tribute/tribute.js"), static("js/admin/repeat_section.js")]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related("updated_by").prefetch_related(
            models.Prefetch(
                "submodule",
                queryset=Submodule.objects.select_related("module").order_by(
                    "order",
                    "pk",
                ),
            )
        )

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        if db_field.name == "questions":
            kwargs["queryset"] = BaseQuestion.objects.select_related(
                "root_question",
                "sub_question",
                "repeat_section",
            )
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        obj.set_repeat_count_dependencies()
        if obj.relevant:
            names = BaseQuestion.get_question_names(obj.relevant)
            base_questions = BaseQuestion.get_base_questions(names)
            obj.relevant_dependencies.set(question.id for question in base_questions)
        else:
            obj.relevant_dependencies.clear()

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(
            request, queryset, search_term
        )

        submodule = request.GET.get("submodule", "")
        if submodule.isdigit():
            queryset = queryset.filter(submodule_id=int(submodule))

        return queryset, use_distinct

    @admin.display(description="Submodule")
    def submodule_display(self, obj):
        submodules = list(obj.submodule.all())
        if not submodules:
            return "-"

        return format_html_join(
            ",\n",
            "<a href='{}' target='_blank'>{}</a>",
            (
                (get_model_admin_base_url(Submodule, "_change", [s.id]), s.label)
                for s in submodules
            ),
        )
