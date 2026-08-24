import io
import json
import uuid
from xml.etree import ElementTree as ET

import pytest
from accounts.const import UserAPISiteAPITypes
from accounts.models import UserAPIKey, UserAPISite
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django_rq import get_queue
from documents.models import Document
from modules.models import (
    IndicatorMapping,
    IndicatorMappingSurveyAttribute,
    IndicatorMappingSurveyMode,
    IndicatorMappingSurveyType,
    SubmoduleRequiredGroup,
)
from modules.views import generate_docx
from questions.const import QuestionType
from questions.models import (
    RootQuestion,
    RootQuestionTranslation,
    SubQuestion,
    SubQuestionTranslation,
)
from rest_framework import status
from rq.exceptions import NoSuchJobError
from rq.job import Job
from surveys.models import Survey


class FakeFieldFile:
    def __init__(self, name, content=b"name\nvalue\n"):
        self.name = f"question/{name}"
        self._content = content
        self.file = None

    def open(self, mode="rb"):
        self.file = io.BytesIO(self._content)
        self.file.seek(0)
        return self.file

    def close(self):
        if self.file:
            self.file.seek(0)


def build_stub_xls_form(external_files):
    class StubXLSForm:
        id_name = "test-form-id"

        def __init__(self, files):
            self.external_files = files

        def generate(self):
            return b"fake-xlsx"

    return StubXLSForm(external_files)


def mock_successful_xml_conversion(mocker, xml=None):
    conversion = mocker.Mock()
    conversion.run.return_value = xml or (
        '<h:html xmlns:h="http://www.w3.org/1999/xhtml" '
        'xmlns:xf="http://www.w3.org/2002/xforms">'
        "<h:head><xf:model><xf:instance><data/></xf:instance>"
        "</xf:model></h:head><h:body/></h:html>"
    )
    conversion.warnings = []
    conversion.errors = []
    mocker.patch("modules.views.XMLConversion", return_value=conversion)
    return conversion


@pytest.fixture(autouse=True)
def selected_organization_header(
    logged_admin_client, api_client_authenticated_admin, organization_1
):
    header_value = str(organization_1.pk)
    logged_admin_client.defaults["HTTP_SURVEY_DESIGNER_ORGANIZATIONS"] = header_value
    api_client_authenticated_admin.credentials(
        HTTP_SURVEY_DESIGNER_ORGANIZATIONS=header_value
    )


@pytest.fixture()
def moda_api_key(admin):
    site, created = UserAPISite.objects.get_or_create(
        name="MODA DEV",
        defaults={
            "api_type": UserAPISiteAPITypes.ONA,
            "url": "https://api.dev.moda.wfp.org/",
        },
    )
    if not created:
        site.api_type = UserAPISiteAPITypes.ONA
        site.url = "https://api.dev.moda.wfp.org/"
        site.save(update_fields=["api_type", "url"])

    api_key = UserAPIKey.objects.create(
        user=admin, site=site, name=f"Moda Token {uuid.uuid4()}"
    )
    api_key.set_key("test-token")
    api_key.save()
    return api_key


def test_module_view_set_list(
    logged_admin_client, submodule_1, root_question_1, root_question_2, root_question_3
):
    submodule_1.module.relevant = f"${{{root_question_1.name}}} > 0"
    submodule_1.module.save()

    url = "/api/modules/"
    response = logged_admin_client.get(url)
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["id"] == submodule_1.module.id
    assert response.json()[0]["relevant"] == submodule_1.module.relevant
    assert response.json()[0]["submodules"][0]["id"] == submodule_1.id


