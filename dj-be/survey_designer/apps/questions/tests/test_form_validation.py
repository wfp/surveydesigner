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


def test_codebook_validation_reports_duplicate_value_in_same_list():
    xlsx = _codebook_workbook(
        [("select_one foods", "preferred_food")],
        [
            ("foods", "rice", "Rice"),
            ("foods", "rice", "Rice duplicate"),
        ],
    )

    issues = validate_codebook_integrity(xlsx)

    assert [issue.code for issue in issues] == ["CODEBOOK_CHOICE_VALUE_DUPLICATE"]
    assert issues[0].as_dict() == {
        "code": "CODEBOOK_CHOICE_VALUE_DUPLICATE",
        "layer": "composition",
        "severity": "error",
        "message": "Choice value 'rice' is duplicated in choice list 'foods'; it was first emitted at row 2.",
        "owner": {"model": "choice", "name": "rice", "choice_list": "foods"},
        "field": "name",
        "sheet": "choices",
        "column": "name",
        "row": 3,
    }


def test_codebook_validation_reports_every_duplicate_after_first_row():
    xlsx = _codebook_workbook(
        [("select_one foods", "preferred_food")],
        [
            ("foods", "rice", "Rice"),
            ("foods", "rice", "Rice duplicate"),
            ("foods", "rice", "Rice duplicate again"),
        ],
    )

    issues = validate_codebook_integrity(xlsx)

    assert [issue.row for issue in issues] == [3, 4]
    assert all("first emitted at row 2" in issue.message for issue in issues)


def test_codebook_validation_allows_same_value_in_different_lists():
    xlsx = _codebook_workbook(
        [
            ("select_one foods", "preferred_food"),
            ("select_one drinks", "preferred_drink"),
        ],
        [
            ("foods", "other", "Other food"),
            ("drinks", "other", "Other drink"),
        ],
    )

    assert validate_codebook_integrity(xlsx) == []


def test_codebook_validation_compares_choice_values_case_sensitively():
    xlsx = _codebook_workbook(
        [("select_one foods", "preferred_food")],
        [
            ("foods", "Other", "Uppercase"),
            ("foods", "other", "Lowercase"),
        ],
    )

    assert validate_codebook_integrity(xlsx) == []


@pytest.mark.parametrize(
    "first_value, duplicate_value",
    [(" rice ", "rice"), (1, "1")],
)
def test_codebook_validation_uses_emitted_value_normalization_for_duplicates(
    first_value,
    duplicate_value,
):
    xlsx = _codebook_workbook(
        [("select_one foods", "preferred_food")],
        [
            ("foods", first_value, "First"),
            ("foods", duplicate_value, "Duplicate"),
        ],
    )

    issues = validate_codebook_integrity(xlsx)

    assert [issue.code for issue in issues] == ["CODEBOOK_CHOICE_VALUE_DUPLICATE"]


def test_duplicate_choice_value_blocks_pyxform_conversion():
    artifact = GeneratedSurveyArtifact(
        _codebook_workbook(
            [("select_one foods", "preferred_food")],
            [
                ("foods", "rice", "Rice"),
                ("foods", "rice", "Rice duplicate"),
            ],
        )
    )

    result = validate_generated_artifact(artifact, converter_cls=ConversionMustNotRun)

    assert result.valid is False
    assert [issue.code for issue in result.errors] == [
        "CODEBOOK_CHOICE_VALUE_DUPLICATE"
    ]


def test_codebook_export_layout_reports_duplicate_choice_value():
    xlsx = _codebook_workbook(
        [("select_one", "preferred_food", "foods")],
        [
            ("foods", "rice", "Rice"),
            ("foods", "rice", "Rice duplicate"),
        ],
        export_columns=True,
    )

    issues = validate_codebook_integrity(xlsx)

    assert [issue.code for issue in issues] == ["CODEBOOK_CHOICE_VALUE_DUPLICATE"]


@pytest.mark.parametrize(
    "list_name",
    ["foods", "_foods", "food-list", "food.list", "food_1", "éfoods"],
)
def test_codebook_validation_accepts_compatible_choice_list_names(list_name):
    xlsx = _codebook_workbook(
        [(f"select_one {list_name}", "preferred_food")],
        [(list_name, "rice", "Rice")],
    )

    assert validate_codebook_integrity(xlsx) == []


