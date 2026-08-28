import io

import pytest
from django.core.files.base import ContentFile
from openpyxl import Workbook
from questions.services import XLSForm
from questions.services.form_validation import (
    ArtifactInputError,
    GeneratedSurveyArtifact,
    ValidationIssue,
    build_generated_artifact,
    compute_artifact_hash,
    materialize_external_files,
    validate_codebook_integrity,
    validate_generated_artifact,
    validate_xml_compatibility,
)
from questions.services.xml_conversion import XMLConversion


def _codebook_workbook(
    survey_rows,
    choice_rows=(),
    *,
    export_columns=False,
    label_column="label",
):
    workbook = Workbook()
    survey = workbook.active
    survey.title = "survey"
    survey.append(
        ["type", "name", "choice_list"] if export_columns else ["type", "name"]
    )
    for row in survey_rows:
        survey.append(row)

    choices = workbook.create_sheet("choices")
    choices.append(
        ["choice_list", "name", label_column]
        if export_columns
        else ["list_name", "name", label_column]
    )
    for row in choice_rows:
        choices.append(row)

    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


class ConversionMustNotRun:
    def __init__(self, xlsx_file):
        raise AssertionError("pyxform must not run for an invalid codebook")


def test_artifact_hash_is_order_independent_for_external_files():
    first = compute_artifact_hash(b"xlsx", {"b.csv": b"2", "a.csv": b"1"})
    second = compute_artifact_hash(b"xlsx", {"a.csv": b"1", "b.csv": b"2"})

    assert first == second
    assert first.startswith("sha256:")
    assert first != compute_artifact_hash(b"different", {"a.csv": b"1", "b.csv": b"2"})


def test_build_generated_artifact_generates_and_reads_each_external_file_once():
    class ReadOnceFile:
        def __init__(self, content):
            self.content = content
            self.open_mode = None
            self.read_count = 0
            self.close_count = 0

        def open(self, mode):
            self.open_mode = mode
            return self

        def read(self):
            self.read_count += 1
            return self.content

        def close(self):
            self.close_count += 1

    external = ReadOnceFile(b"name\nvalue\n")

    class Form:
        id_name = "generated-form"

        def __init__(self):
            self.generate_count = 0
            self.external_files = {"choices.csv": external}

        def generate(self):
            self.generate_count += 1
            return b"xlsx-bytes"

    form = Form()
    artifact = build_generated_artifact(form)

    assert artifact.xlsx_bytes == b"xlsx-bytes"
    assert artifact.external_files == {"choices.csv": b"name\nvalue\n"}
    assert form.generate_count == 1
    assert external.open_mode == "rb"
    assert external.read_count == 1
    assert external.close_count == 1


def test_compatibility_requires_referenced_csv_in_exact_artifact():
    xml = (
        '<h:html xmlns:h="http://www.w3.org/1999/xhtml" '
        'xmlns:xf="http://www.w3.org/2002/xforms">'
        "<h:head><xf:model><xf:instance><data/></xf:instance>"
        '<xf:instance id="choices" src="jr://file-csv/choices.csv"/>'
        "</xf:model></h:head><h:body/></h:html>"
    )

    issues = validate_xml_compatibility(xml)
    assert [issue.code for issue in issues] == ["EXTERNAL_FILE_MISSING"]
    assert validate_xml_compatibility(xml, {"choices.csv": b"data"}) == []


def test_validation_result_normalizes_compatibility_issues():
    class Conversion:
        def __init__(self, xlsx_file):
            self.xlsx_file = xlsx_file
            self.errors = []
            self.warnings = ["non-blocking warning"]

        def run(self):
            return (
                '<h:html xmlns:h="http://www.w3.org/1999/xhtml" '
                'xmlns:xf="http://www.w3.org/2002/xforms">'
                "<h:head><xf:model><xf:instance><data/></xf:instance>"
                "</xf:model></h:head><h:body/></h:html>"
            )

    artifact = GeneratedSurveyArtifact(_codebook_workbook([("text", "notes")]))
    result = validate_generated_artifact(artifact, converter_cls=Conversion)

    assert result.valid is True
    assert result.errors == ()
    assert result.warnings[0].as_dict() == {
        "code": "PYXFORM_WARNING",
        "layer": "pyxform",
        "severity": "warning",
        "message": "non-blocking warning",
    }
    assert result.as_dict()["validator"] == {
        "pyxform": "4.5.0",
        "compatibility": "1.0",
    }