@pytest.mark.django_db
@pytest.mark.parametrize(
    "filter_params,expected_submodules",
    [
        # Scenario A
        (
            "type={survey_type_1_id}",
            ["submodule_6", "submodule_10", "submodule_11"],
        ),
        # Scenario B
        (
            "type={survey_type_1_id}&mode={survey_mode_1_id}",
            ["submodule_10", "submodule_11"],
        ),
        # Scenario C_1
        (
            "type={survey_type_1_id}&attributes={survey_attribute_1_id}",
            ["submodule_1", "submodule_6", "submodule_10", "submodule_11"],
        ),
        # Scenario C_2
        (
            "type={survey_type_1_id}&attributes={survey_attribute_2_id}",
            ["submodule_6", "submodule_10", "submodule_11", "submodule_12a"],
        ),
        # Scenario D
        (
            "",
            [
                "submodule_1",
                "submodule_2",
                "submodule_3",
                "submodule_4",
                "submodule_5",
                "submodule_6",
                "submodule_7",
                "submodule_8",
                "submodule_9",
                "submodule_10",
                "submodule_11",
                "submodule_12a",
                "submodule_12b",
            ],
        ),
        # Scenario E
        (
            "mode={survey_mode_1_id}&attributes={survey_attribute_1_id}",
            ["submodule_7", "submodule_10", "submodule_11"],
        ),
        # # Scenario F
        (
            "attributes={survey_attribute_1_id}",
            [
                "submodule_1",
                "submodule_6",
                "submodule_7",
                "submodule_8",
                "submodule_9",
                "submodule_10",
                "submodule_11",
            ],
        ),
        # Scenario G
        (
            "type={survey_type_1_id}&mode={survey_mode_1_id}&attributes={survey_attribute_1_id}",
            ["submodule_10", "submodule_11"],
        ),
        # # Scenario H
        (
            "type={survey_type_2_id}&mode={survey_mode_1_id}&attributes={survey_attribute_1_id}",
            ["submodule_7"],
        ),
        # Scenario I
        (
            "type={survey_type_1_id}&mode={survey_mode_1_id}&attributes={survey_attribute_1_id},{survey_attribute_2_id}",
            ["submodule_10", "submodule_11", "submodule_12a"],
        ),
        (
            "attributes=",
            [
                "submodule_1",
                "submodule_2",
                "submodule_3",
                "submodule_4",
                "submodule_5",
                "submodule_6",
                "submodule_7",
                "submodule_8",
                "submodule_9",
                "submodule_10",
                "submodule_11",
                "submodule_12a",
                "submodule_12b",
            ],
        ),
    ],
)
def test_module_view_set_filtering(
    logged_admin_client,
    filter_params,
    expected_submodules,
    module_1,
    module_2,
    submodule_1,
    submodule_2,
    submodule_3,
    submodule_4,
    submodule_5,
    submodule_6,
    submodule_7,
    submodule_8,
    submodule_9,
    submodule_10,
    submodule_11,
    submodule_12,
    survey_type_1,
    survey_type_2,
    survey_mode_1,
    survey_mode_2,
    survey_attribute_1,
    survey_attribute_2,
    survey_attribute_3,
):
    # Replace placeholders in filter_params with actual IDs
    filter_params = filter_params.format(
        survey_type_1_id=survey_type_1.id,
        survey_type_2_id=survey_type_2.id,
        survey_mode_1_id=survey_mode_1.id,
        survey_mode_2_id=survey_mode_2.id,
        survey_attribute_1_id=survey_attribute_1.id,
        survey_attribute_2_id=survey_attribute_2.id,
        survey_attribute_3_id=survey_attribute_3.id,
    )

    # Prepare the URL
    url = f"/api/modules/?{filter_params}" if filter_params else "/api/modules/"

    # Perform the request
    response = logged_admin_client.get(url)

    # Verify response status code
    assert response.status_code == 200

    # Parse response data
    response_data = response.json()

    # Collect all submodules from the response
    submodule_ids_in_response = [
        submodule["id"]
        for module in response_data
        for submodule in module["submodules"]
    ]

    # Map expected submodule names to instances
    submodule_fixture_map = {
        "submodule_1": submodule_1,
        "submodule_2": submodule_2,
        "submodule_3": submodule_3,
        "submodule_4": submodule_4,
        "submodule_5": submodule_5,
        "submodule_6": submodule_6,
        "submodule_7": submodule_7,
        "submodule_8": submodule_8,
        "submodule_9": submodule_9,
        "submodule_10": submodule_10,
        "submodule_11": submodule_11,
        # submodule_12 is a list [submodule_12a, submodule_12b]
        "submodule_12a": submodule_12[0],
        "submodule_12b": submodule_12[1],
    }

    # Get the expected submodule IDs
    expected_submodule_ids = [
        submodule_fixture_map[name].id for name in expected_submodules
    ]

    # Assert that the expected submodule IDs match the response
    assert sorted(submodule_ids_in_response) == sorted(expected_submodule_ids)


def test_submodule_view_set_list(logged_admin_client, submodule_1, root_question_1):
    url = "/api/submodules/"
    response = logged_admin_client.get(url)
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == submodule_1.id
    assert response.json()[0]["root_questions"][1]["id"] == root_question_1.id


def test_submodule_view_set_list_with_submodule_params(
    logged_admin_client, submodule_1, root_question_1
):
    url = f"/api/submodules/?submodule_ids={submodule_1.id}"
    response = logged_admin_client.get(url)
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == submodule_1.id


def test_submodule_view_set_list_with_indicator_params(
    logged_admin_client, indicator_1
):
    url = f"/api/submodules/?indicator_ids={indicator_1.id}"
    response = logged_admin_client.get(url)
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert (
        response.json()[0]["id"]
        == indicator_1.questions.last().root_question.submodule.first().id
    )


def test_submodule_view_set_list_with_all_params(
    logged_admin_client, submodule_1, indicator_1
):
    url = f"/api/submodules/?submodule_ids={submodule_1.id}&indicator_ids={indicator_1.id}"
    response = logged_admin_client.get(url)
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == submodule_1.id


def test_submodule_view_set_list_invalid_submodule_ids(logged_admin_client):
    response = logged_admin_client.get("/api/submodules/?submodule_ids=1,bad,3")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {
        "submodule_ids": "This parameter must contain only integers."
    }


def test_submodule_view_set_list_invalid_indicator_ids(logged_admin_client):
    response = logged_admin_client.get("/api/submodules/?indicator_ids=1,bad,3")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {
        "indicator_ids": "This parameter must contain only integers."
    }


def test_submodule_view_set_list_uses_bounded_queries(
    api_client_authenticated_admin,
    submodule_1,
    indicator_1,
    choices_1,
    choices_2,
    suffix_1,
    suffix_2,
    recall_period_1,
    repeat_section_1,
):
    for index in range(5):
        root_question = RootQuestion.objects.create(
            name=f"PerfQuestion{index}",
            label=f"Perf Question {index}",
            type=(
                QuestionType.SELECT_ONE
                if index % 2 == 0
                else QuestionType.SELECT_MULTIPLE
            ),
            choices=choices_1 if index % 2 == 0 else choices_2,
        )
        root_question.submodule.add(submodule_1)
        RootQuestionTranslation.objects.create(
            root_question=root_question,
            language="fr",
            label=f"Perf Question {index} FR",
        )

        sub_question_1 = SubQuestion.objects.create(
            root_question=root_question,
            suffix=suffix_1,
            label=f"Perf SubQuestion {index} A",
        )
        SubQuestionTranslation.objects.create(
            sub_question=sub_question_1,
            language="fr",
            label=f"Perf SubQuestion {index} A FR",
        )

        sub_question_2 = SubQuestion.objects.create(
            root_question=root_question,
            suffix=suffix_2,
            recall_period=recall_period_1,
            label=f"Perf SubQuestion {index} B",
        )
        SubQuestionTranslation.objects.create(
            sub_question=sub_question_2,
            language="fr",
            label=f"Perf SubQuestion {index} B FR",
        )

    SubmoduleRequiredGroup.objects.create(
        submodule=submodule_1,
        required_suffix=suffix_1,
        required_nested_suffix=suffix_2,
        required_recall_period=recall_period_1,
    )

    cache.clear()
    url = f"/api/submodules/?submodule_ids={submodule_1.id}&indicator_ids={indicator_1.id}"

    with CaptureQueriesContext(connection) as queries:
        response = api_client_authenticated_admin.get(url)

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == submodule_1.id
    # Current optimized path is well below this threshold in local profiling.
    assert len(queries) <= 25


def test_indicator_view_set_list(logged_admin_client, indicator_1):
    url = "/api/indicators/"
    response = logged_admin_client.get(url)
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == indicator_1.id


def test_indicator_view_set_list_with_params_type(
    logged_admin_client,
    indicator_1,
    indicator_mapping_survey_type,
    survey_type_1,
):
    indicator_1.mapping = indicator_mapping_survey_type
    indicator_1.save()
    url = f"/api/indicators/?type={survey_type_1.id}"
    response = logged_admin_client.get(url)
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == indicator_1.id
    assert response.json()[0]["is_mandatory"]


