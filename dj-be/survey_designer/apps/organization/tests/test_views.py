import pytest
from accounts.const import PermissionGroups
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from organization.models import Organization
from organization.tests.factories import OrganizationFactory
from rest_framework import status

pytestmark = pytest.mark.django_db


def _create_global_admin(email="global-admin@example.com", password="test_user"):
    user = get_user_model().objects.create_user(
        email=email,
        password=password,
        is_staff=True,
    )
    group, _ = Group.objects.get_or_create(name=PermissionGroups.GLOBAL_ADMINS)
    user.groups.add(group)
    return user


def test_fetch_organizations_returns_only_user_organization(
    django_client, user, organization_1, organization_2
):
    user.organization = organization_1
    user.save(update_fields=["organization"])
    django_client.login(email="test@example.com", password="test_user")

    response = django_client.get("/api/organizations/")

    assert response.status_code == status.HTTP_200_OK
    assert [organization["id"] for organization in response.data] == [organization_1.id]


def test_fetch_organizations_orgless_user_returns_empty(logged_client):
    OrganizationFactory(name="test_1")
    OrganizationFactory(name="test_2")

    response = logged_client.get("/api/organizations/")

    assert response.status_code == status.HTTP_200_OK
    assert response.data == []


def test_fetch_organizations_global_admin_returns_all(django_client):
    organization_1 = OrganizationFactory(name="test_1")
    organization_2 = OrganizationFactory(name="test_2")
    global_admin = _create_global_admin()
    django_client.login(email=global_admin.email, password="test_user")

    response = django_client.get("/api/organizations/")

    assert response.status_code == status.HTTP_200_OK
    assert {organization["id"] for organization in response.data} == set(
        Organization.objects.values_list("id", flat=True)
    )
    assert {organization_1.id, organization_2.id}.issubset(
        {organization["id"] for organization in response.data}
    )
