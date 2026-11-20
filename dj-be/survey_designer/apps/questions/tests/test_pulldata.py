import json

import pytest
from core.utils import get_model_admin_base_url
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.forms import modelform_factory
from django.urls import reverse
from organization.utils import get_organizations
from questions.forms import PulldataFileAdminForm, SubQuestionAdminModelForm
from questions.models import PulldataFile, RootQuestion, SubQuestion
from questions.services.expression_validation import analyse_expression
from questions.services.pulldata import (
    pulldata_file_status,
    pulldata_filename_error,
    validate_pulldata_files,
)
from questions.services.pulldata_csv import PulldataHeaderError, read_pulldata_headers

from .test_expression_authoring import _form_errors, _post_root_question

# The weight-for-length calculation from the FSNA survey (issue #183).
FSNA_CALCULATION = (
    "if(${ChAnthropoSex}=0 and ${ChAnthropoAge}<24, "
    "pulldata('wfl_0_2_girls','minZScore','Length',${lowerChAnthropoHgt}),"
    "if(${ChAnthropoSex}=0 and ${ChAnthropoAge}>=24, "
    "pulldata('wfh_2_5_girls','minZScore','Height',${lowerChAnthropoHgt}),"
    "if(${ChAnthropoSex}=1 and ${ChAnthropoAge}<24, "
    "pulldata('wfl_0_2_boys','minZScore','Length',${lowerChAnthropoHgt}),"
    "if(${ChAnthropoSex}=1 and ${ChAnthropoAge}>=24, "
    "pulldata('wfh_2_5_boys','minZScore','Height',${lowerChAnthropoHgt}),''))))"
)
FSNA_FILES = (
    "wfl_0_2_girls.csv",
    "wfh_2_5_girls.csv",
    "wfl_0_2_boys.csv",
    "wfh_2_5_boys.csv",
)
OWNER = {"model": "RootQuestion", "id": 1, "name": "ZminChAnthropoWgt"}
CSV_CONTENT = b"Length,minZScore,maxZScore\n45,1.6,4.0\n"


class _AttachedFile:
    def __init__(self, filename, columns=None):
        self.filename = filename
        if columns is not None:
            self.columns = columns


def _check(calculation, *filenames, **fields):
    return validate_pulldata_files(
        OWNER,
        {"calculation": calculation, **fields},
        [_AttachedFile(filename) for filename in filenames],
    )


def _codes(issues):
    return [issue.code for issue in issues]


def _upload(filename="wfl_0_2_girls.csv", content=CSV_CONTENT):
    return SimpleUploadedFile(filename, content, content_type="text/csv")


@pytest.fixture()
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    return tmp_path


# Detection


def test_parser_records_every_pulldata_call_in_the_fsna_calculation():
    assert analyse_expression(FSNA_CALCULATION).pulldata_calls == (
        ("wfl_0_2_girls", "minZScore", "Length", None),
        ("wfh_2_5_girls", "minZScore", "Height", None),
        ("wfl_0_2_boys", "minZScore", "Length", None),
        ("wfh_2_5_boys", "minZScore", "Height", None),
    )


def test_parser_finds_nested_calls_and_ignores_pulldata_inside_text():
    analysis = analyse_expression(
        "concat('pulldata(', pulldata('g', 'a', 'b', pulldata('h', 'c', 'd', ${x})))"
    )

    assert analysis.pulldata_calls == (("h", "c", "d", None), ("g", "a", "b", None))


def test_parser_marks_arguments_that_are_not_single_literals():
    analysis = analyse_expression("pulldata(${file}, concat('a', 'b'), 'c', 1)")

    assert analysis.pulldata_calls == ((None, None, "c", None),)


def test_parser_handles_an_unfinished_pulldata_call():
    analysis = analyse_expression("pulldata(")

    assert analysis.valid is False
    assert analysis.pulldata_calls == ()


def test_matching_files_pass():
    assert _check(FSNA_CALCULATION, *FSNA_FILES) == []


