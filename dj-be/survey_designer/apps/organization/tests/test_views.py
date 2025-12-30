import pytest
from organization.models import Organization
from organization.tests.factories import OrganizationFactory
from rest_framework import status

pytestmark = pytest.mark.django_db


def test_fetch_all_organizations(logged_client):
    test_organizations_count = 3
    default_organizations_count = Organization.objects.all().count()
    for index in range(test_organizations_count):
        OrganizationFactory(name=f"test_{index}")
    response = logged_client.get("/api/organizations/")

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == test_organizations_count + default_organizations_count