def test_indicator_view_set_list_with_params_mode(
    logged_admin_client,
    indicator_1,
    indicator_mapping_survey_mode,
    survey_mode_1,
    indicator_mapping_survey_type,
    survey_type_1,
):
    indicator_1.mapping = indicator_mapping_survey_mode
    indicator_1.save()
    url = f"/api/indicators/?mode={survey_mode_1.id}&type={survey_type_1.id}"
    response = logged_admin_client.get(url)
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == indicator_1.id
    assert response.json()[0]["is_mandatory"]


def test_indicator_view_set_list_with_all_params(
    logged_admin_client,
    indicator_1,
    survey_type_1,
    survey_mode_1,
    survey_attribute_1,
):
    """
    Test that when all parameters are provided, the endpoint returns indicator_1
    and that the attribute mapping (mandatory) makes the indicator appear as mandatory.
    """
    mapping = IndicatorMapping.objects.create()
    st_mapping = IndicatorMappingSurveyType.objects.create(
        indicator_mapping=mapping,
        survey_type=survey_type_1,
        is_mandatory=True,
    )
    IndicatorMappingSurveyMode.objects.create(
        survey_mode=survey_mode_1,
        survey_type=st_mapping,
        is_mandatory=True,
    )
    IndicatorMappingSurveyAttribute.objects.create(
        indicator_mapping=mapping,
        survey_attribute=survey_attribute_1,
        is_mandatory=True,
    )
    indicator_1.mapping = mapping
    indicator_1.save()

    # Build the URL with type, mode, and attributes query parameters.
    url = f"/api/indicators/?type={survey_type_1.id}&mode={survey_mode_1.id}&attributes={survey_attribute_1.id}"
    response = logged_admin_client.get(url)
    assert response.status_code == 200
    data = response.json()
    # Expect only indicator_1 to be returned.
    assert len(data) == 1
    assert data[0]["id"] == indicator_1.id
    # Because the attribute mapping is mandatory, is_mandatory should be True.
    assert data[0]["is_mandatory"] is True


def test_indicator_mandatory_flag_attribute_overrides(
    logged_admin_client,
    indicator_1,
    survey_type_1,
    survey_mode_1,
    survey_attribute_1,
):
    """
    Test that if the type and mode mappings are set as non-mandatory (False) while the
    attribute mapping remains mandatory (True), then the serializer returns is_mandatory as True.
    """
    # Create a new mapping that will combine type, mode, and attribute info.
    mapping = IndicatorMapping.objects.create()

    # Create a type mapping with is_mandatory=False.
    st_mapping = IndicatorMappingSurveyType.objects.create(
        indicator_mapping=mapping,
        survey_type=survey_type_1,
        is_mandatory=False,
    )
    # Create a mode mapping with is_mandatory=False.
    IndicatorMappingSurveyMode.objects.create(
        survey_mode=survey_mode_1,
        survey_type=st_mapping,
        is_mandatory=False,
    )
    # Create an attribute mapping with is_mandatory=True.
    IndicatorMappingSurveyAttribute.objects.create(
        indicator_mapping=mapping,
        survey_attribute=survey_attribute_1,
        is_mandatory=True,
    )
    indicator_1.mapping = mapping
    indicator_1.save()

    url = f"/api/indicators/?type={survey_type_1.id}&mode={survey_mode_1.id}&attributes={survey_attribute_1.id}"
    response = logged_admin_client.get(url)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == indicator_1.id
    # Although type and mode mappings return False, the attribute mapping is True so overall is_mandatory is True.
    assert data[0]["is_mandatory"] is True


def test_preview_xls_form(
    logged_admin_client,
    submodule_1,
    sub_question_1,
    sub_question_2,
    sub_question_3,
    sub_question_4,
    xls_form_data,
):
    data = {
        "name": "test",
        "submodules": [submodule_1.id],
        "sub_questions": [
            sub_question_1.id,
            sub_question_2.id,
            sub_question_3.id,
            sub_question_4.id,
        ],
        "submodules_order": [submodule_1.id],
        "languages": ["en", "fr"],
    }

    response = logged_admin_client.post("/api/preview/", data, follow=True)
    assert response.status_code == 200
    assert Survey.objects.count() == 1


