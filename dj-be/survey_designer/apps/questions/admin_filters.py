from admin_auto_filters.filters import AutocompleteFilter
from core.utils import get_model_admin_base_url
from django.conf import settings
from django.contrib.admin import SimpleListFilter
from django.db.models import Q
from django.db.models.functions import Coalesce
from modules.models import Indicator, Module, Submodule
from organization.models import Organization
from questions.const import QuestionType
from questions.models import (
    BaseQuestion,
    ChoiceGroup,
    ChoiceGroupFile,
    RecallPeriod,
    SubQuestion,
    Suffix,
)
from questions.recall_period_ordering import order_recall_period_queryset


class SubmoduleFilter(AutocompleteFilter):
    title = "Submodule"
    field_name = "submodule"
    parameter_name = "submodule__pk"


class ModuleFilter(AutocompleteFilter):
    title = "Module"
    field_name = "module"
    parameter_name = "submodule__module__pk"
    rel_model = Submodule


class ChoiceListFilter(AutocompleteFilter):
    title = "Choice List"
    field_name = "choices"
    parameter_name = "choices__pk"


class SuffixListFilter(AutocompleteFilter):
    title = "Suffix"
    field_name = "suffix"
    parameter_name = "sub_questions__suffix__pk"
    rel_model = SubQuestion


class Suffix2ListFilter(AutocompleteFilter):
    title = "Suffix 2"
    field_name = "suffix_2"
    parameter_name = "sub_questions__suffix_2__pk"
    rel_model = SubQuestion


class ParentSuffixListFilter(AutocompleteFilter):
    title = "Parent Suffix"
    field_name = "nested_suffixes"
    parameter_name = "parent_suffixes"


class RecallPeriodListFilter(AutocompleteFilter):
    title = "Recall Period"
    field_name = "recall_period"
    parameter_name = "recall_period__pk"
    rel_model = SubQuestion

    @staticmethod
    def get_queryset_for_field(model, name):
        return order_recall_period_queryset(RecallPeriod.objects.all())


class RootQuestionListFilter(AutocompleteFilter):
    title = "Root Question"
    field_name = "root_question"
    parameter_name = "root_question__pk"


class QuestionLevelFilter(SimpleListFilter):
    title = "Question Level"
    parameter_name = "question_level"

    def lookups(self, request, model_admin):
        return (
            ("root", "Root Question"),
            ("sub", "Question"),
        )

    def queryset(self, request, queryset):
        if self.value() == "root":
            return queryset.filter(root_question__isnull=False)
        if self.value() == "sub":
            return queryset.filter(sub_question__isnull=False)


class QuestionTypeFilter(SimpleListFilter):
    template = "admin/dropdown_filter.html"
    title = "Question Type"
    parameter_name = "question_type"

    def lookups(self, request, model_admin):
        return QuestionType.choices

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            qs = queryset.annotate(
                annotated_type=Coalesce(
                    "root_question__type",
                    "sub_question__suffix_2__type",
                    "sub_question__suffix__type",
                    "sub_question__root_question__type",
                )
            )
            return qs.filter(annotated_type=value)


class BaseQuestionSubmoduleFilter(AutocompleteFilter):
    title = "Submodule"
    field_name = "id"
    parameter_name = "submodule__pk"

    @staticmethod
    def get_queryset_for_field(model, name):
        return Submodule.objects.all()

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                Q(root_question__submodule=self.value())
                | Q(sub_question__root_question__submodule=self.value())
                | Q(repeat_section__submodule=self.value())
            )
        return queryset

    def get_autocomplete_url(self, request, model_admin):
        return get_model_admin_base_url(Submodule, "_autocomplete")


class BaseQuestionModuleFilter(AutocompleteFilter):
    title = "Module"
    field_name = "id"
    parameter_name = "submodule__module__pk"

    @staticmethod
    def get_queryset_for_field(model, name):
        return Module.objects.all()

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                Q(root_question__submodule__module=self.value())
                | Q(sub_question__root_question__submodule__module=self.value())
                | Q(repeat_section__submodule__module=self.value())
            )
        return queryset

    def get_autocomplete_url(self, request, model_admin):
        return get_model_admin_base_url(Module, "_autocomplete")


class BaseQuestionChoiceListFilter(AutocompleteFilter):
    title = "Choice List"
    field_name = "id"
    parameter_name = "choices__pk"

    @staticmethod
    def get_queryset_for_field(model, name):
        return ChoiceGroup.objects.all()

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                Q(root_question__choices=self.value())
                | Q(sub_question__suffix__choices=self.value())
                | Q(sub_question__suffix_2__choices=self.value())
            )
        return queryset

    def get_autocomplete_url(self, request, model_admin):
        return get_model_admin_base_url(ChoiceGroup, "_autocomplete")


class BaseQuestionSuffixListFilter(AutocompleteFilter):
    title = "Suffix"
    field_name = "id"
    parameter_name = "sub_questions__suffix__pk"

    @staticmethod
    def get_queryset_for_field(model, name):
        return Suffix.objects.all()

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(sub_question__suffix=self.value())
        return queryset

    def get_autocomplete_url(self, request, model_admin):
        return get_model_admin_base_url(Suffix, "_autocomplete")


class BaseQuestionSuffix2ListFilter(AutocompleteFilter):
    title = "Suffix 2"
    field_name = "id"
    parameter_name = "sub_questions__suffix_2__pk"

    @staticmethod
    def get_queryset_for_field(model, name):
        return Suffix.objects.all()

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(sub_question__suffix_2=self.value())
        return queryset

    def get_autocomplete_url(self, request, model_admin):
        return get_model_admin_base_url(Suffix, "_autocomplete")


