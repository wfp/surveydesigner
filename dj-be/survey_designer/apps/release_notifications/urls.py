from django.urls import path
from release_notifications.views import (
    ClearRecentReleaseNotificationsView,
    ClearReleaseNotificationView,
    CurrentReleaseNotificationView,
    ReadReleaseNotificationView,
    RecentReleaseNotificationsView,
    ReleaseHistoryView,
)

urlpatterns = [
    path("", ReleaseHistoryView.as_view(), name="release-history"),
    path("recent/", RecentReleaseNotificationsView.as_view(), name="release-recent"),
    path(
        "clear/",
        ClearRecentReleaseNotificationsView.as_view(),
        name="release-clear-recent",
    ),
    path("current/", CurrentReleaseNotificationView.as_view(), name="release-current"),
    path(
        "<int:release_id>/read/",
        ReadReleaseNotificationView.as_view(),
        name="release-read",
    ),
    path(
        "<int:release_id>/clear/",
        ClearReleaseNotificationView.as_view(),
        name="release-clear",
    ),
]
