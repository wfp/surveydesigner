import uuid as uuid_

from django_filters import rest_framework as filters
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from saved_surveys.models import SavedSurvey, SubQuestionSubmodule

from .models import SubModuleOrder
from .serializers import SavedSurveysReadSerializer, SavedSurveysWriteSerializer


class SavedSurveyFilter(filters.FilterSet):
    name = filters.CharFilter(lookup_expr="icontains")
    organizations = filters.CharFilter(
        field_name="organizations__name", lookup_expr="icontains"
    )
    survey_category = filters.CharFilter(
        field_name="survey_category__label", lookup_expr="icontains"
    )
    survey_type = filters.CharFilter(
        field_name="survey_type__label", lookup_expr="icontains"
    )
    survey_mode = filters.CharFilter(
        field_name="survey_mode__label", lookup_expr="icontains"
    )
    attributes = filters.CharFilter(
        field_name="attributes__label", lookup_expr="icontains"
    )
    start_date = filters.DateTimeFilter(field_name="date_updated", lookup_expr="gte")
    end_date = filters.DateTimeFilter(field_name="date_updated", lookup_expr="lte")

    class Meta:
        model = SavedSurvey
        fields = [
            "name",
            "organizations",
            "survey_category",
            "survey_type",
            "survey_mode",
            "start_date",
            "end_date",
        ]


class SavedSurveyViewset(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = SavedSurveyFilter
    lookup_field = "uuid"

    def get_serializer_class(self):
        if self.request.method in ["POST", "PUT", "PATCH"]:
            return SavedSurveysWriteSerializer
        return SavedSurveysReadSerializer

    def get_queryset(self):
        return SavedSurvey.objects.filter(owner=self.request.user).prefetch_related(
            "organizations",
            "survey_category",
            "survey_type",
            "survey_mode",
            "indicators",
            "submodules",
            "attributes",
            "submodule_orders",
            "subquestions_submodules__submodule",
            "subquestions_submodules__subquestion",
            "subquestions_submodules__subquestion__suffix",
            "subquestions_submodules__subquestion__suffix_2",
        )

    def retrieve(self, request, *args, **kwargs):
        saved_survey = get_object_or_404(SavedSurvey, uuid=kwargs["uuid"])
        serializer = SavedSurveysReadSerializer(saved_survey)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = SavedSurveysWriteSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "saved survey created successfully"}, status=201)

    def update(self, request, *args, **kwargs):
        """
        Update a saved survey
        """
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({"message": "saved survey updated successfully"}, status=200)

    @action(detail=True, methods=["get"])
    def copy(self, request, uuid=None):
        """
        Save a duplicate version of a shared survey
        """
        saved_survey = SavedSurvey.objects.get(uuid=uuid)
        old_orgs = saved_survey.organizations.all()
        old_attributes = saved_survey.attributes.all()
        old_indicators = saved_survey.indicators.all()
        old_submodules = saved_survey.submodules.all()

        saved_survey.pk = None
        saved_survey.id = None
        saved_survey.uuid = uuid_.uuid4()
        saved_survey._state.adding = True
        saved_survey.owner = request.user
        saved_survey.save()

        saved_survey.organizations.set(old_orgs)
        saved_survey.attributes.set(old_attributes)
        saved_survey.indicators.set(old_indicators)
        saved_survey.submodules.set(old_submodules)

        # copy subquestion mappings
        old_saved_survey = SavedSurvey.objects.get(uuid=uuid)
        subquestion_mappings = SubQuestionSubmodule.objects.filter(
            saved_survey=old_saved_survey
        )
        for mapping in subquestion_mappings:
            mapping.pk = None
            mapping.id = None
            mapping._state.adding = True
            mapping.saved_survey = saved_survey
            mapping.save()

        submodule_orders = SubModuleOrder.objects.filter(saved_survey=old_saved_survey)

        for submodule_order in submodule_orders:
            submodule_order.pk = None
            submodule_order.id = None
            submodule_order._state.adding = True
            submodule_order.saved_survey = saved_survey
            submodule_order.save()

        serializer = SavedSurveysReadSerializer(saved_survey)
        return Response(serializer.data, status=200)
