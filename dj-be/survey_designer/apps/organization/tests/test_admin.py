from core.utils import get_model_admin_base_url
from organization.models import Organization
from rest_framework import status


def test_admin_change_form(logged_admin_client, organization_1):
    url = get_model_admin_base_url(Organization, "_change", [organization_1.id])
    response = logged_admin_client.get(url)
    assert response.status_code == status.HTTP_200_OK


def test_admin_change_form_no_permission(logged_client, organization_1):
    url = get_model_admin_base_url(Organization, "_change", [organization_1.id])
    response = logged_client.get(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN
