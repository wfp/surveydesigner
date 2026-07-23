import pytest
from django_rq import get_queue
from modules.models import Module, Submodule
from modules.views import generate_docx
from rest_framework import status
from rq.job import Job

pytestmark = pytest.mark.django_db


@pytest.fixture
def scoped_modules(organization_1, organization_2):
    module_1 = Module.objects.create(name="ScopedModule1", label="Scoped module 1")
    module_1.organizations.set([organization_1])
    module_2 = Module.objects.create(name="ScopedModule2", label="Scoped module 2")
    module_2.organizations.set([organization_2])
    shared = Module.objects.create(name="ScopedShared", label="Scoped shared")
    shared.organizations.set([organization_1, organization_2])
    submodule_1 = Submodule.objects.create(
        module=module_1, name="ScopedSubmodule1", label="Scoped submodule 1"
    )
    submodule_2 = Submodule.objects.create(
        module=module_2, name="ScopedSubmodule2", label="Scoped submodule 2"
    )
    shared_submodule = Submodule.objects.create(
        module=shared, name="ScopedSharedSubmodule", label="Scoped shared submodule"
    )
    return module_1, module_2, shared, submodule_1, submodule_2, shared_submodule


def _scope(client, *organizations):
    client.credentials(
        HTTP_SURVEY_DESIGNER_ORGANIZATIONS=",".join(
            str(organization.pk) for organization in organizations
        )
    )


def _generation_payload(submodule):
    return {
        "name": "Scoped survey",
        "submodules": [submodule.pk],
        "submodules_order": [submodule.pk],
        "sub_questions": [],
        "languages": [],
        "survey_type": None,
    }


def test_selected_scope_not_user_assignment_controls_module_content(
    api_client, user, organization_1, organization_2, scoped_modules
):
    user.organization = organization_1
    user.save(update_fields=["organization"])
    api_client.force_authenticate(user)
    _scope(api_client, organization_2)
    module_1, module_2, shared, *_ = scoped_modules

    response = api_client.get("/api/modules/")

    assert response.status_code == status.HTTP_200_OK
    assert {module["id"] for module in response.data} == {module_2.pk, shared.pk}
    assert module_1.pk not in {module["id"] for module in response.data}


def test_empty_scope_returns_empty_organization_content_lists(
    api_client_authenticated, scoped_modules
):
    assert api_client_authenticated.get("/api/modules/").data == []
    assert api_client_authenticated.get("/api/submodules/").data == []
    assert api_client_authenticated.get("/api/indicators/").data == []


def test_multiple_organizations_use_intersection_and_allow_extra_associations(
    api_client_authenticated, organization_1, organization_2, scoped_modules
):
    _scope(api_client_authenticated, organization_2, organization_1)
    shared = scoped_modules[2]

    response = api_client_authenticated.get("/api/modules/")

    assert response.status_code == status.HTTP_200_OK
    assert [module["id"] for module in response.data] == [shared.pk]


def test_cached_content_varies_by_authenticated_user_and_normalized_scope(
    api_client_authenticated, organization_1, organization_2, scoped_modules
):
    _scope(api_client_authenticated, organization_2, organization_1)

    response = api_client_authenticated.get("/api/modules/")

    vary_headers = {value.strip() for value in response.headers["Vary"].split(",")}
    assert "Cookie" in vary_headers
    assert "Authorization" in vary_headers
    assert "Survey-Designer-Organizations" in vary_headers


def test_assigned_admin_can_queue_generation_for_foreign_selected_scope(
    mocker,
    api_client,
    user,
    organization_1,
    organization_2,
    scoped_modules,
):
    user.organization = organization_1
    user.save(update_fields=["organization"])
    api_client.force_authenticate(user)
    _scope(api_client, organization_2)
    foreign_submodule = scoped_modules[4]
    mocker.patch("django_rq.get_queue", return_value=get_queue("generate-doc"))
    mock_enqueue = mocker.patch("rq.Queue.enqueue")
    job = mocker.Mock(spec=Job, id="scope-job")
    job.get_status.return_value = "queued"
    job.get_position.return_value = None
    mock_enqueue.return_value = job

    response = api_client.post(
        "/api/generate-doc/", _generation_payload(foreign_submodule), format="json"
    )

    assert response.status_code == status.HTTP_200_OK
    mock_enqueue.assert_called_once()
    assert mock_enqueue.call_args.args[0] is generate_docx


@pytest.mark.parametrize(
    "endpoint", ["/api/generate/", "/api/preview/", "/api/upload/"]
)
def test_out_of_scope_content_fails_before_generation_or_external_side_effects(
    mocker,
    api_client_authenticated,
    organization_1,
    scoped_modules,
    endpoint,
):
    _scope(api_client_authenticated, organization_1)
    foreign_submodule = scoped_modules[4]
    payload = _generation_payload(foreign_submodule)
    if endpoint == "/api/upload/":
        payload.update({"id": 999999, "project_id": 1})
    generate = mocker.patch("modules.views.get_xlsx_from_data")
    external = mocker.patch("modules.views.requests.post")
    storage = mocker.patch("modules.views.Survey.objects.create")

    response = api_client_authenticated.post(endpoint, payload, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    generate.assert_not_called()
    external.assert_not_called()
    storage.assert_not_called()


def test_invalid_organization_fails_before_queueing(
    mocker, api_client_authenticated, scoped_modules
):
    api_client_authenticated.credentials(HTTP_SURVEY_DESIGNER_ORGANIZATIONS="999999")
    enqueue = mocker.patch("rq.Queue.enqueue")

    response = api_client_authenticated.post(
        "/api/generate-doc/",
        _generation_payload(scoped_modules[3]),
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    enqueue.assert_not_called()


def test_malformed_organization_fails_before_queueing(
    mocker, api_client_authenticated, scoped_modules
):
    api_client_authenticated.credentials(HTTP_SURVEY_DESIGNER_ORGANIZATIONS="1,invalid")
    enqueue = mocker.patch("rq.Queue.enqueue")

    response = api_client_authenticated.post(
        "/api/generate-doc/",
        _generation_payload(scoped_modules[3]),
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    enqueue.assert_not_called()
