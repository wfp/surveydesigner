from collections import defaultdict

from modules.models import Submodule
from organization.serializers import OrganizationListSerializer
from questions.models import SubQuestion
from rest_framework import serializers
from saved_surveys.models import SavedSurvey, SubModuleOrder, SubQuestionSubmodule
from surveys.serializers import (
    SurveyAttributeListSerializer,
    SurveyCategoryListSerializer,
    SurveyModeListSerializer,
    SurveyTypesListSerializer,
)


class SavedSurveysReadSerializer(serializers.ModelSerializer):
    organizations = OrganizationListSerializer(many=True, read_only=True)
    survey_category = SurveyCategoryListSerializer(read_only=True)
    survey_type = SurveyTypesListSerializer(read_only=True)
    survey_mode = SurveyModeListSerializer(read_only=True)
    attributes = SurveyAttributeListSerializer(many=True, read_only=True)
    subquestion_submodule_mapping = serializers.SerializerMethodField()
    submodules_order = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()
    sortable_updated_at = serializers.DateTimeField(source="date_updated")

    def get_subquestion_submodule_mapping(self, obj):
        mappings = obj.subquestions_submodules.all()
        mapping_data = defaultdict(list)
        for mapping in mappings:
            submodule_id = mapping.submodule.id
            subquestion = mapping.subquestion
            mapping_data[submodule_id].append(
                {
                    "suffix": subquestion.suffix.id if subquestion.suffix else None,
                    "suffix_2": (
                        subquestion.suffix_2.id if subquestion.suffix_2 else None
                    ),
                    "id": subquestion.id,
                    "recall_period_id": subquestion.recall_period_id,
                }
            )
        return dict(mapping_data)

    def get_submodules_order(self, obj):
        submodule_orders = obj.submodule_orders.order_by("order").values_list(
            "submodule_id", flat=True
        )
        return list(submodule_orders)

    def get_updated_at(self, obj):
        return obj.date_updated.strftime(
            "%B %d, %Y, %I:%M %p"
        )  # Localized Date and Time Format

    class Meta:
        model = SavedSurvey
        fields = (
            "uuid",
            "id",
            "name",
            "owner",
            "organizations",
            "survey_category",
            "survey_type",
            "survey_mode",
            "indicators",
            "submodules",
            "modules_order",
            "submodules_order",
            "subquestion_submodule_mapping",
            "attributes",
            "indicator_areas_order",
            "indicators_order",
            "languages",
            "created_at",
            "updated_at",
            "sortable_updated_at",
        )
        read_only_fields = ("uuid", "id", "owner", "created_at", "updated_at")


class SavedSurveysWriteSerializer(serializers.ModelSerializer):
    subquestions = serializers.JSONField(required=False)
    submodules_order = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Submodule.objects.all(), required=False
    )
    modules_order = serializers.ListField(
        child=serializers.IntegerField(), required=False
    )
    indicator_areas_order = serializers.ListField(
        child=serializers.IntegerField(), required=False
    )
    indicators_order = serializers.DictField(
        child=serializers.ListField(child=serializers.IntegerField()),
        required=False,
    )

    class Meta:
        model = SavedSurvey
        fields = (
            "uuid",
            "id",
            "name",
            "owner",
            "organizations",
            "survey_category",
            "survey_type",
            "survey_mode",
            "subquestions",
            "indicators",
            "submodules",
            "modules_order",
            "submodules_order",
            "attributes",
            "indicator_areas_order",
            "indicators_order",
            "languages",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("uuid", "id", "owner", "created_at", "updated_at")

    def create(self, validated_data):
        validated_data["owner"] = self.context["request"].user
        subquestion_mappings_data = validated_data.pop("subquestions", {})
        submodules_order = validated_data.pop("submodules_order", [])
        saved_survey = super().create(validated_data)

        for submodule_id, subquestion_ids in subquestion_mappings_data.items():
            submodule = Submodule.objects.get(id=submodule_id)
            for subquestion_id in subquestion_ids:
                subquestion = SubQuestion.objects.get(id=subquestion_id)
                SubQuestionSubmodule.objects.create(
                    saved_survey=saved_survey,
                    submodule=submodule,
                    subquestion=subquestion,
                )

        # set the order of the submodules
        for order, submodule in enumerate(submodules_order):
            SubModuleOrder.objects.create(
                saved_survey=saved_survey, submodule=submodule, order=order
            )
        return saved_survey

    def update(self, instance, validated_data):
        missing = serializers.empty
        subquestion_mappings_data = validated_data.pop("subquestions", missing)
        submodules_order = validated_data.pop("submodules_order", missing)
        instance = super().update(instance, validated_data)

        if subquestion_mappings_data is not missing:
            subquestion_mappings = SubQuestionSubmodule.objects.filter(
                saved_survey=instance
            )
            subquestion_mappings.delete()
            for submodule_id, subquestion_ids in subquestion_mappings_data.items():
                submodule = Submodule.objects.get(id=submodule_id)
                for subquestion_id in subquestion_ids:
                    subquestion = SubQuestion.objects.get(id=subquestion_id)
                    SubQuestionSubmodule.objects.create(
                        saved_survey=instance,
                        submodule=submodule,
                        subquestion=subquestion,
                    )

        if submodules_order is not missing:
            submodules_order_mapping = SubModuleOrder.objects.filter(
                saved_survey=instance
            )
            submodules_order_mapping.delete()
            for order, submodule in enumerate(submodules_order):
                SubModuleOrder.objects.create(
                    saved_survey=instance, submodule=submodule, order=order
                )

        return instance

    def validate(self, data):
        survey_category = data.get("survey_category")
        survey_type = data.get("survey_type")
        survey_mode = data.get("survey_mode")
        attributes = data.get("attributes")
        organizations = data.get("organizations")

        if (
            survey_category
            and organizations
            and not survey_category.organizations.filter(
                pk__in=[organization.pk for organization in organizations]
            ).exists()
        ):
            raise serializers.ValidationError(
                "Survey category must belong to at least one selected organization."
            )

        if survey_type and survey_category and survey_type.category != survey_category:
            raise serializers.ValidationError(
                "Survey type must belong to the same category as the saved survey."
            )

        if (
            survey_type
            and organizations
            and not survey_type.organizations.filter(
                pk__in=[organization.pk for organization in organizations]
            ).exists()
        ):
            raise serializers.ValidationError(
                "Survey type must belong to at least one selected organization."
            )

        if (
            survey_mode
            and organizations
            and not survey_mode.organizations.filter(
                pk__in=[organization.pk for organization in organizations]
            ).exists()
        ):
            raise serializers.ValidationError(
                "Survey mode must belong to at least one selected organization."
            )

        if (
            attributes
            and survey_type
            and not all(attr in survey_type.attributes.all() for attr in attributes)
        ):
            raise serializers.ValidationError(
                "Attribute must belong to the same type as the saved survey."
            )

        if (
            attributes
            and organizations
            and not all(
                attribute.organizations.filter(
                    pk__in=[organization.pk for organization in organizations]
                ).exists()
                for attribute in attributes
            )
        ):
            raise serializers.ValidationError(
                "Each attribute must belong to at least one selected organization."
            )

        return data