@pytest.mark.django_db
def test_preview_xls_form_with_external_media(
    mocker,
    logged_admin_client,
    submodule_1,
):
    csv_content = b"name,color\nbanana,yellow\n"
    stub_form = mocker.Mock()
    stub_form.name = "preview_form"
    stub_form.generate.return_value = b"fake-xlsx"
    stub_form.external_files = {
        "fruits.csv": ContentFile(csv_content, name="fruits.csv")
    }

    mocker.patch("modules.views.get_xlsx_from_request", return_value=stub_form)

    mock_successful_xml_conversion(mocker)

    saved_paths = []

    class DummyStorage:
        def save(self, path, content):
            saved_paths.append(path)
            return path

        @staticmethod
        def url(path):
            return f"https://storage.test/{path}"

    class DummyFile:
        def __init__(self, storage):
            self.storage = storage
            self._url = ""

        def save(self, name, content):
            saved_name = self.storage.save(name, content)
            self._url = self.storage.url(saved_name)
            self.name = saved_name

        @property
        def url(self):
            return self._url

    storage = DummyStorage()
    dummy_file = DummyFile(storage)
    survey_instance = mocker.Mock()
    survey_instance.file = dummy_file
    survey_instance.get_enketo_preview_url.return_value = "https://enketo.test/preview"

    mocker.patch("modules.views.Survey.objects.create", return_value=survey_instance)

    data = {
        "name": "test",
        "submodules": [submodule_1.id],
        "submodules_order": [submodule_1.id],
        "sub_questions": [],
        "languages": [],
    }

    response = logged_admin_client.post("/api/preview/", data, follow=True)
    assert response.status_code == status.HTTP_200_OK
    payload = response.json()

    assert "manifest_url" not in payload
    assert "media_files" not in payload
    assert payload["enketo_url"] == "https://enketo.test/preview"
    assert payload["url"].startswith("https://storage.test/previews/")

    csv_saved = [path for path in saved_paths if path.endswith("fruits.csv")]
    xml_saved = [path for path in saved_paths if path.endswith("form_preview.xml")]
    assert csv_saved and xml_saved


@pytest.mark.django_db
def test_preview_xls_form_rewrites_external_file_links(
    mocker,
    logged_admin_client,
    submodule_1,
):
    csv_content = b"name,color\nbanana,yellow\n"
    img_content = b"png"
    stub_form = mocker.Mock()
    stub_form.name = "preview_form"
    stub_form.generate.return_value = b"fake-xlsx"
    stub_form.external_files = {
        "fruits.csv": ContentFile(csv_content, name="fruits.csv"),
        "logo.png": ContentFile(img_content, name="logo.png"),
    }

    mocker.patch("modules.views.get_xlsx_from_request", return_value=stub_form)

    xml_payload = (
        '<h:html xmlns:h="http://www.w3.org/1999/xhtml" '
        'xmlns:xf="http://www.w3.org/2002/xforms">'
        '<h:head><xf:model><xf:instance src="jr://file-csv/fruits.csv"/></xf:model></h:head>'
        '<h:body><h:img src="jr://images/logo.png"/></h:body>'
        "</h:html>"
    )
    mock_successful_xml_conversion(mocker, xml_payload)

    saved_contents = {}

    class DummyStorage:
        def save(self, path, content):
            saved_contents[path] = content.read()
            return path

        @staticmethod
        def url(path):
            return f"https://storage.test/{path}"

    class DummyFile:
        def __init__(self, storage):
            self.storage = storage
            self._url = ""

        def save(self, name, content):
            saved_name = self.storage.save(name, content)
            self._url = self.storage.url(saved_name)
            self.name = saved_name

        @property
        def url(self):
            return self._url

    storage = DummyStorage()
    dummy_file = DummyFile(storage)
    survey_instance = mocker.Mock()
    survey_instance.file = dummy_file
    survey_instance.get_enketo_preview_url.return_value = "https://enketo.test/preview"

    mocker.patch("modules.views.Survey.objects.create", return_value=survey_instance)

    data = {
        "name": "test",
        "submodules": [submodule_1.id],
        "submodules_order": [submodule_1.id],
        "sub_questions": [],
        "languages": [],
    }

    response = logged_admin_client.post("/api/preview/", data, follow=True)
    assert response.status_code == status.HTTP_200_OK

    xml_path = next(
        path for path in saved_contents if path.endswith("form_preview.xml")
    )
    csv_path = next(path for path in saved_contents if path.endswith("fruits.csv"))
    img_path = next(path for path in saved_contents if path.endswith("logo.png"))

    root = ET.fromstring(saved_contents[xml_path])
    ns = {
        "xf": "http://www.w3.org/2002/xforms",
        "h": "http://www.w3.org/1999/xhtml",
    }
    instance = root.find(".//xf:instance", namespaces=ns)
    img = root.find(".//h:img", namespaces=ns)
    assert instance is not None
    assert img is not None
    assert instance.get("src") == storage.url(csv_path)
    assert img.get("src") == storage.url(img_path)


