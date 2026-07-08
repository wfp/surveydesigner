from django.conf import settings
from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("login/", views.OIDCAuthenticationRequestView.as_view(), name="oidc-login"),
    path("logout/", views.LogoutView.as_view(), name="oidc-logout"),
    path(
        "callback/",
        views.OIDCAuthenticationCallbackView.as_view(),
        name="oidc-callback",
    ),
]

if settings.ENABLE_E2E_AUTH:
    urlpatterns.append(
        path("e2e-login/", views.E2ELoginView.as_view(), name="e2e-login")
    )
