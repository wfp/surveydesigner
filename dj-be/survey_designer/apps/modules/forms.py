from django import forms
from django.forms.models import BaseInlineFormSet
from modules.models import (
    IndicatorMappingSurveyMode,
    IndicatorMappingSurveyType,
    SubmoduleMappingSurveyAttribute,
    SubmoduleMappingSurveyCategory,
    SubmoduleMappingSurveyMode,
    SubmoduleMappingSurveyType,
    SubmoduleRequiredGroup,
)
from questions.models import RecallPeriod, Suffix
from surveys.models import SurveyAttribute, SurveyCategory, SurveyMode, SurveyType
from surveys.serializers import SurveyCategoryWithoutIndicatorsSerializer


class SubmoduleMappingForm(forms.ModelForm):
    category_to_type = forms.JSONField(required=False, widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        categories = SurveyCategoryWithoutIndicatorsSerializer(
            SurveyCategory.objects.prefetch_related("survey_types"), many=True
        ).data
        self.fields["category_to_type"].initial = categories


class BaseMappingForm(forms.ModelForm):
    include = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["include"].widget.attrs["class"] = "include-checkbox"

        if self.instance and self.instance.id:
            self.fields["include"].initial = True

    def clean(self):
        self.cleaned_data["DELETE"] = not self.cleaned_data["include"]
        return self.cleaned_data

    def has_changed(self):
        if not self.instance.id:
            return True
        return super().has_changed()


class SurveyCategoryForm(BaseMappingForm):
    class Meta:
        model = SubmoduleMappingSurveyCategory
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["survey_category"].queryset = (
            SurveyCategory.objects.visible_for_user(self.user)
        )


class SurveyTypeForm(BaseMappingForm):
    class Meta:
        model = SubmoduleMappingSurveyType
        fields = ["include", "is_mandatory", "survey_type"]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["survey_type"].queryset = SurveyType.objects.visible_for_user(user)


class SurveyModeForm(BaseMappingForm):
    class Meta:
        model = SubmoduleMappingSurveyMode
        fields = ["include", "is_mandatory", "survey_mode"]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.survey_type:
            self.fields["survey_mode"].queryset = SurveyMode.objects.visible_for_user(
                self.user
            )


class SurveyAttributeForm(BaseMappingForm):
    class Meta:
        model = SubmoduleMappingSurveyAttribute
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["survey_attribute"].queryset = (
            SurveyAttribute.objects.visible_for_user(self.user)
        )


class IndicatorSurveyTypeForm(BaseMappingForm):
    class Meta:
        model = IndicatorMappingSurveyType
        fields = ["include", "is_mandatory", "survey_type"]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["survey_type"].queryset = SurveyType.objects.visible_for_user(
            self.user
        )


class IndicatorSurveyModeForm(BaseMappingForm):
    class Meta:
        model = IndicatorMappingSurveyMode
        fields = ["include", "is_mandatory", "survey_mode"]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["survey_mode"].queryset = SurveyMode.objects.visible_for_user(
            self.user
        )


class SubmoduleRequiredGroupForm(forms.ModelForm):
    class Meta:
        model = SubmoduleRequiredGroup
        fields = "__all__"


class SubmoduleRequiredGroupInlineFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        self.instance = kwargs.get("instance")
        super().__init__(*args, **kwargs)

    def add_fields(self, form, index):
        super().add_fields(form, index)
        if self.instance and self.instance.id:
            form.fields["required_suffix"].queryset = Suffix.objects.filter(
                id__in=self.instance.root_questions.values_list(
                    "sub_questions__suffix", flat=True
                )
            )
            form.fields["required_nested_suffix"].queryset = Suffix.objects.filter(
                id__in=self.instance.root_questions.values_list(
                    "sub_questions__suffix_2", flat=True
                )
            )
            form.fields["required_recall_period"].queryset = (
                RecallPeriod.objects.filter(
                    id__in=self.instance.root_questions.values_list(
                        "sub_questions__recall_period", flat=True
                    )
                )
            )
        else:
            form.fields["required_suffix"].queryset = Suffix.objects.none()
            form.fields["required_nested_suffix"].queryset = Suffix.objects.none()
            form.fields["required_recall_period"].queryset = RecallPeriod.objects.none()


class SubmoduleMappingSurveyCategoryInlineFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        instance = kwargs.get("instance")
        user = self.request.user
        categories = SurveyCategory.objects.prefetch_related(
            "organizations"
        ).visible_for_user(user)

        if instance and instance.id:
            ids = instance.survey_categories.values_list("id", flat=True)
            categories = categories.exclude(id__in=ids)
            kwargs["initial"] = [{"survey_category": sc} for sc in categories]
        else:
            kwargs["initial"] = [
                {"survey_category": sc, "include": False} for sc in categories
            ]
        super().__init__(*args, **kwargs)


class MappingSurveyTypeInlineFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        instance = kwargs.get("instance")
        user = self.request.user if self.request else None
        self.user = user
        types = SurveyType.objects.visible_for_user(user)
        if instance and instance.id:
            ids = instance.survey_types.values_list("id", flat=True)
            types = types.exclude(id__in=ids)
            initial = [{"survey_type": sc} for sc in types]
        else:
            initial = [{"survey_type": sc, "include": False} for sc in types]
        self.initial = initial
        kwargs["initial"] = initial

        super().__init__(*args, **kwargs)

    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        kwargs["user"] = self.user
        return kwargs


class MappingSurveyModeInlineFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        instance = kwargs.get("instance")
        user = self.request.user if self.request else None
        self.user = user
        modes = SurveyMode.objects.visible_for_user(user)
        if instance and instance.id:
            ids = instance.modes.values_list("survey_mode__id", flat=True)
            modes = modes.exclude(id__in=ids)
            initial = [{"survey_mode": sm} for sm in modes]
        else:
            initial = [{"survey_mode": sm, "include": False} for sm in modes]

        kwargs["initial"] = initial

        super().__init__(*args, **kwargs)

    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        kwargs["user"] = self.user
        return kwargs


class MappingSurveyAttributeInlineFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        instance = kwargs.get("instance")
        user = self.request.user
        attrs = SurveyAttribute.objects.prefetch_related(
            "organizations"
        ).visible_for_user(user)

        if instance and instance.id:
            ids = instance.survey_attributes.values_list("id", flat=True)
            attrs = attrs.exclude(id__in=ids)
            kwargs["initial"] = [{"survey_attribute": sc} for sc in attrs]
        else:
            kwargs["initial"] = [
                {"survey_attribute": sc, "include": False} for sc in attrs
            ]
        super().__init__(*args, **kwargs)