@pytest.mark.parametrize("question_type", ["select_one", "select_multiple"])
def test_codebook_validation_accepts_internal_select_with_emitted_choices(
    question_type,
):
    xlsx = _codebook_workbook(
        [(f"{question_type} foods", "preferred_food")],
        [("foods", "rice", "Rice")],
    )

    assert validate_codebook_integrity(xlsx) == []


def test_codebook_validation_reports_internal_select_without_choice_list():
    xlsx = _codebook_workbook([("select_one", "preferred_food")])

    issues = validate_codebook_integrity(xlsx)

    assert [issue.code for issue in issues] == ["CODEBOOK_CHOICE_LIST_MISSING"]
    assert issues[0].as_dict() == {
        "code": "CODEBOOK_CHOICE_LIST_MISSING",
        "layer": "composition",
        "severity": "error",
        "message": "Question 'preferred_food' uses select_one but does not specify a choice list.",
        "owner": {"model": "question", "name": "preferred_food"},
        "field": "choices",
        "sheet": "survey",
        "column": "type",
        "row": 2,
    }


def test_codebook_validation_reports_choice_list_without_emitted_rows():
    xlsx = _codebook_workbook([("select_multiple foods", "preferred_foods")])

    issues = validate_codebook_integrity(xlsx)

    assert [issue.code for issue in issues] == ["CODEBOOK_CHOICE_LIST_NOT_EMITTED"]
    assert "choice list 'foods'" in issues[0].message


def test_codebook_validation_uses_export_choice_list_column():
    xlsx = _codebook_workbook(
        [("select_one", "preferred_food", "foods")],
        [("foods", "rice", "Rice")],
        export_columns=True,
    )

    assert validate_codebook_integrity(xlsx) == []


@pytest.mark.parametrize("missing_value", [None, "", "   "])
def test_codebook_validation_reports_missing_choice_value(missing_value):
    xlsx = _codebook_workbook(
        [("select_one foods", "preferred_food")],
        [("foods", missing_value, "Rice")],
    )

    issues = validate_codebook_integrity(xlsx)

    assert [issue.code for issue in issues] == ["CODEBOOK_CHOICE_VALUE_MISSING"]
    assert issues[0].as_dict() == {
        "code": "CODEBOOK_CHOICE_VALUE_MISSING",
        "layer": "composition",
        "severity": "error",
        "message": "Choice list 'foods' has an emitted choice with no value.",
        "owner": {"model": "choice_list", "name": "foods"},
        "field": "name",
        "sheet": "choices",
        "column": "name",
        "row": 2,
    }


@pytest.mark.parametrize("missing_label", [None, "", "   "])
@pytest.mark.parametrize("label_column", ["label", "label::English (en)"])
def test_codebook_validation_reports_missing_english_label(
    missing_label,
    label_column,
):
    xlsx = _codebook_workbook(
        [("select_one foods", "preferred_food")],
        [("foods", "rice", missing_label)],
        label_column=label_column,
    )

    issues = validate_codebook_integrity(xlsx)

    assert [issue.code for issue in issues] == ["CODEBOOK_CHOICE_LABEL_MISSING"]
    assert issues[0].as_dict() == {
        "code": "CODEBOOK_CHOICE_LABEL_MISSING",
        "layer": "composition",
        "severity": "error",
        "message": "Choice 'rice' in choice list 'foods' has no English label.",
        "owner": {"model": "choice", "name": "rice", "choice_list": "foods"},
        "field": "label",
        "sheet": "choices",
        "column": label_column,
        "row": 2,
    }


def test_codebook_validation_accepts_numeric_choice_value():
    xlsx = _codebook_workbook(
        [("select_one foods", "preferred_food")],
        [("foods", 0, "None")],
    )

    assert validate_codebook_integrity(xlsx) == []


def test_codebook_validation_does_not_decide_non_english_label_fallback():
    xlsx = _codebook_workbook(
        [("select_one foods", "preferred_food")],
        [("foods", "rice", "")],
        label_column="label::French (fr)",
    )

    assert validate_codebook_integrity(xlsx) == []


def test_codebook_validation_ignores_external_selects():
    xlsx = _codebook_workbook([("select_one_from_file foods.csv", "preferred_food")])

    assert validate_codebook_integrity(xlsx) == []