@pytest.mark.parametrize(
    "list_name",
    ["1foods", "food list", "food$list", "food/list", "food:items"],
)
def test_codebook_validation_reports_invalid_choice_list_name(list_name):
    xlsx = _codebook_workbook(
        [(f"select_one {list_name}", "preferred_food")],
        [(list_name, "rice", "Rice")],
    )

    issues = validate_codebook_integrity(xlsx)

    assert [issue.code for issue in issues] == ["CODEBOOK_CHOICE_LIST_NAME_INVALID"]
    assert issues[0].as_dict() == {
        "code": "CODEBOOK_CHOICE_LIST_NAME_INVALID",
        "layer": "composition",
        "severity": "error",
        "message": f"Choice list name '{list_name}' is invalid. Names must begin with a letter or underscore and contain only letters, digits, underscores, hyphens, or periods.",
        "owner": {"model": "choice_list", "name": list_name},
        "field": "list_name",
        "sheet": "choices",
        "column": "list_name",
        "row": 2,
    }


def test_invalid_unemitted_choice_list_name_is_reported_at_question():
    xlsx = _codebook_workbook([("select_one 1foods", "preferred_food")])

    issues = validate_codebook_integrity(xlsx)

    assert [issue.code for issue in issues] == [
        "CODEBOOK_CHOICE_LIST_NAME_INVALID",
        "CODEBOOK_CHOICE_LIST_NOT_EMITTED",
    ]
    assert issues[0].sheet == "survey"
    assert issues[0].row == 2
    assert issues[0].owner == {"model": "question", "name": "preferred_food"}


def test_codebook_validation_reports_choice_row_without_list_name():
    xlsx = _codebook_workbook(
        [("select_one foods", "preferred_food")],
        [("", "rice", "Rice")],
    )

    issues = validate_codebook_integrity(xlsx)

    assert [issue.code for issue in issues] == [
        "CODEBOOK_CHOICE_LIST_NAME_MISSING",
        "CODEBOOK_CHOICE_LIST_NOT_EMITTED",
    ]
    assert issues[0].as_dict() == {
        "code": "CODEBOOK_CHOICE_LIST_NAME_MISSING",
        "layer": "composition",
        "severity": "error",
        "message": "An emitted choice row does not specify a choice list name.",
        "owner": {"model": "choice", "name": "rice"},
        "field": "list_name",
        "sheet": "choices",
        "column": "list_name",
        "row": 2,
    }


@pytest.mark.parametrize("choice_value", ["with space", "with\tspace"])
def test_codebook_validation_rejects_whitespace_in_select_multiple_value(
    choice_value,
):
    xlsx = _codebook_workbook(
        [("select_multiple foods", "preferred_foods")],
        [("foods", choice_value, "Value")],
    )

    issues = validate_codebook_integrity(xlsx)

    assert [issue.code for issue in issues] == ["CODEBOOK_CHOICE_VALUE_INVALID"]
    assert issues[0].as_dict() == {
        "code": "CODEBOOK_CHOICE_VALUE_INVALID",
        "layer": "composition",
        "severity": "error",
        "message": f"Choice value '{choice_value}' in choice list 'foods' contains whitespace, which is not supported by select_multiple questions.",
        "owner": {
            "model": "choice",
            "name": choice_value,
            "choice_list": "foods",
        },
        "field": "name",
        "sheet": "choices",
        "column": "name",
        "row": 2,
    }


def test_codebook_validation_allows_whitespace_in_select_one_value():
    xlsx = _codebook_workbook(
        [("select_one foods", "preferred_food")],
        [("foods", "white rice", "White rice")],
    )

    assert validate_codebook_integrity(xlsx) == []


def test_codebook_validation_uses_strictest_type_for_shared_choice_list():
    xlsx = _codebook_workbook(
        [
            ("select_one foods", "preferred_food"),
            ("select_multiple foods", "preferred_foods"),
        ],
        [("foods", "white rice", "White rice")],
    )

    issues = validate_codebook_integrity(xlsx)

    assert [issue.code for issue in issues] == ["CODEBOOK_CHOICE_VALUE_INVALID"]


@pytest.mark.parametrize(
    "choice_value",
    ["1", "1.5", "-1", "a-b", "a.b", "a/b", "a:b", "é"],
)
def test_codebook_validation_accepts_compatible_select_multiple_values(choice_value):
    xlsx = _codebook_workbook(
        [("select_multiple foods", "preferred_foods")],
        [("foods", choice_value, "Value")],
    )

    assert validate_codebook_integrity(xlsx) == []


def test_choice_value_syntax_validation_supports_codebook_export_layout():
    xlsx = _codebook_workbook(
        [("select_multiple", "preferred_foods", "foods")],
        [("foods", "white rice", "White rice")],
        export_columns=True,
    )

    issues = validate_codebook_integrity(xlsx)

    assert [issue.code for issue in issues] == ["CODEBOOK_CHOICE_VALUE_INVALID"]