def test_repeated_calls_on_one_file_need_one_file():
    calculation = (
        "pulldata('growth', 'a', 'id', ${x}) + pulldata('growth', 'b', 'id', ${x})"
        " + pulldata('growth', 'c', 'id', ${x})"
    )

    assert _check(calculation, "growth.csv") == []
    assert _codes(_check(calculation)) == [
        "PULLDATA_FILE_MISSING",
        "PULLDATA_FILE_MAPPING_FAILED",
    ]


@pytest.mark.parametrize(
    "return_column, lookup_column, missing_column",
    [("Display", "key", "Display"), ("display", "Key", "Key")],
)
def test_literal_return_and_lookup_columns_are_checked_case_sensitively(
    return_column, lookup_column, missing_column
):
    issues = validate_pulldata_files(
        OWNER,
        {
            "calculation": (
                f"pulldata('growth', '{return_column}', '{lookup_column}', ${{x}})"
            )
        },
        [_AttachedFile("growth.csv", ["key", "display"])],
    )

    assert [(issue.code, issue.field) for issue in issues] == [
        ("PULLDATA_COLUMN_MISSING", "calculation")
    ]
    assert (
        f"Column '{missing_column}' does not exist in 'growth.csv'."
        in issues[0].message
    )


def test_dynamic_column_expressions_are_not_rejected_without_metadata():
    assert (
        validate_pulldata_files(
            OWNER,
            {"calculation": "pulldata('growth', ${return_col}, ${key_col}, ${x})"},
            [_AttachedFile("growth.csv", ["key", "display"])],
        )
        == []
    )


def test_missing_file_does_not_cascade_into_column_errors():
    issues = validate_pulldata_files(
        OWNER,
        {"calculation": "pulldata('growth', 'display', 'key', ${x})"},
        [],
    )

    assert [issue.code for issue in issues] == [
        "PULLDATA_FILE_MISSING",
        "PULLDATA_FILE_MAPPING_FAILED",
    ]


def test_unavailable_legacy_columns_are_reported_without_guessing():
    issues = validate_pulldata_files(
        OWNER,
        {"calculation": "pulldata('growth', 'display', 'key', ${x})"},
        [_AttachedFile("growth.csv", [])],
    )

    assert [issue.code for issue in issues] == ["PULLDATA_COLUMNS_UNAVAILABLE"]
    assert "Re-upload the file" in issues[0].message


def test_no_pulldata_and_no_files_pass():
    assert _check("${a} + 1") == []


# Errors


def test_missing_file_is_reported_with_a_count_mismatch():
    issues = _check(FSNA_CALCULATION, *FSNA_FILES[:3])

    assert [(issue.code, issue.field, issue.message) for issue in issues] == [
        (
            "PULLDATA_FILE_MISSING",
            "pulldata_files",
            "Missing file: RootQuestion 'ZminChAnthropoWgt' uses "
            "pulldata('wfh_2_5_boys', ...) in 'calculation' but 'wfh_2_5_boys.csv' "
            "is not attached. Upload it or select it in Pull data files.",
        ),
        (
            "PULLDATA_FILE_MAPPING_FAILED",
            "pulldata_files",
            "Mapping failed: RootQuestion 'ZminChAnthropoWgt' needs 4 pull data "
            "files but 3 are attached. Review the files and the pulldata function.",
        ),
    ]


def test_unknown_file_is_reported_with_a_count_mismatch():
    issues = _check(FSNA_CALCULATION, *FSNA_FILES, "growth.csv")

    assert _codes(issues) == ["PULLDATA_FILE_UNKNOWN", "PULLDATA_FILE_MAPPING_FAILED"]
    assert issues[0].message == (
        "Unknown file: 'growth.csv' is attached to RootQuestion 'ZminChAnthropoWgt' "
        "but no pulldata() call uses 'growth'. Remove the file or review the "
        "pulldata function."
    )


def test_wrong_file_is_missing_and_unknown_when_counts_match():
    issues = _check(FSNA_CALCULATION, *FSNA_FILES[:3], "growth.csv")

    assert _codes(issues) == ["PULLDATA_FILE_MISSING", "PULLDATA_FILE_UNKNOWN"]


def test_file_attached_without_any_pulldata_is_unknown():
    issues = _check("", "growth.csv")

    assert _codes(issues) == ["PULLDATA_FILE_UNKNOWN", "PULLDATA_FILE_MAPPING_FAILED"]
    assert issues[1].message.startswith(
        "Mapping failed: RootQuestion 'ZminChAnthropoWgt' needs 0 pull data files "
        "but 1 is attached."
    )


