from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from release_notifications.models import ReleaseEvent, UserReleaseState
from release_notifications.serializers import (
    ClearReleaseNotificationsSerializer,
    ReleaseNotificationSerializer,
)
from release_notifications.services import update_release_state
from rest_framework.exceptions import NotFound
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


def eligible_releases():
    return ReleaseEvent.objects.filter(is_active=True, deployed_at__lte=timezone.now())


def release_response(release, user_state=None):
    return Response(
        {
            "release": (
                ReleaseNotificationSerializer(
                    release, context={"user_state": user_state}
                ).data
                if release is not None
                else None
            )
        }
    )


@method_decorator(never_cache, name="dispatch")
@method_decorator(ensure_csrf_cookie, name="dispatch")
class CurrentReleaseNotificationView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        release = eligible_releases().first()
        state = (
            UserReleaseState.objects.filter(
                user=request.user, release_event=release
            ).first()
            if release is not None
            else None
        )
        return release_response(release, state)


@method_decorator(never_cache, name="dispatch")
class ReadReleaseNotificationView(APIView):
    permission_classes = (IsAuthenticated,)
    action = "read"

    def post(self, request, release_id):
        release = get_object_or_404(eligible_releases(), pk=release_id)
        state = update_release_state(
            user=request.user, release_event=release, action=self.action
        )
        return release_response(release, state)


class ClearReleaseNotificationView(ReadReleaseNotificationView):
    action = "clear"


def states_for(user, releases):
    return {
        state.release_event_id: state
        for state in UserReleaseState.objects.filter(
            user=user, release_event_id__in=[release.pk for release in releases]
        )
    }


def unread_count(user):
    seen_ids = (
        UserReleaseState.objects.filter(user=user)
        .filter(Q(read_at__isnull=False) | Q(cleared_at__isnull=False))
        .values("release_event_id")
    )
    return eligible_releases().exclude(pk__in=seen_ids).count()


class ReleaseHistoryPagination(PageNumberPagination):
    page_size = 20


@method_decorator(never_cache, name="dispatch")
@method_decorator(ensure_csrf_cookie, name="dispatch")
class ReleaseHistoryView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        pagination = ReleaseHistoryPagination()
        releases = pagination.paginate_queryset(eligible_releases(), request, view=self)
        data = ReleaseNotificationSerializer(
            releases,
            many=True,
            context={"user_states": states_for(request.user, releases)},
        ).data
        response = pagination.get_paginated_response(data)
        response.data["unread_count"] = unread_count(request.user)
        return response


@method_decorator(never_cache, name="dispatch")
@method_decorator(ensure_csrf_cookie, name="dispatch")
class RecentReleaseNotificationsView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        releases = list(eligible_releases()[:5])
        states = states_for(request.user, releases)
        # Clearing the visible window must not refill it with older releases.
        visible = [
            release
            for release in releases
            if release.pk not in states or states[release.pk].cleared_at is None
        ]
        return Response(
            {
                "results": ReleaseNotificationSerializer(
                    visible, many=True, context={"user_states": states}
                ).data,
                "unread_count": unread_count(request.user),
            }
        )


@method_decorator(never_cache, name="dispatch")
class ClearRecentReleaseNotificationsView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = ClearReleaseNotificationsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ids = set(serializer.validated_data["release_ids"])
        releases = list(eligible_releases().filter(pk__in=ids).order_by("id"))
        if len(releases) != len(ids):
            raise NotFound("One or more release notifications are unavailable.")
        for release in releases:
            update_release_state(
                user=request.user, release_event=release, action="clear"
            )
        return Response({"cleared_ids": [release.pk for release in releases]})
