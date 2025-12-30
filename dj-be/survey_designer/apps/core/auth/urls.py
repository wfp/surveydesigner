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
