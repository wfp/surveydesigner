from organization.serializers import OrganizationListSerializer
from questions.models import SubQuestion
from rest_framework import serializers
from surveys.models import SurveyAttribute, SurveyCategory, SurveyMode, SurveyType


class SurveyModeSerializer(serializers.ModelSerializer):
    attributes = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = SurveyMode
        fields = ("id", "label", "description", "attributes")


class SurveyModeListSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurveyMode
        fields = ("id", "label")


class SurveyAttributeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurveyAttribute
        fields = ("id", "label", "description", "is_active")


class SurveyAttributeListSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurveyAttribute
        fields = ("id", "label")


class SurveyTypesWithoutIndicatorsSerializer(serializers.ModelSerializer):
    attributes = SurveyAttributeSerializer(many=True)

    class Meta:
        model = SurveyType
        fields = ("id", "label", "description", "attributes", "is_active", "order")


class SurveyCategoryWithoutIndicatorsSerializer(serializers.ModelSerializer):
    survey_types = SurveyTypesWithoutIndicatorsSerializer(many=True, read_only=True)

    class Meta:
        model = SurveyCategory
        fields = ("id", "label", "survey_types", "description")


class SurveyTypesSerializer(serializers.ModelSerializer):
    attributes = SurveyAttributeSerializer(many=True)

    class Meta:
        model = SurveyType
        fields = ("id", "label", "description", "attributes", "is_active", "order")


class SurveyTypesListSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurveyType
        fields = ("id", "label")


class SurveyCategorySerializer(serializers.ModelSerializer):
    survey_types = SurveyTypesSerializer(many=True, read_only=True)
    organizations = OrganizationListSerializer(many=True, read_only=True)

    class Meta:
        model = SurveyCategory
        fields = ("id", "label", "survey_types", "description", "organizations")


class SurveyCategoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurveyCategory
        fields = ("id", "label")


class SurveysSerializer(serializers.Serializer):
    categories = SurveyCategorySerializer(many=True)
    modes = SurveyModeSerializer(many=True)


class SubquestionListSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubQuestion
        fields = ("id", "name", "suffix")
