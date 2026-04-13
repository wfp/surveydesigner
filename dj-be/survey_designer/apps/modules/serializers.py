from typing import Dict, List

from django.conf import settings
from modules.models import (
    Indicator,
    IndicatorArea,
    Module,
    Submodule,
    SubmoduleRequiredGroup,
)
from organization.serializers import OrganizationSerializer
from questions.serializers import RootQuestionSerializer
from rest_framework import serializers
from surveys.serializers import SurveyTypesSerializer


class SubmoduleSerializer(serializers.ModelSerializer):
    is_mandatory = serializers.SerializerMethodField()
    root_questions = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = Submodule
        fields = (
            "id",
            "label",
            "description",
            "is_mandatory",
            "url",
            "root_questions",
            "is_active",
        )

    def get_is_mandatory(self, obj) -> bool:
        is_type_mandatory = getattr(obj, "is_type_mandatory", False) or False
        is_mode_mandatory = getattr(obj, "is_mode_mandatory", False) or False
        is_attributes_mandatory = (
            getattr(obj, "is_attributes_mandatory", False) or False
        )
        return is_type_mandatory or is_mode_mandatory or is_attributes_mandatory


class SubmoduleRequiredGroupSerializer(serializers.ModelSerializer):
    suffix = serializers.CharField(source="required_suffix.name", required=False)
    suffix_2 = serializers.CharField(
        source="required_nested_suffix.name", required=False
    )
    recall_period = serializers.CharField(
        source="required_recall_period.name", required=False
    )

    class Meta:
        model = SubmoduleRequiredGroup
        fields = (
            "suffix",
            "suffix_2",
            "recall_period",
        )


class SubmoduleWithQuestionsSerializer(serializers.ModelSerializer):
    root_questions = RootQuestionSerializer(
        source="filtered_root_questions", many=True, read_only=True
    )
    repeat_section_translations = serializers.SerializerMethodField()
    required_groups = SubmoduleRequiredGroupSerializer(many=True, read_only=True)

    class Meta:
        model = Submodule
        fields = (
            "id",
            "label",
            "root_questions",
            "module",
            "required_groups",
            "repeat_section_translations",
            "is_active",
        )

    def get_repeat_section_translations(self, obj) -> List[Dict[str, str]]:
        language_codes = set()
        languages = []

        def add_translation(t):
            if (code := t.language) not in language_codes:
                language_codes.add(code)
                languages.append(
                    {
                        "language": code,
                        "language_display": t.get_language_display(),
                    }
                )

        for repeat_section in obj.repeat_sections.all():
            for translation in repeat_section.translations.all():
                add_translation(translation)

        return languages


class ModuleSerializer(serializers.ModelSerializer):
    submodules = SubmoduleSerializer(many=True, read_only=True)
    organizations = OrganizationSerializer(many=True, read_only=True)

    class Meta:
        model = Module
        fields = (
            "id",
            "label",
            "description",
            "submodules",
            "url",
            "relevant",
            "organizations",
        )


class IndicatorAreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = IndicatorArea
        fields = (
            "id",
            "name",
            "label",
            "url",
            "order",
            "description",
        )


class IndicatorSerializer(serializers.ModelSerializer):
    is_mandatory = serializers.SerializerMethodField()
    submodules = SubmoduleSerializer(many=True, read_only=True)
    indicator_area = IndicatorAreaSerializer()
    root_questions = serializers.ListField(
        source="root_question_ids", child=serializers.IntegerField(), read_only=True
    )

    class Meta:
        model = Indicator
        fields = (
            "id",
            "name",
            "label",
            "url",
            "description",
            "root_questions",
            "submodules",
            "indicator_area",
            "is_mandatory",
        )

    def get_is_mandatory(self, obj) -> bool:
        is_type_mandatory = getattr(obj, "is_type_mandatory", False) or False
        is_mode_mandatory = getattr(obj, "is_mode_mandatory", False) or False
        is_attributes_mandatory = (
            getattr(obj, "is_attributes_mandatory", False) or False
        )
        return is_type_mandatory or is_mode_mandatory or is_attributes_mandatory


class GenerateXLSFormSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    submodules = serializers.ListField(child=serializers.IntegerField())
    submodules_order = serializers.ListField(child=serializers.IntegerField())
    sub_questions = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=True
    )
    languages = serializers.ListField(
        child=serializers.ChoiceField(choices=settings.LANGUAGES), allow_empty=True
    )
    indicators = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=True, required=False
    )
    survey_type = serializers.PrimaryKeyRelatedField(
        queryset=SurveyTypesSerializer.Meta.model.objects.all(),
        source="survey_type_id",
        required=False,
        write_only=True,
        allow_null=True,
    )


class UploadXLSFormSerializer(GenerateXLSFormSerializer):
    id = serializers.IntegerField(help_text="UserAPIKey ID")
    project_id = serializers.IntegerField(allow_null=True)


class SubmodulesOrderValidationSerializer(serializers.Serializer):
    messages = serializers.ListField(child=serializers.CharField())

    class Meta:
        fields = ("messages",)

    def to_representation(self, instance):
        if isinstance(instance, list):
            # If the instance is a list, return it directly as a list of strings
            return [str(item) for item in instance]
        # Otherwise, use the default to_representation method
        return super().to_representation(instance)
