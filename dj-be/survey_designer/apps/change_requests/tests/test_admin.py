from change_requests.models import ChangeRequest
from core.utils import get_model_admin_base_url


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
