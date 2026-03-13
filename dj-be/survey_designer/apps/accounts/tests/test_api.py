import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .factories import UserAPIKeyFactory, UserAPISiteFactory


@pytest.mark.django_db
class TestUserAPIKeyViewSet:
    def test_list_user_api_keys_unauthenticated(self, api_client):
        response = api_client.get("/api/accounts/api-keys/")
        assert response.status_code == 403
        assert response.json() == {
            "detail": "Authentication credentials were not provided."
        }

    def test_retrieve_user_api_key_denied(self, logged_admin_client, user):
        api_key = UserAPIKeyFactory(user=user)
        response = logged_admin_client.get(f"/api/accounts/api-keys/{api_key.id}/")
        assert response.status_code == 404
        assert response.json() == {"detail": "No UserAPIKey matches the given query."}

    def test_list_user_api_keys(self, api_client, user):
        api_key = UserAPIKeyFactory(user=user)
        api_client.login(email=user.email, password="test_user")
        response = api_client.get("/api/accounts/api-keys/")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["id"] == api_key.id

    def test_retrieve_user_api_key(self, api_client, user):
        api_key = UserAPIKeyFactory(user=user)
        api_client.login(email=user.email, password="test_user")
        response = api_client.get(f"/api/accounts/api-keys/{api_key.id}/")
        assert response.status_code == 200
        assert response.json()["id"] == api_key.id

    def test_create_user_api_key(self, api_client, user):
        api_client.login(email=user.email, password="test_user")
        site = UserAPISiteFactory()
        data = {"site": site.id, "name": "test", "raw_key": "test_key"}
        response = api_client.post(
            "/api/accounts/api-keys/",
            data=data,
            format="json",
        )
        assert response.status_code == 201
        assert response.json()["site"] == site.id
        assert response.json()["name"] == "test"
        assert response.json()["raw_key"] == "test_key"

    def test_create_user_api_key_rejects_case_variant_duplicate_name(
        self, api_client, user
    ):
        api_client.login(email=user.email, password="test_user")
        site = UserAPISiteFactory()
        UserAPIKeyFactory(user=user, site=site, name="ProdKey")

        response = api_client.post(
            "/api/accounts/api-keys/",
            data={"site": site.id, "name": "prodkey", "raw_key": "test_key_2"},
            format="json",
        )

        assert response.status_code == 400
        assert response.json()[settings.REST_FRAMEWORK["NON_FIELD_ERRORS_KEY"]] == [
            "Please provide a unique name."
        ]

    def test_update_user_api_key(self, api_client, user):
        api_key = UserAPIKeyFactory(user=user)
        api_client.login(email=user.email, password="test_user")
        data = {"site": api_key.site.id, "name": "test", "raw_key": "test_key"}
        response = api_client.put(
            f"/api/accounts/api-keys/{api_key.id}/",
            data=data,
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["name"] == "test"
        assert response.json()["raw_key"] == "test_key"

    def test_patch_user_api_key(self, api_client, user):
        api_key = UserAPIKeyFactory(user=user)
        api_client.login(email=user.email, password="test_user")
        data = {
            "name": "test",
        }
        response = api_client.patch(
            f"/api/accounts/api-keys/{api_key.id}/",
            data=data,
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["name"] == "test"


@pytest.mark.django_db
class TestAuthToken:
    def test_create_token(self, api_client, user):
        response = api_client.post(
            "/api/accounts/api-token-auth/",
            {"username": user.email, "password": "test_user"},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["token"]
        assert response.json()["user_id"] == user.id
        assert response.json()["email"] == user.email


@pytest.mark.django_db
class TestUserDetailAPI:
    def test_get_user(self, api_client, user):
        api_client.login(email=user.email, password="test_user")
        response = api_client.get(
            "/api/accounts/user/",
        )
        assert response.status_code == 200
        assert response.json()["email"] == user.email


@pytest.mark.django_db
class TestUserAPISiteAPI:
    def test_list_sites(self, api_client, user):
        api_client.login(email=user.email, password="test_user")
        response = api_client.get(
            "/api/accounts/api-sites/",
        )
        assert response.status_code == 200


class TestCaseInsensitiveUserAPIKeyViewSet(TestCase):
    def setUp(self):
        self.api_client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="api@example.com", password="test_user"
        )
        self.api_client.login(email=self.user.email, password="test_user")

    def test_create_user_api_key_rejects_case_variant_duplicate_name(self):
        site = UserAPISiteFactory()
        UserAPIKeyFactory(user=self.user, site=site, name="ProdKey")

        response = self.api_client.post(
            "/api/accounts/api-keys/",
            data={"site": site.id, "name": "prodkey", "raw_key": "test_key_2"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()[settings.REST_FRAMEWORK["NON_FIELD_ERRORS_KEY"]],
            ["Please provide a unique name."],
        )
