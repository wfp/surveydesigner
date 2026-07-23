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

from core.organization_scope import (
    filter_for_selected_organizations,
    get_selected_organization_ids,
)
from django.db.models import Prefetch
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from surveys.models import SurveyAttribute, SurveyCategory, SurveyMode, SurveyType
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
        organizations = get_selected_organization_ids(request)

        if not organizations:
            return Response({"categories": [], "modes": []})

        scoped_attributes = filter_for_selected_organizations(
            SurveyAttribute.objects.all(), organizations
        )
        related_objects = Prefetch(
            "survey_types",
            queryset=filter_for_selected_organizations(
                SurveyType.objects.all(), organizations
            ).prefetch_related(
                Prefetch("attributes", queryset=scoped_attributes),
                "indicator_mappings__indicator",
            ),
        )
        categories = SurveyCategorySerializer(
            filter_for_selected_organizations(
                SurveyCategory.objects.all(), organizations
            ).prefetch_related(related_objects),
            many=True,
        ).data
        modes = SurveyModeSerializer(
            filter_for_selected_organizations(
                SurveyMode.objects.all(), organizations
            ).prefetch_related(Prefetch("attributes", queryset=scoped_attributes)),
            many=True,
        ).data

        surveys = {
            "categories": categories,
            "modes": modes,
        }

        return Response(surveys)
