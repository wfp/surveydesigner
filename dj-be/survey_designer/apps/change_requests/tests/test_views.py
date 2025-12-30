from accounts.const import PermissionGroups
from change_requests.const import StatusType
from change_requests.models import ChangeRequest
from django.contrib.auth.models import Group
from django.shortcuts import reverse


def test_submit_change_request_view_get(
    logged_admin_client,
    change_request_1,
):
    url = reverse("submit_change_request")
    response = logged_admin_client.get(url)
    assert response.status_code == 200


def test_submit_single_organization_change_request_view_post(
    admin, logged_admin_client
):
    description = "test description"
    admin_organization_id = 1
    admin.groups.add(Group.objects.get(name=PermissionGroups.CHANGE_REQUESTS))
    admin.save()
    with open(
        "./survey_designer/apps/questions/tests/files/questions.xlsx", "rb"
    ) as file:
        url = reverse("submit_change_request")
        response = logged_admin_client.post(
            url,
            {
                "file": file,
                "description": description,
                "organizations": [admin_organization_id],
            },
            follow=True,
        )
        assert response.status_code == 200
        created_cr = ChangeRequest.objects.last()
        assert created_cr.description == description
        assert created_cr.created_by == admin
        assert created_cr.organizations.all().count() == 1
        assert created_cr.organizations.first().id == admin_organization_id


def test_submit_multi_organization_change_request_view_post(admin, logged_admin_client):
    description = "test description"
    organization_ids = [1, 2]
    admin.groups.add(Group.objects.get(name=PermissionGroups.CHANGE_REQUESTS))
    admin.save()
    with open(
        "./survey_designer/apps/questions/tests/files/questions.xlsx", "rb"
    ) as file:
        url = reverse("submit_change_request")
        response = logged_admin_client.post(
            url,
            {
                "file": file,
                "description": description,
                "organizations": organization_ids,
            },
            follow=True,
        )
        assert response.status_code == 200
        created_cr = ChangeRequest.objects.last()
        assert created_cr.description == description
        assert created_cr.created_by == admin
        assert created_cr.organizations.all().count() == len(organization_ids)
        assert (
            list(created_cr.organizations.all().values_list("id", flat=True))
            == organization_ids
        )


def test_approve_change_request_view_get(logged_admin_client, change_request_1):
    url = reverse("approve_change_request", args=[change_request_1.id])
    response = logged_admin_client.get(url)
    assert response.status_code == 200


def test_approve_change_request_view_post(logged_admin_client, change_request_1):
    cr_response = "test response"
    url = reverse("approve_change_request", args=[change_request_1.id])
    response = logged_admin_client.post(url, {"response": cr_response}, follow=True)
    assert response.status_code == 200
    change_request_1.refresh_from_db()
    assert change_request_1.status == StatusType.APPROVED
    assert change_request_1.response == cr_response