def test_pulldata_in_other_expression_fields_is_detected():
    issues = _check("", relevant="pulldata('growth', 'a', 'id', ${x}) = 'yes'")

    assert _codes(issues) == ["PULLDATA_FILE_MISSING", "PULLDATA_FILE_MAPPING_FAILED"]
    assert "in 'relevant'" in issues[0].message


@pytest.mark.parametrize(
    "calculation, expected",
    [
        (
            "pulldata(${file}, 'a', 'id', 1)",
            "RootQuestion 'ZminChAnthropoWgt' field 'calculation' has a pulldata() "
            "call whose first argument is not a quoted file name. Write it as "
            "pulldata('file_name', ...).",
        ),
        (
            "pulldata('growth.csv', 'a', 'id', 1)",
            "RootQuestion 'ZminChAnthropoWgt' field 'calculation' passes "
            "'growth.csv' to pulldata(). Leave out .csv: pulldata('growth', ...) "
            "reads growth.csv.",
        ),
        (
            "pulldata('my file', 'a', 'id', 1)",
            "RootQuestion 'ZminChAnthropoWgt' field 'calculation' passes 'my file' "
            "to pulldata(). File names must start with a letter or '_' and use only "
            "letters, digits, '_', '-' or '.'.",
        ),
    ],
)
def test_unusable_file_name_argument_is_reported_on_the_field(calculation, expected):
    issues = _check(calculation, "other.csv")

    # The required files are unknown, so unknown and mapping errors wait.
    assert [(issue.code, issue.field, issue.message) for issue in issues] == [
        ("PULLDATA_SOURCE_INVALID", "calculation", expected)
    ]


def test_syntax_errors_are_left_to_expression_validation():
    assert _check("pulldata('growth', 'a', 'id'", "other.csv") == []


@pytest.mark.parametrize(
    "filename, valid",
    [
        ("wfl_0_2_girls.csv", True),
        ("Prefill_1_AdminNames.csv", True),
        ("growth.v2.csv", True),
        ("growth.CSV", False),
        ("growth.xlsx", False),
        ("my file.csv", False),
        ("2020_prices.csv", False),
    ],
)
def test_uploaded_file_names_must_work_with_pulldata(filename, valid):
    assert (pulldata_filename_error(filename) is None) is valid


# Uploads


def test_upload_keeps_the_original_file_name(db, media_root):
    pulldata_file = PulldataFile.objects.create(file=_upload("growth.csv"))

    assert pulldata_file.filename == "growth.csv"
    assert pulldata_file.columns == ["Length", "minZScore", "maxZScore"]
    assert pulldata_file.file.name.startswith("pulldata/")
    assert pulldata_file.file.name.endswith("/growth.csv")


def test_header_reader_supports_bom_quoted_headers_and_restores_position():
    uploaded = SimpleUploadedFile(
        "quoted.csv", b'\xef\xbb\xbf"lookup,id",Return\n1,2\n', content_type="text/csv"
    )
    uploaded.read(2)

    assert read_pulldata_headers(uploaded) == ["lookup,id", "Return"]
    assert uploaded.tell() == 2


@pytest.mark.parametrize(
    "content, message",
    [
        (b"", "empty or has no header row"),
        (b"id, \n1,2\n", "empty or blank header name"),
        (b"id,id\n1,2\n", "duplicate header 'id'"),
        (b"id,\xff\n1,2\n", "not valid UTF-8"),
        (b'id,"unterminated\n1,2\n', "invalid header row"),
    ],
)
def test_header_reader_rejects_invalid_headers(content, message):
    with pytest.raises(PulldataHeaderError, match=message):
        read_pulldata_headers(SimpleUploadedFile("bad.csv", content))


def test_model_save_rejects_invalid_header_before_storage(db, media_root):
    with pytest.raises(ValidationError, match="duplicate header"):
        PulldataFile.objects.create(file=_upload("bad.csv", b"id,id\n1,2\n"))