@pytest.mark.django_db
def test_generate_docx(mocker, user):
    mock_job = mocker.patch("modules.views.job")
    mock_job.return_value = lambda f: f

    mock_uuid4 = mocker.patch("uuid.uuid4")
    mock_uuid4.return_value = uuid.UUID("01234567-89ab-cdef-0123-456789abcdef")

    mock_get_xlsx_from_data = mocker.patch("modules.views.get_xlsx_from_data")
    mock_xlsx_form = mocker.Mock()
    mock_get_xlsx_from_data.return_value = mock_xlsx_form

    mock_run = mocker.Mock()
    mock_run.return_value = io.BytesIO(b"mock_doc_content")  # Return BytesIO
    mock_DocConversion = mocker.patch("modules.views.DocConversion")
    mock_DocConversion.return_value.run = mock_run

    mock_document_create = mocker.patch.object(Document.objects, "create")
    mock_document = mocker.Mock()
    mock_document.id = 123
    mock_document_create.return_value = mock_document

    data = {
        "name": "test",
        "submodules": [1],
        "sub_questions": [1, 2, 3, 4],
        "submodules_order": [1],
        "languages": ["en", "fr"],
    }
    result = generate_docx(data, user)
    assert result == 123  # Ensure the return value is the document id
    mock_uuid4.assert_called_once()
    mock_get_xlsx_from_data.assert_called_once_with(data)
    mock_DocConversion.assert_called_once_with(mock_xlsx_form, data["languages"])
    mock_DocConversion.return_value.run.assert_called_once()
    mock_document_create.assert_called_once_with(type="doc", created_by=user)
    mock_document.save.assert_called_once()