class BaseQuestionRecallPeriodListFilter(AutocompleteFilter):
    title = "Recall Period"
    field_name = "id"
    parameter_name = "sub_questions__recall_period__pk"

    @staticmethod
    def get_queryset_for_field(model, name):
        return order_recall_period_queryset(RecallPeriod.objects.all())

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(sub_question__recall_period=self.value())
        return queryset

    def get_autocomplete_url(self, request, model_admin):
        return get_model_admin_base_url(RecallPeriod, "_autocomplete")


class QuestionTranslationFilter(SimpleListFilter):
    template = "admin/dropdown_multiple_filter.html"
    title = "Translations"
    parameter_name = "question_translation"

    def value(self):
        value = super().value()
        if value:
            return value.split(",")
        return []

    def lookups(self, request, model_admin):
        relevant_languages = set(
            BaseQuestion.objects.annotate(
                languages=Coalesce(
                    "root_question__translations__language",
                    "sub_question__translations__language",
                    "repeat_section__translations__language",
                )
            ).values_list("languages", flat=True)
        )
        return (
            (code, name)
            for (code, name) in settings.LANGUAGES
            if code in relevant_languages
        )

    def queryset(self, request, queryset):
        value = self.value()
        for lang in value:
            if lang == "en":
                continue
            queryset = queryset.filter(
                Q(root_question__translations__language=lang)
                | Q(sub_question__translations__language=lang)
                | Q(repeat_section__translations__language=lang)
            )
        return queryset

    def choices(self, changelist):
        for lookup, title in self.lookup_choices:
            yield {
                "selected": str(lookup) in self.value(),
                "query_string": lookup,
                "display": title,
            }


# Temporary filters until autocomplete is replaced


class QuestionModuleFilter(SimpleListFilter):
    title = "Module"
    parameter_name = "module__pk"
    template = "admin/dropdown_filter.html"

    def lookups(self, request, model_admin):
        return ((q.id, q.label) for q in Module.objects.order_by("label"))

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                root_question__submodule__module=self.value()
            ) | queryset.filter(
                sub_question__root_question__submodule__module=self.value()
            )
        return queryset


class QuestionSubmoduleFilter(SimpleListFilter):
    title = "Submodule"
    parameter_name = "submodule__pk"
    template = "admin/dropdown_filter.html"

    def lookups(self, request, model_admin):
        return ((q.id, q.label) for q in Submodule.objects.order_by("label"))

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                root_question__submodule=self.value()
            ) | queryset.filter(sub_question__root_question__submodule=self.value())
        return queryset


class QuestionChoiceFilter(SimpleListFilter):
    title = "Choice List"
    parameter_name = "choices__pk"
    template = "admin/dropdown_filter.html"

    def lookups(self, request, model_admin):
        return ((q.id, q.name) for q in ChoiceGroup.objects.all())

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                Q(root_question__choices=self.value())
                | Q(sub_question__suffix__choices=self.value())
                | Q(sub_question__suffix_2__choices=self.value())
            )
        return queryset


class QuestionChoiceFileFilter(SimpleListFilter):
    title = "Choice List with External File"
    parameter_name = "choice_file_filter"
    template = "admin/dropdown_filter.html"

    def lookups(self, request, model_admin):
        return ((q.id, q.name) for q in ChoiceGroupFile.objects.order_by("name"))

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                Q(root_question__choices_file=self.value())
                | Q(sub_question__suffix__choices_file=self.value())
                | Q(sub_question__suffix_2__choices_file=self.value())
            ).distinct()
        return queryset


class QuestionSuffixFilter(SimpleListFilter):
    title = "Suffix"
    parameter_name = "sub_questions__suffix__pk"
    template = "admin/dropdown_filter.html"

    def lookups(self, request, model_admin):
        return ((q.id, q.name) for q in Suffix.objects.all())

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(sub_question__suffix=self.value())
        return queryset


class QuestionSuffix2Filter(SimpleListFilter):
    title = "Suffix 2"
    parameter_name = "sub_questions__suffix_2__pk"
    template = "admin/dropdown_filter.html"

    def lookups(self, request, model_admin):
        return ((q.id, q.name) for q in Suffix.objects.all())

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(sub_question__suffix_2=self.value())
        return queryset


class QuestionRecallPeriodFilter(SimpleListFilter):
    title = "Recall Period"
    parameter_name = "sub_questions__recall_period__pk"
    template = "admin/dropdown_filter.html"

    def lookups(self, request, model_admin):
        recall_periods = order_recall_period_queryset(RecallPeriod.objects.all())
        return ((q.id, q.name) for q in recall_periods)

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(sub_question__recall_period=self.value())
        return queryset


class QuestionIndicatorFilter(SimpleListFilter):
    title = "Indicator"
    parameter_name = "indicators__pk"
    template = "admin/dropdown_filter.html"

    def lookups(self, request, model_admin):
        return ((q.id, q.label) for q in Indicator.objects.all())

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(indicators=self.value())
        return queryset


class QuestionOrganizationFilter(SimpleListFilter):
    title = "Organization"
    parameter_name = "organizations"

    def lookups(self, request, model_admin):
        return ((o.id, o.name) for o in Organization.objects.all())

    def queryset(self, request, queryset):
        q1 = Q(root_question__submodule__module__organizations=self.value())
        q2 = Q(
            sub_question__root_question__submodule__module__organizations=self.value()
        )
        if self.value():
            return queryset.filter(q1 | q2)
        return queryset