def test_invalid_choice_syntax_blocks_pyxform_conversion():
    artifact = GeneratedSurveyArtifact(
        _codebook_workbook(
            [("select_multiple foods", "preferred_foods")],
            [("foods", "white rice", "White rice")],
        )
    )

    result = validate_generated_artifact(artifact, converter_cls=ConversionMustNotRun)

    assert result.valid is False
    assert [issue.code for issue in result.errors] == ["CODEBOOK_CHOICE_VALUE_INVALID"]


def test_codebook_validation_reports_missing_generated_name():
    xlsx = _codebook_workbook([("text", "")])

    issues = validate_codebook_integrity(xlsx)

    assert [issue.code for issue in issues] == ["CODEBOOK_GENERATED_NAME_MISSING"]
    assert issues[0].as_dict() == {
        "code": "CODEBOOK_GENERATED_NAME_MISSING",
        "layer": "composition",
        "severity": "error",
        "message": "Survey row 2 of type 'text' requires a generated name.",
        "owner": {"model": "question", "type": "text"},
        "field": "name",
        "sheet": "survey",
        "column": "name",
        "row": 2,
    }


def test_codebook_validation_allows_unnamed_closing_rows():
    xlsx = _codebook_workbook(
        [
            ("begin_group", "household"),
            ("end_group", ""),
            ("begin_repeat", "members"),
            ("end repeat", ""),
        ]
    )

    assert validate_codebook_integrity(xlsx) == []


@pytest.mark.parametrize(
    "name",
    ["1question", "question name", "question$name", "question/name", "question:name"],
)
def test_codebook_validation_reports_invalid_generated_name(name):
    xlsx = _codebook_workbook([("text", name)])

    issues = validate_codebook_integrity(xlsx)

    assert [issue.code for issue in issues] == ["CODEBOOK_GENERATED_NAME_INVALID"]
    assert issues[0].as_dict() == {
        "code": "CODEBOOK_GENERATED_NAME_INVALID",
        "layer": "composition",
        "severity": "error",
        "message": f"Generated question name '{name}' is invalid. Names must begin with a letter or underscore and contain only letters, digits, underscores, hyphens, or periods.",
        "owner": {"model": "question", "name": name, "type": "text"},
        "field": "name",
        "sheet": "survey",
        "column": "name",
        "row": 2,
    }


@pytest.mark.parametrize(
    "name",
    ["question", "_question", "question-1", "question.1", "question_1", "équestion"],
)
def test_codebook_validation_accepts_compatible_generated_name(name):
    xlsx = _codebook_workbook([("text", name)])

    assert validate_codebook_integrity(xlsx) == []


def test_codebook_validation_rejects_reserved_generated_name():
    xlsx = _codebook_workbook([("text", "meta")])

    issues = validate_codebook_integrity(xlsx)

    assert [issue.code for issue in issues] == ["CODEBOOK_GENERATED_NAME_INVALID"]
    assert issues[0].message == (
        "Generated question name 'meta' is reserved and cannot be emitted on the "
        "survey sheet."
    )


def test_codebook_validation_reports_duplicate_generated_name_across_row_types():
    xlsx = _codebook_workbook(
        [
            ("begin_group", "household"),
            ("text", "household"),
            ("end_group", ""),
        ]
    )

    issues = validate_codebook_integrity(xlsx)

    assert [issue.code for issue in issues] == ["CODEBOOK_GENERATED_NAME_DUPLICATE"]
    assert issues[0].as_dict() == {
        "code": "CODEBOOK_GENERATED_NAME_DUPLICATE",
        "layer": "composition",
        "severity": "error",
        "message": "Generated question name 'household' duplicates a group first emitted at survey row 2.",
        "owner": {
            "model": "question",
            "name": "household",
            "type": "text",
            "first_model": "group",
            "first_row": 2,
        },
        "field": "name",
        "sheet": "survey",
        "column": "name",
        "row": 3,
    }


def test_codebook_validation_reports_every_generated_name_duplicate_after_first():
    xlsx = _codebook_workbook(
        [("text", "shared"), ("integer", "shared"), ("decimal", "shared")]
    )

    issues = validate_codebook_integrity(xlsx)

    assert [issue.row for issue in issues] == [3, 4]
    assert all(issue.code == "CODEBOOK_GENERATED_NAME_DUPLICATE" for issue in issues)
    assert all("first emitted at survey row 2" in issue.message for issue in issues)


def test_codebook_validation_compares_generated_names_case_sensitively():
    xlsx = _codebook_workbook([("text", "Household"), ("text", "household")])

    assert validate_codebook_integrity(xlsx) == []


