from django.db.models import Count, Prefetch, Q
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from surveys.models import SurveyCategory, SurveyMode, SurveyType
from surveys.serializers import (
    SurveyCategorySerializer,
    SurveyModeSerializer,
    SurveysSerializer,
)

user_response = OpenApiResponse(description="Surveys", response=SurveysSerializer)


class SurveysAPIView(APIView):
    """
    Endpoint for getting all data to define a survey
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: user_response})
    def get(self, request, *args, **kwargs):
        organizations = request.organization_ids
        related_objects = Prefetch(
            "survey_types",
            queryset=SurveyType.objects.annotate(
                organization_match_count=Count(
                    "organizations", filter=Q(organizations__id__in=organizations)
                )
            )
            .filter(organization_match_count__gte=len(organizations))
            .prefetch_related("attributes", "indicator_mappings__indicator"),
        )
        categories = SurveyCategorySerializer(
            SurveyCategory.objects.annotate(
                organization_match_count=Count(
                    "organizations", filter=Q(organizations__id__in=organizations)
                ),
                organization_total_count=Count("organizations"),
            )
            .filter(
                organization_match_count=len(organizations),
                organization_total_count=len(organizations),
            )
            .prefetch_related(related_objects),
            many=True,
        ).data
        modes = SurveyModeSerializer(
            SurveyMode.objects.annotate(
                organization_match_count=Count(
                    "organizations", filter=Q(organizations__id__in=organizations)
                )
            )
            .filter(organization_match_count__gte=len(organizations))
            .prefetch_related("attributes"),
            many=True,
        ).data

        surveys = {
            "categories": categories,
            "modes": modes,
        }

        return Response(surveys)
