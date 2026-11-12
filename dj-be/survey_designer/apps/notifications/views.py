from django.http import Http404
from django.utils.cache import patch_cache_control, patch_vary_headers
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notification
from .selectors import notifications_for_user, releases_for_user
from .serializers import (
    AcknowledgementRequestSerializer,
    AcknowledgementSerializer,
    NotificationDetailSerializer,
    NotificationListSerializer,
    ReleaseSerializer,
)
from .services import acknowledge_notification

LANGUAGE = OpenApiParameter(
    name="lang",
    type=str,
    description="Requested content language. Unavailable translations fall back to English.",
)


class ActiveAuthenticated(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.is_active


class ConsumerAccessMixin:
    permission_classes = (ActiveAuthenticated,)
    filter_backends = ()
    pagination_class = None

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        # Responses depend on current account/group membership and read state.
        patch_cache_control(response, private=True, no_store=True)
        patch_vary_headers(response, ("Cookie", "Authorization", "Accept-Language"))
        return response


@extend_schema(parameters=[LANGUAGE])
class NotificationListView(ConsumerAccessMixin, generics.ListAPIView):
    serializer_class = NotificationListSerializer

    def get_queryset(self):
        return notifications_for_user(self.request.user)


@extend_schema(parameters=[LANGUAGE])
class NotificationDetailView(ConsumerAccessMixin, generics.RetrieveAPIView):
    serializer_class = NotificationDetailSerializer

    def get_queryset(self):
        return notifications_for_user(self.request.user)


class NotificationAcknowledgeView(ConsumerAccessMixin, generics.GenericAPIView):
    serializer_class = AcknowledgementRequestSerializer

    @extend_schema(responses={200: AcknowledgementSerializer})
    def post(self, request, pk):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            state, _ = acknowledge_notification(
                notification_id=pk,
                actor=request.user,
                action=serializer.validated_data["action"],
            )
        except Notification.DoesNotExist as exc:
            raise Http404("Notification not found.") from exc
        return Response(AcknowledgementSerializer(state).data)


@extend_schema(parameters=[LANGUAGE])
class ReleaseDetailView(ConsumerAccessMixin, generics.RetrieveAPIView):
    serializer_class = ReleaseSerializer

    def get_queryset(self):
        return releases_for_user(self.request.user)


class LatestReleaseView(ReleaseDetailView):
    def get_object(self):
        release = self.get_queryset().first()
        if release is None:
            raise Http404("Release not found.")
        return release