def test_replacing_a_file_refreshes_its_columns(db, media_root):
    pulldata_file = PulldataFile.objects.create(file=_upload("growth.csv"))
    pulldata_file.file = _upload("growth.csv", b"key,display\n1,Apple\n")
    pulldata_file.save()

    pulldata_file.refresh_from_db()
    assert pulldata_file.columns == ["key", "display"]


def test_description_only_save_does_not_read_or_persist_pending_file(
    db, media_root, mocker
):
    created = PulldataFile.objects.create(file=_upload("growth.csv"))
    pulldata_file = PulldataFile.objects.get(pk=created.pk)
    pulldata_file.description = "Updated"
    pulldata_file.file = _upload("growth.csv", b"new_key,new_value\n1,Apple\n")
    mocker.patch.object(
        pulldata_file.file.storage,
        "open",
        side_effect=AssertionError("storage should not be read"),
    )
    mocker.patch(
        "questions.services.pulldata_csv.read_pulldata_headers",
        side_effect=AssertionError("file header should not be read"),
    )

    pulldata_file.save(update_fields={"description"})

    pulldata_file.refresh_from_db()
    assert pulldata_file.description == "Updated"
    assert pulldata_file.columns == ["Length", "minZScore", "maxZScore"]


def test_empty_update_fields_is_a_noop_for_pending_file(db, media_root, mocker):
    pulldata_file = PulldataFile.objects.create(file=_upload("growth.csv"))
    pulldata_file.file = _upload("growth.csv", b"new_key,new_value\n1,Apple\n")
    mocker.patch(
        "questions.services.pulldata_csv.read_pulldata_headers",
        side_effect=AssertionError("empty update must not read file"),
    )

    pulldata_file.save(update_fields=[])

    pulldata_file.refresh_from_db()
    assert pulldata_file.columns == ["Length", "minZScore", "maxZScore"]


def test_pulldata_validation_uses_metadata_without_opening_storage(
    db, media_root, mocker
):
    created = PulldataFile.objects.create(file=_upload("growth.csv"))
    pulldata_file = PulldataFile.objects.get(pk=created.pk)
    mocker.patch.object(
        pulldata_file.file.storage,
        "open",
        side_effect=AssertionError("storage should not be read"),
    )

    issues = validate_pulldata_files(
        OWNER,
        {"calculation": "pulldata('growth', 'minZScore', 'Length', ${x})"},
        [pulldata_file],
    )

    assert issues == []


def test_file_names_are_unique_ignoring_case(db, media_root):
    PulldataFile.objects.create(file=_upload("growth.csv"))

    with pytest.raises(IntegrityError), transaction.atomic():
        PulldataFile.objects.create(file=_upload("Growth.csv"))


def test_upload_form_points_to_the_file_already_uploaded(db, media_root):
    PulldataFile.objects.create(file=_upload("growth.csv"))

    form = PulldataFileAdminForm(data={}, files={"file": _upload("GROWTH.csv")})

    assert form.is_valid() is False
    assert form.errors["file"] == [
        "'growth.csv' has already been uploaded. Select it on the question "
        "instead: one file can serve any number of pulldata() calls."
    ]


def test_upload_form_lets_a_file_keep_its_own_name(db, media_root):
    pulldata_file = PulldataFile.objects.create(file=_upload("growth.csv"))

    form = PulldataFileAdminForm(
        data={"description": "WHO table"},
        files={"file": _upload("growth.csv", b"id,b\n1,2\n")},
        instance=pulldata_file,
    )

    assert form.is_valid(), form.errors


def test_upload_form_rejects_names_pulldata_cannot_use(db):
    form = PulldataFileAdminForm(data={}, files={"file": _upload("Growth Table.csv")})

    assert form.is_valid() is False
    assert form.errors["file"] == [
        "'Growth Table.csv' cannot be used by pulldata(). File names must start "
        "with a letter or '_' and use only letters, digits, '_', '-' or '.'."
    ]


def test_upload_form_applies_the_external_file_size_limit(db, settings):
    settings.EXTERNAL_CHOICE_FILE_MAX_BYTES = 10

    form = PulldataFileAdminForm(data={}, files={"file": _upload()})

    assert form.is_valid() is False
    assert form.errors["file"][0].startswith("File size exceeds the maximum")


