import pytest
from accounts.models import User
from organization.models import Organization

pytestmark = pytest.mark.django_db


def test_display_name(user):
    assert user.display_name() == "test"


def test_get_full_name(user):
    assert user.get_full_name() == "test@example.com"


def test_get_short_name_name(user):
    assert user.display_name() == "test"


def test_save_lowercase_email():
    user = User.objects.create(email="UPPERCASE@example.COM")
    assert user.email == "uppercase@example.com"


def test_organization_assigned_on_create():
    user = User.objects.create(email="test_email@wfp.org")
    assert user.organization == Organization.objects.get(
        allowed_domains__contains=["wfp.org"]
    )