@pytest.mark.django_db
class TestGenerateDocForm:
    def test_generate_doc_form_post(
        self,
        mocker,
        logged_admin_client,
        user,
        submodule_1,
        sub_question_1,
        sub_question_2,
        sub_question_3,
        sub_question_4,
    ):
        logged_admin_client.force_login(user)
        mocker.patch("django_rq.get_queue", return_value=get_queue("generate-doc"))
        mock_enqueue = mocker.patch("rq.Queue.enqueue")
        mock_job = mocker.Mock(spec=Job)
        mock_enqueue.return_value = mock_job
        mock_job.id = "mock_job_id"
        mock_job.get_status.return_value = "queued"
        mock_job.get_position.return_value = None

        data = {
            "name": "test",
            "submodules": [submodule_1.pk],
            "sub_questions": [
                sub_question_1.pk,
                sub_question_2.pk,
                sub_question_3.pk,
                sub_question_4.pk,
            ],
            "submodules_order": [submodule_1.pk],
            "languages": ["en", "fr"],
            "survey_type": "",
        }
        url = "/api/generate-doc/"

        response = logged_admin_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "jobId": "mock_job_id",
            "status": "queued",
            "position": None,
        }
        del data["survey_type"]
        data["survey_type_id"] = None
        mock_enqueue.assert_called_once_with(generate_docx, data=data, user=user)

    def test_generate_doc_form_get_success(self, mocker, logged_admin_client):
        mock_fetch = mocker.patch("rq.job.Job.fetch")
        mock_fetch.return_value = mocker.Mock(
            spec=Job, id="mock_job_id", result=123, is_finished=True
        )
        mock_fetch.return_value.get_status.return_value = "finished"
        mock_fetch.return_value.get_position.return_value = None
        mocker.patch("django_rq.get_connection", return_value="mock_redis_connection")
        mocker.patch.object(
            Document.objects,
            "get",
            return_value=mocker.Mock(
                spec=Document, document=mocker.Mock(url="/some/url")
            ),
        )

        url = "/api/generate-doc/"
        params = {"jobId": "mock_job_id"}

        response = logged_admin_client.get(url, params, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "doc": "/some/url",
            "jobId": "mock_job_id",
            "status": "finished",
            "position": None,
        }

    def test_generate_doc_form_get_job_not_found(self, mocker, logged_admin_client):
        mocker.patch("rq.job.Job.fetch", side_effect=NoSuchJobError("Job not found"))

        url = "/api/generate-doc/"
        params = {"jobId": "non_existent_job"}

        response = logged_admin_client.get(url, params, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {"detail": "Job not found."}

    def test_generate_doc_form_get_exception(self, mocker, logged_admin_client):
        mocker.patch("rq.job.Job.fetch", side_effect=Exception("Some error"))

        url = "/api/generate-doc/"
        params = {"jobId": "mock_job_id"}

        response = logged_admin_client.get(url, params, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {"detail": "Some error"}


@pytest.mark.django_db
def test_upload_xls_form_moda_uploads_metadata(
    mocker, logged_admin_client, moda_api_key, submodule_1
):
    site = moda_api_key.site
    fake_file = FakeFieldFile("fruits.csv", b"name,color\nbanana,yellow\n")
    stub_form = build_stub_xls_form({"fruits.csv": fake_file})
    mocker.patch("modules.views.get_xlsx_from_data", return_value=stub_form)
    mock_successful_xml_conversion(mocker)

    upload_response = mocker.Mock()
    upload_response.ok = True
    upload_response.json.return_value = {
        "id": 681,
        "enketo_preview_url": "https://enketo.test/preview",
    }

    metadata_response = mocker.Mock()
    metadata_response.ok = True
    metadata_response.json.return_value = {"status": "ok"}

    mock_post = mocker.patch(
        "modules.views.requests.post", side_effect=[upload_response, metadata_response]
    )

    payload = {
        "name": "Moda Form",
        "submodules": [submodule_1.id],
        "submodules_order": [submodule_1.id],
        "sub_questions": [],
        "languages": [],
        "id": moda_api_key.id,
        "project_id": 99,
    }

    response = logged_admin_client.post(
        "/api/upload/",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == status.HTTP_200_OK, response.json()
    body = response.json()
    assert body["preview_url"] == "https://enketo.test/preview"
    assert body["metadata_uploaded_files"] == ["fruits.csv"]

    assert mock_post.call_count == 2
    upload_call, metadata_call = mock_post.call_args_list

    upload_url = UserAPISiteAPITypes.get_upload_url(site, payload["project_id"])
    assert upload_call.args[0] == upload_url
    assert upload_call.kwargs["headers"] == {"Authorization": "Token test-token"}
    assert upload_call.kwargs["files"]["xls_file"][0] == f"{stub_form.id_name}.xlsx"
    assert upload_call.kwargs["files"]["xls_file"][1] == b"fake-xlsx"

    metadata_url = UserAPISiteAPITypes.get_metadata_url(site)
    assert metadata_call.args[0] == metadata_url
    assert metadata_call.kwargs["headers"] == {
        "Accept": "application/json",
        "Authorization": "Token test-token",
    }

    metadata_files = metadata_call.kwargs["files"]
    assert metadata_files["xform"] == (None, "681")
    assert metadata_files["data_type"] == (None, "media")
    assert metadata_files["data_value"] == (None, "fruits.csv")
    data_file = metadata_files["data_file"]
    assert data_file[0] == "fruits.csv"
    assert data_file[2] == "text/csv"
    assert data_file[1].getvalue() == b"name,color\nbanana,yellow\n"


@pytest.mark.django_db
def test_upload_xls_form_moda_without_attachments(
    mocker, logged_admin_client, moda_api_key, submodule_1
):
    site = moda_api_key.site
    stub_form = build_stub_xls_form({})
    mocker.patch("modules.views.get_xlsx_from_data", return_value=stub_form)
    mock_successful_xml_conversion(mocker)

    upload_response = mocker.Mock()
    upload_response.ok = True
    upload_response.json.return_value = {
        "id": 682,
        "enketo_preview_url": "https://enketo.test/preview",
    }
    mock_post = mocker.patch(
        "modules.views.requests.post", return_value=upload_response
    )

    payload = {
        "name": "Moda Form",
        "submodules": [submodule_1.id],
        "submodules_order": [submodule_1.id],
        "sub_questions": [],
        "languages": [],
        "id": moda_api_key.id,
        "project_id": 100,
    }

    response = logged_admin_client.post(
        "/api/upload/",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["preview_url"] == "https://enketo.test/preview"
    assert "metadata_uploaded_files" not in body
    assert mock_post.call_count == 1
    upload_call = mock_post.call_args_list[0]
    upload_url = UserAPISiteAPITypes.get_upload_url(site, payload["project_id"])
    assert upload_call.args[0] == upload_url


@pytest.mark.django_db
def test_upload_xls_form_moda_metadata_failure(
    mocker, logged_admin_client, moda_api_key, submodule_1
):
    stub_form = build_stub_xls_form({"fruits.csv": FakeFieldFile("fruits.csv")})
    mocker.patch("modules.views.get_xlsx_from_data", return_value=stub_form)
    mock_successful_xml_conversion(mocker)

    upload_response = mocker.Mock()
    upload_response.ok = True
    upload_response.json.return_value = {
        "id": 700,
        "enketo_preview_url": "https://enketo.test/preview",
    }

    metadata_response = mocker.Mock()
    metadata_response.ok = False
    metadata_response.status_code = 500
    metadata_response.json.return_value = {"detail": "server error"}

    mocker.patch(
        "modules.views.requests.post",
        side_effect=[upload_response, metadata_response],
    )

    payload = {
        "name": "Moda Form",
        "submodules": [submodule_1.id],
        "submodules_order": [submodule_1.id],
        "sub_questions": [],
        "languages": [],
        "id": moda_api_key.id,
        "project_id": 101,
    }

    response = logged_admin_client.post(
        "/api/upload/",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    body = response.json()
    assert body["message"] == "Failed to upload metadata file 'fruits.csv' to Moda."
    assert str(body["code"]) == "500"
    assert body["details"] == {"detail": "server error"}


@pytest.mark.django_db
class TestSubmodulesOrderValidationView:
    def test_submodules_order_validation_view_no_submodule_ids(
        self, logged_admin_client
    ):
        url = "/api/order-validation/"

        response = logged_admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_submodules_order_validation_view_with_submodule_ids(
        self, logged_admin_client, submodule_1, submodule_2, submodule_3
    ):
        url = "/api/order-validation/"

        submodule_ids = [submodule_1.pk, submodule_2.pk, submodule_3.pk]
        query_params = {
            "submodule_ids": " ".join(map(str, submodule_ids)),
            "all_submodule_ids": " ".join(map(str, submodule_ids)),
        }
        response = logged_admin_client.get(url, query_params)

        assert response.status_code == status.HTTP_200_OK

    def test_submodules_order_validation_view_invalid_order(
        self, logged_admin_client, submodule_1, submodule_2, submodule_3
    ):
        url = "/api/order-validation/"

        submodule_ids = [submodule_2.pk, submodule_1.pk, submodule_3.pk]
        query_params = {
            "submodule_ids": " ".join(map(str, submodule_ids)),
            "all_submodule_ids": " ".join(map(str, submodule_ids)),
        }
        response = logged_admin_client.get(url, query_params)

        assert response.status_code == status.HTTP_200_OK

    def test_submodules_order_validation_view_invalid_indicator_ids(
        self, logged_admin_client
    ):
        url = "/api/order-validation/"

        query_params = {
            "submodule_ids": "1 2 3",
            "indicator_ids": "1 two 3",
            "all_submodule_ids": "1 2 3 4 5",
        }
        response = logged_admin_client.get(url, query_params)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {
            "indicator_ids": "This parameter must contain only integers."
        }