def test_admin_uploads_a_pull_data_file(logged_admin_client, media_root):
    url = get_model_admin_base_url(PulldataFile, "_add")

    response = logged_admin_client.post(url, {"file": _upload(), "description": ""})

    assert response.status_code == 302
    pulldata_file = PulldataFile.objects.get()
    assert pulldata_file.filename == "wfl_0_2_girls.csv"
    assert pulldata_file.created_by.email == "admin@example.com"


# Saving questions


def test_root_question_without_its_file_cannot_be_saved(
    logged_admin_client, root_question_1
):
    calculation = "pulldata('wfl_0_2_girls', 'minZScore', 'Length', 45)"

    response = _post_root_question(
        logged_admin_client, root_question_1, calculation=calculation
    )

    assert response.status_code == 200
    assert _form_errors(response)["pulldata_files"] == [
        "Missing file: RootQuestion 'TestQuestion1' uses pulldata('wfl_0_2_girls', "
        "...) in 'calculation' but 'wfl_0_2_girls.csv' is not attached. Upload it "
        "or select it in Pull data files.",
        "Mapping failed: RootQuestion 'TestQuestion1' needs 1 pull data file but 0 "
        "are attached. Review the files and the pulldata function.",
    ]
    root_question_1.refresh_from_db()
    assert root_question_1.calculation == ""


def test_root_question_saves_with_its_file_attached(
    logged_admin_client, root_question_1, media_root
):
    pulldata_file = PulldataFile.objects.create(file=_upload())
    calculation = "pulldata('wfl_0_2_girls', 'minZScore', 'Length', 45)"

    response = _post_root_question(
        logged_admin_client,
        root_question_1,
        calculation=calculation,
        pulldata_files=[str(pulldata_file.pk)],
    )

    assert response.status_code == 302
    root_question_1.refresh_from_db()
    assert root_question_1.calculation == calculation
    assert list(root_question_1.pulldata_files.all()) == [pulldata_file]


def _codes_from_messages(messages):
    return [message.split(":", 1)[0] for message in messages]


def _sub_question_form(sub_question, **data):
    form_class = modelform_factory(
        SubQuestion,
        form=SubQuestionAdminModelForm,
        fields=("root_question", "suffix", "label", "calculation", "pulldata_files"),
    )
    return form_class(
        data={
            "root_question": sub_question.root_question_id,
            "suffix": sub_question.suffix_id,
            "label": sub_question.label,
            **data,
        },
        instance=sub_question,
    )


def test_sub_question_without_its_file_cannot_be_saved(sub_question_1):
    form = _sub_question_form(
        sub_question_1, calculation="pulldata('growth', 'a', 'id', 1)"
    )

    assert form.is_valid() is False
    assert _codes_from_messages(form.errors["pulldata_files"]) == [
        "Missing file",
        "Mapping failed",
    ]


def test_live_pulldata_errors_are_marked_without_marking_other_form_errors(
    sub_question_1, media_root
):
    pulldata_file = PulldataFile.objects.create(
        file=_upload("growth.csv", b"id,display\n1,Apple\n")
    )
    form = _sub_question_form(
        sub_question_1,
        calculation="pulldata('growth', 'missing', 'id', 1)",
        label="",
        pulldata_files=[pulldata_file.pk],
    )

    assert form.is_valid() is False
    marked = json.loads(
        form.fields["calculation"].widget.attrs["data-pulldata-server-errors"]
    )
    assert len(marked) == 1
    assert "Column 'missing' does not exist in 'growth.csv'." in marked[0]
    assert "label" in form.errors


def test_sub_question_rejects_an_unknown_file(sub_question_1, media_root):
    pulldata_file = PulldataFile.objects.create(file=_upload("growth.csv"))

    form = _sub_question_form(
        sub_question_1, calculation="", pulldata_files=[pulldata_file.pk]
    )

    assert form.is_valid() is False
    assert _codes_from_messages(form.errors["pulldata_files"]) == [
        "Unknown file",
        "Mapping failed",
    ]


