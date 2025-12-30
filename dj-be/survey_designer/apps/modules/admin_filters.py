from admin_auto_filters.filters import AutocompleteFilter
from modules.models import (
    IndicatorMapping,
    IndicatorMappingSurveyMode,
    SubmoduleMapping,
    SubmoduleMappingSurveyMode,
)


class ModuleSurveyTypeFilter(AutocompleteFilter):
    title = "Survey Type"  # display title
    rel_model = SubmoduleMapping  # this is needed when you have nested lookup
    field_name = "survey_types"  # name of the foreign key field
    parameter_name = (
        "submodules__mapping__survey_types"  # for changing default while nested lookup
    )


class ModuleSurveyCategoryFilter(AutocompleteFilter):
    title = "Survey Category"
    rel_model = SubmoduleMapping
    field_name = "survey_categories"
    parameter_name = "submodules__mapping__survey_categories"


class ModuleSurveyModeFilter(AutocompleteFilter):
    title = "Survey Mode"
    rel_model = SubmoduleMappingSurveyMode
    field_name = "survey_mode"
    parameter_name = (
        "submodules__mapping__submodulemappingsurveytype__modes__survey_mode"
    )


class SubmoduleSurveyTypeFilter(AutocompleteFilter):
    title = "Survey Type"
    rel_model = SubmoduleMapping
    field_name = "survey_types"
    parameter_name = "mapping__survey_types"


class SubmoduleSurveyCategoryFilter(AutocompleteFilter):
    title = "Survey Category"
    rel_model = SubmoduleMapping
    field_name = "survey_categories"
    parameter_name = "mapping__survey_categories"


class SubmoduleSurveyModeFilter(AutocompleteFilter):
    title = "Survey Mode"
    rel_model = SubmoduleMappingSurveyMode
    field_name = "survey_mode"
    parameter_name = "mapping__submodulemappingsurveytype__modes__survey_mode"


class IndicatorSurveyTypeFilter(AutocompleteFilter):
    title = "Survey Type"
    rel_model = IndicatorMapping
    field_name = "survey_types"
    parameter_name = "mapping__survey_types"


class IndicatorSurveyModeFilter(AutocompleteFilter):
    title = "Survey Mode"
    rel_model = IndicatorMappingSurveyMode
    field_name = "survey_mode"
    parameter_name = "mapping__indicatormappingsurveytype__modes__survey_mode"
