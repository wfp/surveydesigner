import pytest
from change_requests.admin import ChangeRequestAdmin
from change_requests.models import ChangeRequest
from core.utils import get_model_admin_base_url
from django.contrib.admin import AdminSite
from django.urls import reverse


@pytest.fixture
def admin_site():
    return AdminSite()


@pytest.fixture
def change_request_admin(admin_site):
    return ChangeRequestAdmin(ChangeRequest, admin_site)


def test_change_request_list_view(
    logged_admin_client,
    change_request_1,
):
    url = get_model_admin_base_url(ChangeRequest, "_changelist")
    response = logged_admin_client.get(url)
    assert response.status_code == 200


def test_change_request_edit_view(
    logged_admin_client,
    change_request_1,
):
    url = get_model_admin_base_url(ChangeRequest, "_change", [change_request_1.id])
    response = logged_admin_client.get(url)
    assert response.status_code == 200


def test_approve_button_renders_valid_anchor(
    request_factory,
    change_request_admin,
    change_request_1,
    admin,
):
    request = request_factory.get(reverse("admin:change_requests_changerequest_changelist"))
    request.user = admin
    change_request_admin.request = request

    response = change_request_admin.approve_button(change_request_1)

    assert "href=" in response
    assert response.endswith("</a>")
    assert "</button>" not in response