def test_questions_export_layout_does_not_apply_final_name_collision_rule():
    xlsx = _codebook_workbook(
        [("text", "shared", ""), ("text", "shared", "")],
        export_columns=True,
    )

    assert validate_codebook_integrity(xlsx) == []


def test_invalid_generated_name_blocks_pyxform_conversion():
    artifact = GeneratedSurveyArtifact(_codebook_workbook([("text", "1invalid")]))

    result = validate_generated_artifact(artifact, converter_cls=ConversionMustNotRun)

    assert result.valid is False
    assert [issue.code for issue in result.errors] == [
        "CODEBOOK_GENERATED_NAME_INVALID"
    ]


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


def test_generated_survey_reports_invalid_choice_list_name(
    submodule_1,
    root_question_2,
    choices_1,
):
    choices_1.name = "1invalid"
    choices_1.save(update_fields=["name"])
    form = XLSForm(
        name="Invalid choice list name",
        submodule_ids=[submodule_1.id],
        sub_question_ids=[],
        submodules_order=[submodule_1.id],
    )

    result = validate_generated_artifact(
        build_generated_artifact(form), converter_cls=ConversionMustNotRun
    )

    assert [issue.code for issue in result.errors] == [
        "CODEBOOK_CHOICE_LIST_NAME_INVALID"
    ]
    assert result.errors[0].owner == {
        "model": "choice_list",
        "name": "1invalid",
    }


def test_generated_select_multiple_reports_choice_value_with_whitespace(
    submodule_1,
    root_question_2,
    choices_1,
):
    choice = choices_1.choices.first()
    choices_1.choices.filter(id=choice.id).update(name="with space")
    form = XLSForm(
        name="Invalid choice value",
        submodule_ids=[submodule_1.id],
        sub_question_ids=[],
        submodules_order=[submodule_1.id],
    )

    result = validate_generated_artifact(
        build_generated_artifact(form), converter_cls=ConversionMustNotRun
    )

    assert [issue.code for issue in result.errors] == ["CODEBOOK_CHOICE_VALUE_INVALID"]
    assert result.errors[0].owner == {
        "model": "choice",
        "name": "with space",
        "choice_list": choices_1.name,
    }


def test_generated_survey_reports_missing_question_name(
    submodule_1,
    root_question_1,
):
    root_question_1.name = ""
    root_question_1.save(update_fields=["name"])
    form = XLSForm(
        name="Missing generated name",
        submodule_ids=[submodule_1.id],
        sub_question_ids=[],
        submodules_order=[submodule_1.id],
    )

    result = validate_generated_artifact(
        build_generated_artifact(form), converter_cls=ConversionMustNotRun
    )

    assert [issue.code for issue in result.errors] == [
        "CODEBOOK_GENERATED_NAME_MISSING"
    ]
    assert result.errors[0].owner == {"model": "question", "type": "integer"}


def test_generated_survey_reports_invalid_question_name(
    submodule_1,
    root_question_1,
):
    root_question_1.name = "1invalid"
    root_question_1.save(update_fields=["name"])
    form = XLSForm(
        name="Invalid generated name",
        submodule_ids=[submodule_1.id],
        sub_question_ids=[],
        submodules_order=[submodule_1.id],
    )

    result = validate_generated_artifact(
        build_generated_artifact(form), converter_cls=ConversionMustNotRun
    )

    assert [issue.code for issue in result.errors] == [
        "CODEBOOK_GENERATED_NAME_INVALID"
    ]
    assert result.errors[0].owner == {
        "model": "question",
        "name": "1invalid",
        "type": "integer",
    }


def test_generated_survey_reports_root_and_subquestion_name_collision(
    submodule_1,
    root_question_1,
    sub_question_1,
):
    type(sub_question_1).objects.filter(id=sub_question_1.id).update(
        name=root_question_1.name
    )
    sub_question_1.refresh_from_db()
    form = XLSForm(
        name="Duplicate generated name",
        submodule_ids=[submodule_1.id],
        sub_question_ids=[sub_question_1.id],
        submodules_order=[submodule_1.id],
    )

    result = validate_generated_artifact(
        build_generated_artifact(form), converter_cls=ConversionMustNotRun
    )

    assert [issue.code for issue in result.errors] == [
        "CODEBOOK_GENERATED_NAME_DUPLICATE"
    ]
    assert result.errors[0].owner["model"] == "question"
    assert result.errors[0].owner["name"] == root_question_1.name
    assert result.errors[0].owner["first_model"] == "question"
    assert result.errors[0].owner["first_row"] < result.errors[0].row


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
