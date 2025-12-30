from change_requests import views as requests_views
from core.auth.views import LogoutView, OIDCAuthenticationRequestView
from django.conf import settings
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path
from django.utils.translation import gettext_lazy as _
from django.views.static import serve
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from questions import views
from questions.views import IndicatorAutocomplete

admin.site.index_title = _("Survey Designer Admin")
admin.site.site_header = _("Survey Designer Admin")
admin.site.site_title = _("Survey Designer Admin")
admin.site.enable_nav_sidebar = False

api_urlpatterns = [
    path("accounts/", include("accounts.urls")),
    path("", include("modules.urls")),
    path("", include("saved_surveys.urls")),
    path("", include("surveys.urls")),
    path("", include("organization.urls")),
    path("", include("frontend_content.urls")),
    path(
        "repeat-section-autocomplete/",
        views.RepeatSectionAutocomplete.as_view(),
        name="repeat-section-autocomplete",
    ),
    path(
        "indicator-autocomplete/",
        IndicatorAutocomplete.as_view(),
        name="indicator-autocomplete",
    ),
    path(
        "language-autocomplete/",
        views.LanguageAutocomplete.as_view(),
        name="language-autocomplete",
    ),
]

admin_urlpatterns = [
    path(
        "questions/constraint/",
        views.ConstraintCreateView.as_view(),
        name="constraint",
    ),
    path(
        "questions/relevant/",
        views.RelevantCreateView.as_view(),
        name="relevant",
    ),
    path(
        "questions/import/",
        views.UploadQuestionsView.as_view(),
        name="import",
    ),
    path(
        "change-requests/submit/",
        requests_views.SubmitChangeRequestView.as_view(),
        name="submit_change_request",
    ),
    path(
        "change-requests/approve/<int:pk>/",
        requests_views.ApproveChangeRequestView.as_view(),
        name="approve_change_request",
    ),
    path("dynamic_raw_id/", include("dynamic_raw_id.urls")),
    path("rq/", include("django_rq.urls")),
    path("", admin.site.urls),
]

if settings.IDENTITY_PROVIDER:
    admin_urlpatterns.append(
        path("login/", OIDCAuthenticationRequestView.as_view(), name="admin-login")
    )
    admin_urlpatterns.append(path("logout/", LogoutView.as_view(), name="admin-logout"))


urlpatterns = [
    path("health/", include("health_check.urls")),
    path("auth/", include("core.auth.urls")),
    path("admin/", include(admin_urlpatterns)),
    path("api/", include((api_urlpatterns, "api"), namespace="v1")),
    path(
        "robots.txt",
        lambda x: HttpResponse("User-Agent: *\nDisallow: /", content_type="text/plain"),
        name="robots_file",
    ),
    path(
        "manifest.json",
        serve,
        {"document_root": settings.STATIC_ROOT, "path": "manifest.webmanifest"},
    ),
    path(
        "favicon.ico",
        serve,
        {"document_root": settings.STATIC_ROOT, "path": "favicon.ico"},
    ),
    path(
        "serviceworker.js",
        serve,
        {"document_root": settings.STATIC_ROOT, "path": "sw.js"},
    ),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    # Optional UI:
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    path("martor/", include("martor.urls")),
    # path("silk/", include("silk.urls", namespace="silk")),
]
