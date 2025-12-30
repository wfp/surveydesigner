from unittest import mock

import pytest
from core.auth.views import (
    OIDCAuthenticationCallbackView,
    OIDCAuthenticationRequestView,
)
from django.conf import settings
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory


@pytest.mark.django_db
class TestOIDCAuthenticationRequestView:
    def test_oidc_authentication_request_view(self):
        view = OIDCAuthenticationRequestView.as_view()
        factory = RequestFactory()
        request = factory.get("/auth/login/")
        get_response = mock.MagicMock()
        middleware_instance = SessionMiddleware(get_response)
        middleware_instance.process_request(request)

        response = view(request)

        assert response.status_code == 302  # Expecting a redirection
        assert response.url.startswith(settings.OIDC_AUTHORIZATION_ENDPOINT)


@pytest.mark.django_db
class TestOIDCAuthenticationCallbackView:
    def test_oidc_authentication_callback_view_error(self, user):
        view = OIDCAuthenticationCallbackView.as_view()
        factory = RequestFactory()
        request = factory.get("/auth/callback/")
        request.GET = {"error": "some_error"}
        get_response = mock.MagicMock()
        middleware_instance = SessionMiddleware(get_response)
        middleware_instance.process_request(request)
        request.user = user

        response = view(request)

        assert response.status_code == 302
        assert response.url == "/"

    def test_oidc_authentication_callback_view_invalid_verifier(self):
        view = OIDCAuthenticationCallbackView.as_view()
        factory = RequestFactory()
        request = factory.get("/auth/callback/")
        request.GET = {"code": "mock_code"}

        # Simulate the absence of code_verifier in the session
        request.session = {}

        response = view(request)

        assert response.status_code == 302  # Expecting a redirection
        assert response.url == "/"
