import io

import pytest
from questions.services.form_validation import (
    ArtifactInputError,
    GeneratedSurveyArtifact,
    ValidationIssue,
    build_generated_artifact,
    compute_artifact_hash,
    materialize_external_files,
    validate_generated_artifact,
    validate_xml_compatibility,
)
from questions.services.xml_conversion import XMLConversion


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


def test_materialize_external_files_accepts_already_materialized_bytes():
    assert materialize_external_files({"choices.csv": b"name\nvalue\n"}) == {
        "choices.csv": b"name\nvalue\n"
    }


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

    artifact = GeneratedSurveyArtifact(b"xlsx")
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


def test_missing_xform_is_an_invalid_artifact():
    class Conversion:
        errors = []
        warnings = []

        def __init__(self, xlsx_file):
            pass

        def run(self):
            return None

    result = validate_generated_artifact(
        GeneratedSurveyArtifact(b"xlsx"), converter_cls=Conversion
    )

    assert result.valid is False
    assert result.errors[0].code == "PYXFORM_NO_XML"


def test_empty_external_file_is_a_structured_input_error():
    with pytest.raises(ArtifactInputError) as raised:
        materialize_external_files({"choices.csv": b""})

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