def test_composition_errors_block_pyxform_conversion():
    artifact = GeneratedSurveyArtifact(
        _codebook_workbook([("select_one foods", "preferred_food")])
    )

    result = validate_generated_artifact(artifact, converter_cls=ConversionMustNotRun)

    assert result.valid is False
    assert [issue.code for issue in result.errors] == [
        "CODEBOOK_CHOICE_LIST_NOT_EMITTED"
    ]


def test_generated_survey_reports_internal_select_without_choice_group(
    submodule_1,
    root_question_2,
):
    root_question_2.choices = None
    root_question_2.save(update_fields=["choices"])
    form = XLSForm(
        name="Missing choice group",
        submodule_ids=[submodule_1.id],
        sub_question_ids=[],
        submodules_order=[submodule_1.id],
    )

    result = validate_generated_artifact(
        build_generated_artifact(form), converter_cls=ConversionMustNotRun
    )

    assert [issue.code for issue in result.errors] == ["CODEBOOK_CHOICE_LIST_MISSING"]
    assert result.errors[0].owner == {
        "model": "question",
        "name": root_question_2.name,
    }


def test_generated_survey_reports_choice_group_without_active_choices(
    submodule_1,
    root_question_2,
    choices_1,
):
    choices_1.choices.update(is_active=False)
    form = XLSForm(
        name="Inactive choices",
        submodule_ids=[submodule_1.id],
        sub_question_ids=[],
        submodules_order=[submodule_1.id],
    )

    result = validate_generated_artifact(
        build_generated_artifact(form), converter_cls=ConversionMustNotRun
    )

    assert [issue.code for issue in result.errors] == [
        "CODEBOOK_CHOICE_LIST_NOT_EMITTED"
    ]
    assert f"choice list '{choices_1.name}'" in result.errors[0].message


def test_generated_survey_reports_blank_choice_value(
    submodule_1,
    root_question_2,
    choices_1,
):
    choice = choices_1.choices.first()
    choices_1.choices.filter(id=choice.id).update(name="   ")
    form = XLSForm(
        name="Blank choice value",
        submodule_ids=[submodule_1.id],
        sub_question_ids=[],
        submodules_order=[submodule_1.id],
    )

    result = validate_generated_artifact(
        build_generated_artifact(form), converter_cls=ConversionMustNotRun
    )

    assert [issue.code for issue in result.errors] == ["CODEBOOK_CHOICE_VALUE_MISSING"]
    assert result.errors[0].owner == {
        "model": "choice_list",
        "name": choices_1.name,
    }


def test_generated_survey_reports_blank_english_choice_label(
    submodule_1,
    root_question_2,
    choices_1,
):
    choice = choices_1.choices.first()
    choices_1.choices.filter(id=choice.id).update(label="   ")
    form = XLSForm(
        name="Blank choice label",
        submodule_ids=[submodule_1.id],
        sub_question_ids=[],
        submodules_order=[submodule_1.id],
        languages=["en"],
    )

    result = validate_generated_artifact(
        build_generated_artifact(form), converter_cls=ConversionMustNotRun
    )

    assert [issue.code for issue in result.errors] == ["CODEBOOK_CHOICE_LABEL_MISSING"]
    assert result.errors[0].owner == {
        "model": "choice",
        "name": choice.name,
        "choice_list": choices_1.name,
    }


def test_empty_external_file_is_a_structured_input_error():
    with pytest.raises(ArtifactInputError) as raised:
        materialize_external_files(
            {"choices.csv": ContentFile(b"", name="choices.csv")}
        )

    assert isinstance(raised.value.issue, ValidationIssue)
    assert raised.value.issue.code == "EXTERNAL_FILE_EMPTY"


def test_xml_conversion_disables_java_validation(monkeypatch):
    calls = {}

    class Converted:
        xform = "<xform/>"

    def convert(xlsform, **kwargs):
        calls.update(kwargs)
        return Converted()

    monkeypatch.setattr("questions.services.xml_conversion.xls2xform.convert", convert)

    conversion = XMLConversion(io.BytesIO(b"xlsx"))
    assert conversion.run() == "<xform/>"
    assert calls["validate"] is False
    assert calls["pretty_print"] is True
    assert calls["enketo"] is False
