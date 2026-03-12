# Survey Designer
# Copyright (C) 2026 World Food Programme
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

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
