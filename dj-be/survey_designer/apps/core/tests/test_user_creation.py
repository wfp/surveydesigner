import pytest
from accounts.models import User
from core.auth.backends import OIDCAuthenticationBackend
from django.test import TestCase


@pytest.mark.django_db
def test_create_wfp_user():
    email = "test@wfp.org"
    user = OIDCAuthenticationBackend.create_user(email)

    created_user = User.objects.get(email=email)

    assert user == created_user
    assert user.is_staff
    assert not user.is_superuser
    assert user.groups.filter(name="Read Only").exists()


@pytest.mark.django_db
def test_create_unicef_user():
    email = "test@unicef.org"
    user = OIDCAuthenticationBackend.create_user(email)

    created_user = User.objects.get(email=email)

    assert user == created_user
    assert user.is_staff
    assert not user.is_superuser
    assert user.groups.filter(name="Read Only").exists()


@pytest.mark.django_db
def test_create_non_wfp_user():
    email = "test@example.com"
    user = OIDCAuthenticationBackend.create_user(email)
    created_user = User.objects.get(email=email)

    assert user == created_user
    assert user.is_staff
    assert not user.is_superuser
    assert user.groups.filter(name="Read Only").exists()


@pytest.mark.django_db
def test_get_or_create_user_reuses_existing_user_for_case_variant_email():
    existing_user = User.objects.create_user(email="mixed.case@example.com")

    user = OIDCAuthenticationBackend().get_or_create_user(
        {"email": "Mixed.Case@Example.com"}
    )

    assert user == existing_user
    assert user.email == "mixed.case@example.com"
    assert User.objects.filter(email="mixed.case@example.com").count() == 1


class TestCaseInsensitiveUserCreation(TestCase):
    def test_get_or_create_user_reuses_existing_user_for_case_variant_email(self):
        existing_user = User.objects.create_user(email="mixed.case@example.com")

        user = OIDCAuthenticationBackend().get_or_create_user(
            {"email": "Mixed.Case@Example.com"}
        )

        self.assertEqual(user.pk, existing_user.pk)
        self.assertEqual(user.email, "mixed.case@example.com")
        self.assertEqual(User.objects.filter(email="mixed.case@example.com").count(), 1)
