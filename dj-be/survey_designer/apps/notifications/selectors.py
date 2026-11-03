from django.db.models import Exists, OuterRef
from django.utils import timezone

from .const import ReleaseStatus
from .models import NotificationAudience, NotificationRead, Release
from .services import currently_published_notifications


def _authenticated_user(user):
    return bool(user and user.is_authenticated and user.is_active and user.pk)


def notifications_for_user(user, *, include_dismissed=False):
    """Visible feed; include_dismissed is only for idempotent acknowledgement writes."""
    queryset = currently_published_notifications()
    if not _authenticated_user(user):
        return queryset.none()

    matching_audience = NotificationAudience.objects.filter(
        notification_id=OuterRef("pk"), group_id__in=user.groups.values("pk")
    )
    user_state = NotificationRead.objects.filter(
        notification_id=OuterRef("pk"), user_id=user.pk
    )
    queryset = queryset.filter(Exists(matching_audience))
    if not include_dismissed:
        queryset = queryset.exclude(Exists(user_state.filter(dismissed=True)))
    return (
        queryset.annotate(is_read=Exists(user_state.filter(read_at__isnull=False)))
        .select_related("release")
        .prefetch_related("translations")
    )


def releases_for_user(user):
    """Published notes inherit the linked notification's audience, not its read state."""
    queryset = Release.objects.filter(
        is_active=True,
        status=ReleaseStatus.PUBLISHED,
        published_at__lte=timezone.now(),
    )
    if not _authenticated_user(user):
        return queryset.none()

    matching_audience = NotificationAudience.objects.filter(
        notification__release_id=OuterRef("pk"),
        group_id__in=user.groups.values("pk"),
    )
    return queryset.filter(Exists(matching_audience)).prefetch_related("translations")
