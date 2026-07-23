from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import AutocompleteSelectMultiple
from django.forms import ModelForm
from modules.models import IndicatorMapping, IndicatorMappingSurveyMode
from organization.permissions import mutation_safe_related_queryset
from surveys.models import SurveyMode, SurveyType


class SurveyAttributesAdminModelForm(ModelForm):
    survey_types = forms.ModelMultipleChoiceField(
        queryset=SurveyType.objects.none(),
        required=True,
        widget=AutocompleteSelectMultiple(
            IndicatorMapping.survey_types.field, admin.site
        ),
    )
    survey_modes = forms.ModelMultipleChoiceField(
        queryset=SurveyMode.objects.none(),
        required=False,
        widget=AutocompleteSelectMultiple(
            IndicatorMappingSurveyMode._meta.get_field(
                "survey_mode"
            ),  # points at SurveyMode
            admin.site,
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # allow searching across all options
        self.fields["survey_types"].queryset = SurveyType.objects.all()
        self.fields["survey_modes"].queryset = SurveyMode.objects.all()

        if self.instance and self.instance.pk:
            init_types = SurveyType.objects.filter(attributes=self.instance)
            self.fields["survey_types"].initial = init_types

            init_modes = SurveyMode.objects.filter(attributes=self.instance)
            self.fields["survey_modes"].initial = init_modes

        else:
            # Default to all modes selected when creating a new context
            all_modes = list(SurveyMode.objects.all())
            self.fields["survey_modes"].initial = all_modes

        user = getattr(self, "user", None)
        if user is not None:
            for field_name in ("survey_types", "survey_modes"):
                field = self.fields[field_name]
                field.queryset = mutation_safe_related_queryset(field.queryset, user)