def test_pull_data_file_belongs_to_the_organizations_of_its_questions(
    root_question_1, media_root
):
    pulldata_file = PulldataFile.objects.create(file=_upload())
    root_question_1.pulldata_files.add(pulldata_file)

    assert set(get_organizations(pulldata_file)) == set(
        get_organizations(root_question_1)
    )
    assert set(get_organizations(root_question_1))


# Question form widget


def test_question_admin_shows_pull_data_files_as_a_searchable_select(
    logged_admin_client,
):
    page = logged_admin_client.get(get_model_admin_base_url(RootQuestion, "_add"))
    content = page.content.decode()
    start = content.index('class="form-row field-pulldata_files"')
    row = content[start : content.index('class="form-row', start + 1)]

    # The admin minifies HTML, so attribute quotes are optional here.
    assert "data-autocomplete-light-url=" in row
    assert reverse("v1:pulldata-file-autocomplete") in row
    assert "add_id_pulldata_files" in row
    assert "Hold down" not in row
    assert f"data-pulldata-status-url={reverse('pulldata-status')}" in row
    assert "js/admin/pulldata_status.js" in content


def test_pull_data_file_autocomplete_is_for_staff_only(
    django_client, logged_admin_client, media_root
):
    pulldata_file = PulldataFile.objects.create(file=_upload())
    url = reverse("v1:pulldata-file-autocomplete")

    staff_results = logged_admin_client.get(url, {"q": "girls"}).json()["results"]
    django_client.logout()
    anonymous_results = django_client.get(url, {"q": "girls"}).json()["results"]

    assert [result["id"] for result in staff_results] == [str(pulldata_file.pk)]
    assert anonymous_results == []


# Live status under the calculation box


def test_status_shows_each_file_as_attached_missing_or_unused():
    status = pulldata_file_status(
        {"calculation": FSNA_CALCULATION},
        ["wfl_0_2_girls.csv", "wfh_2_5_girls.csv", "growth.csv"],
    )

    assert [(file["filename"], file["status"]) for file in status["files"]] == [
        ("wfl_0_2_girls.csv", "attached"),
        ("wfh_2_5_girls.csv", "attached"),
        ("wfl_0_2_boys.csv", "missing"),
        ("wfh_2_5_boys.csv", "missing"),
        ("growth.csv", "unused"),
    ]
    assert status["problems"] == []
    assert status["complete"] is True


def test_status_does_not_call_files_unused_until_every_call_is_readable():
    status = pulldata_file_status(
        {"calculation": "pulldata(${file}, 'a', 'id', 1)"}, ["growth.csv"]
    )

    assert status == {
        "files": [{"filename": "growth.csv", "status": "unchecked", "fields": []}],
        "problems": [
            "Field 'calculation' has a pulldata() call whose first argument is "
            "not a quoted file name. Write it as pulldata('file_name', ...)."
        ],
        "complete": False,
    }


def test_status_reports_literal_column_problem_from_attached_metadata():
    status = pulldata_file_status(
        {"calculation": "pulldata('growth', 'display', 'key', ${x})"},
        [_AttachedFile("growth.csv", ["key"])],
    )

    assert status["problems"] == [
        "Field 'calculation': Column 'display' does not exist in 'growth.csv'."
    ]


def test_status_endpoint_checks_the_form_values(logged_admin_client, media_root):
    pulldata_file = PulldataFile.objects.create(file=_upload())

    response = logged_admin_client.get(
        reverse("pulldata-status"),
        {
            "calculation": "pulldata('wfl_0_2_girls', 'a', 'id', 1)",
            "relevant": "pulldata('growth', 'a', 'id', 1) = 1",
            "files": [str(pulldata_file.pk), "not-an-id"],
        },
    )

    assert response.status_code == 200
    # Fields are read in the order expression validation uses.
    assert response.json()["files"] == [
        {"filename": "growth.csv", "status": "missing", "fields": ["relevant"]},
        {
            "filename": "wfl_0_2_girls.csv",
            "status": "attached",
            "fields": ["calculation"],
        },
    ]


def test_status_endpoint_is_for_staff_who_can_view_pull_data_files(django_client, user):
    url = reverse("pulldata-status")

    assert django_client.get(url).status_code == 302

    user.is_staff = True
    user.save()
    django_client.force_login(user)
    assert django_client.get(url).status_code == 403
