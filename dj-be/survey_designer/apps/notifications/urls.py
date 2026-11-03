from django.urls import path

from . import views

urlpatterns = [
    path(
        "notifications/", views.NotificationListView.as_view(), name="notification-list"
    ),
    path(
        "notifications/<int:pk>/",
        views.NotificationDetailView.as_view(),
        name="notification-detail",
    ),
    path(
        "notifications/<int:pk>/acknowledge/",
        views.NotificationAcknowledgeView.as_view(),
        name="notification-acknowledge",
    ),
    path("releases/latest/", views.LatestReleaseView.as_view(), name="release-latest"),
    path(
        "releases/<int:pk>/", views.ReleaseDetailView.as_view(), name="release-detail"
    ),
]
