import pytest
from accounts.const import PermissionGroups
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import status
from surveys.models import SurveyCategory, SurveyMode, SurveyType

pytestmark = pytest.mark.django_db


def _create_global_admin(email="global-survey-admin@example.com"):
    user = get_user_model().objects.create_user(
        email=email,
        password="test_user",
        is_staff=True,
    )
    group, _ = Group.objects.get_or_create(name=PermissionGroups.GLOBAL_ADMINS)
    user.groups.add(group)
    return user


@pytest.fixture
def scoped_survey_data(organization_1, organization_2):
    category_org_1 = SurveyCategory.objects.create(
        name="CategoryOrg1", label="Category Org 1"
    )
    category_org_1.organizations.set([organization_1])
    category_org_2 = SurveyCategory.objects.create(
        name="CategoryOrg2", label="Category Org 2"
    )
    category_org_2.organizations.set([organization_2])
    category_shared = SurveyCategory.objects.create(
        name="CategoryShared", label="Category Shared"
    )
    category_shared.organizations.set([organization_1, organization_2])

    type_org_1 = SurveyType.objects.create(
        category=category_org_1, name="TypeOrg1", label="Type Org 1"
    )
    type_org_1.organizations.set([organization_1])
    type_org_2 = SurveyType.objects.create(
        category=category_org_2, name="TypeOrg2", label="Type Org 2"
    )
    type_org_2.organizations.set([organization_2])
    type_shared = SurveyType.objects.create(
        category=category_shared, name="TypeShared", label="Type Shared"
    )
    type_shared.organizations.set([organization_1, organization_2])

    mode_org_1 = SurveyMode.objects.create(name="ModeOrg1", label="Mode Org 1")
    mode_org_1.organizations.set([organization_1])
    mode_org_2 = SurveyMode.objects.create(name="ModeOrg2", label="Mode Org 2")
    mode_org_2.organizations.set([organization_2])
    mode_shared = SurveyMode.objects.create(name="ModeShared", label="Mode Shared")
    mode_shared.organizations.set([organization_1, organization_2])

    return {
        "category_org_1": category_org_1,
        "category_org_2": category_org_2,
        "category_shared": category_shared,
        "type_org_1": type_org_1,
        "type_org_2": type_org_2,
        "type_shared": type_shared,
        "mode_org_1": mode_org_1,
        "mode_org_2": mode_org_2,
        "mode_shared": mode_shared,
    }


def _authenticate_for_organization(api_client, user, organization):
    user.organization = organization
    user.save(update_fields=["organization"])
    api_client.force_authenticate(user)


def test_survey_api_uses_selected_organization_scope(
    api_client, user, organization_1, organization_2, scoped_survey_data
):
    _authenticate_for_organization(api_client, user, organization_1)
    api_client.credentials(HTTP_SURVEY_DESIGNER_ORGANIZATIONS=str(organization_1.id))

    response = api_client.get("/api/surveys/")

    assert response.status_code == status.HTTP_200_OK
    assert {category["id"] for category in response.data["categories"]} == {
        scoped_survey_data["category_org_1"].id,
        scoped_survey_data["category_shared"].id,
    }
    shared_category = next(
        category
        for category in response.data["categories"]
        if category["id"] == scoped_survey_data["category_shared"].id
    )
    assert {
        organization["id"] for organization in shared_category["organizations"]
    } == {
        organization_1.id,
        organization_2.id,
    }
    org_1_category = next(
        category
        for category in response.data["categories"]
        if category["id"] == scoped_survey_data["category_org_1"].id
    )
    assert [survey_type["id"] for survey_type in org_1_category["survey_types"]] == [
        scoped_survey_data["type_org_1"].id
    ]
    assert {mode["id"] for mode in response.data["modes"]} == {
        scoped_survey_data["mode_org_1"].id,
        scoped_survey_data["mode_shared"].id,
    }


def test_survey_api_allows_organization_outside_user_assignment(
    api_client, user, organization_1, organization_2, scoped_survey_data
):
    _authenticate_for_organization(api_client, user, organization_1)
    api_client.credentials(HTTP_SURVEY_DESIGNER_ORGANIZATIONS=str(organization_2.id))

    response = api_client.get("/api/surveys/")

    assert response.status_code == status.HTTP_200_OK
    assert {category["id"] for category in response.data["categories"]} == {
        scoped_survey_data["category_org_2"].id,
        scoped_survey_data["category_shared"].id,
    }


def test_survey_api_multiple_selected_organizations_use_union_scope(
    api_client, user, organization_1, organization_2, scoped_survey_data
):
    _authenticate_for_organization(api_client, user, organization_1)
    api_client.credentials(
        HTTP_SURVEY_DESIGNER_ORGANIZATIONS=f"{organization_1.id},{organization_2.id}"
    )

    response = api_client.get("/api/surveys/")

    assert response.status_code == status.HTTP_200_OK
    assert {category["id"] for category in response.data["categories"]} == {
        scoped_survey_data["category_org_1"].id,
        scoped_survey_data["category_org_2"].id,
        scoped_survey_data["category_shared"].id,
    }
    assert {mode["id"] for mode in response.data["modes"]} == {
        scoped_survey_data["mode_org_1"].id,
        scoped_survey_data["mode_org_2"].id,
        scoped_survey_data["mode_shared"].id,
    }


def test_survey_api_allows_orgless_user_non_empty_organization_header(
    api_client_authenticated, organization_1, scoped_survey_data
):
    api_client_authenticated.credentials(
        HTTP_SURVEY_DESIGNER_ORGANIZATIONS=str(organization_1.id)
    )

    response = api_client_authenticated.get("/api/surveys/")

    assert response.status_code == status.HTTP_200_OK
    assert {category["id"] for category in response.data["categories"]} == {
        scoped_survey_data["category_org_1"].id,
        scoped_survey_data["category_shared"].id,
    }


def test_survey_api_orgless_user_empty_scope_returns_no_survey_data(
    api_client_authenticated, scoped_survey_data
):
    response = api_client_authenticated.get("/api/surveys/")

    assert response.status_code == status.HTTP_200_OK
    assert response.data == {"categories": [], "modes": []}


def test_survey_api_rejects_malformed_organization_header(
    api_client, user, organization_1, scoped_survey_data
):
    _authenticate_for_organization(api_client, user, organization_1)
    api_client.credentials(
        HTTP_SURVEY_DESIGNER_ORGANIZATIONS=f"{organization_1.id},bad"
    )

    response = api_client.get("/api/surveys/")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_survey_api_rejects_nonexistent_organization(
    api_client_authenticated, scoped_survey_data
):
    api_client_authenticated.credentials(HTTP_SURVEY_DESIGNER_ORGANIZATIONS="999999")

    response = api_client_authenticated.get("/api/surveys/")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_survey_api_global_admin_can_request_all_organizations(
    api_client, organization_1, organization_2, scoped_survey_data
):
    api_client.force_authenticate(_create_global_admin())
    api_client.credentials(
        HTTP_SURVEY_DESIGNER_ORGANIZATIONS=f"{organization_1.id},{organization_2.id}"
    )

    response = api_client.get("/api/surveys/")

    assert response.status_code == status.HTTP_200_OK
    assert {category["id"] for category in response.data["categories"]} == {
        scoped_survey_data["category_org_1"].id,
        scoped_survey_data["category_org_2"].id,
        scoped_survey_data["category_shared"].id,
    }
    assert {mode["id"] for mode in response.data["modes"]} == {
        scoped_survey_data["mode_org_1"].id,
        scoped_survey_data["mode_org_2"].id,
        scoped_survey_data["mode_shared"].id,
    }
