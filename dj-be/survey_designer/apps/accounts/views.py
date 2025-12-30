from json import JSONDecodeError

import requests
from accounts.models import UserAPIKey, UserAPISite
from django.contrib.auth import get_user_model
from django.db.models import Prefetch
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiTypes,
    extend_schema,
    inline_serializer,
)
from rest_framework import generics as rest_generics, serializers, status
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.generics import GenericAPIView, ListAPIView, get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from .const import UserAPISiteAPITypes
from .serializers import (
    UserAPIKeyReadSerializer,
    UserAPIKeySerializer,
    UserAPISiteSerializer,
    UserDetailSerializer,
)

User = get_user_model()


class AuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, created = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "user_id": user.pk, "email": user.email})


class UserDetailAPIView(rest_generics.RetrieveAPIView):
    """
    Get user details of currently logged in user.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = UserDetailSerializer

    def get_object(self):
        user_api_key_qs = (
            UserAPIKey.objects.filter(site__isnull=False)
            .exclude(name="")
            .select_related("site")
        )
        api_keys_prefetch = Prefetch("api_keys", queryset=user_api_key_qs)
        return User.objects.prefetch_related(api_keys_prefetch).get(
            id=self.request.user.id
        )


site_type_param = OpenApiParameter(
    name="site",
    type=OpenApiTypes.STR,
    description="Site to retrieve user projects from",
    required=True,
)


@extend_schema(
    parameters=[site_type_param],
    description="Site to retrieve user projects from",
    responses={
        200: inline_serializer(
            name="UserProjectListAPIResponse",
            fields={
                "id": serializers.IntegerField(),
                "name": serializers.CharField(),
            },
        ),
    },
)
class UserProjectListAPIView(APIView):
    """
    Get a list of user projects for a provided site.
    """

    permission_classes = [IsAuthenticated]

    def get_object(self) -> UserAPIKey:
        """Return UserAPIKey object from request"""
        return get_object_or_404(
            self.request.user.api_keys.all(), id=self.request.GET.get("site")
        )

    def get(self, request, *args, **kwargs):
        if not self.request.GET.get("site"):
            return Response(
                {"message": "Site not provided."}, status=status.HTTP_400_BAD_REQUEST
            )

        user_api_key = self.get_object()
        api_site = user_api_key.site
        url = UserAPISiteAPITypes.get_projects_url(api_site)

        if not url:
            return Response([])

        token = user_api_key.get_key()
        response = requests.get(url, headers={"Authorization": f"Token {token}"})

        if not response.ok:
            try:
                message = response.json()["detail"]
            except (AttributeError, JSONDecodeError, KeyError):
                message = "Undefined error"

            return Response(
                {"message": f"{message} ({response.status_code})"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        projects_data = response.json()
        projects = []

        moda_username = None
        if api_site.is_ona:
            response = requests.get(
                UserAPISiteAPITypes.get_profiles_url(api_site),
                headers={"Authorization": f"Token {token}"},
            )
            if not response.ok:
                try:
                    message = response.json()["detail"]
                except (AttributeError, JSONDecodeError, KeyError):
                    message = "Undefined error"
                return Response(
                    {"message": f"{message} ({response.status_code})"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            moda_profile = response.json()[0]
            moda_username = moda_profile["username"]

        for project_data in projects_data:
            if api_site.is_ona:
                role = self.__get_role_for_project(
                    project_data,
                    moda_username,
                    api_site,
                    token,
                )
                if role not in ("manager", "owner"):
                    continue

            projects.append(
                {
                    "id": project_data["projectid"],
                    "name": project_data["name"],
                }
            )

        return Response(projects)

    @staticmethod
    def __get_role_for_project(project, username, api_site: UserAPISite, token):
        project_users = project["users"]
        project_user = [user for user in project_users if user["user"] == username]

        if len(project_user):
            return project_user[0]["role"]

        project_teams = project["teams"]
        relevant_project_teams = [
            team for team in project_teams if username in team["users"]
        ]
        relevant_roles = [team["role"] for team in relevant_project_teams]

        if len(relevant_roles):
            if "owner" in relevant_roles:
                return "owner"
            else:
                return None

        org_project = [user for user in project_users if user["is_org"] is True]
        if len(org_project) != 1:
            return None
        org = org_project[0]["user"]
        response = requests.get(
            UserAPISiteAPITypes.get_orgs_url(api_site, org),
            headers={"Authorization": f"Token {token}"},
        )

        if not response.ok:
            return None

        org_data = response.json()
        org_users = org_data["users"]
        org_user = [user for user in org_users if user["user"] == username]

        if len(org_user):
            return org_user[0]["role"]

        return None


site_type_param = OpenApiParameter(
    "site_type",
    description="Filter UserAPIKeys by site type",
    type=OpenApiTypes.STR,
    enum=[str(site_type) for site_type in UserAPISiteAPITypes],
    required=False,
)


@extend_schema(
    description="Retrieve a list of UserAPIKey resources", parameters=[site_type_param]
)
class UserAPIKeyViewSet(ModelViewSet):
    """
    Viewset for managing user's API Key resources
    """

    queryset = UserAPIKey.objects.all()
    permission_classes = [IsAuthenticated]
    lookup_field = "id"

    SERIALIZERS_MAP = {
        "create": UserAPIKeySerializer,
        "update": UserAPIKeySerializer,
        "partial_update": UserAPIKeySerializer,
        "retrieve": UserAPIKeyReadSerializer,
        "list": UserAPIKeyReadSerializer,
    }

    def get_serializer_class(self):
        return self.SERIALIZERS_MAP.get(self.action, UserAPIKeySerializer)

    def get_queryset(self):
        queryset = super().get_queryset().order_by("date_created")
        return queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        if obj.user != request.user:
            self.permission_denied(request)


class UserAPISiteView(ListAPIView, GenericAPIView):
    permission_classes = [IsAuthenticated]

    queryset = UserAPISite.objects.all()
    serializer_class = UserAPISiteSerializer
