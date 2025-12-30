import pytest
from accounts.models import User
from core.auth.backends import OIDCAuthenticationBackend


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
