"""Exact XLSForm artifact validation used by publication boundaries.

This module deliberately stops at pyxform's Python conversion boundary.  The
application does not install or invoke Java/ODK Validate.  The small XML
compatibility validator below is versioned so that its coverage can be
expanded without changing the public issue contract.
"""

from __future__ import annotations

import hashlib
import io
import re
from collections import defaultdict
from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Any, Mapping, Sequence
from xml.etree import ElementTree as ET

from openpyxl import load_workbook
from pyxform.parsing.expression import is_xml_tag

PYXFORM_VERSION = "4.5.0"
COMPATIBILITY_VERSION = "1.0"
_EMPTY_ARTIFACT_HASH = "sha256:" + hashlib.sha256(b"").hexdigest()
_XFORMS_NS = "http://www.w3.org/2002/xforms"
_XHTML_NS = "http://www.w3.org/1999/xhtml"
_EXTERNAL_REFERENCE = re.compile(r"jr://file-csv/([^/]+)$")
_ENGLISH_LABEL_COLUMN = re.compile(r"^label::.*\(\s*en\s*\)$", re.IGNORECASE)
_INTERNAL_SELECT_TYPES = ("select_one", "select_multiple")
_END_SURVEY_ROW_TYPES = frozenset(("end_group", "end_repeat"))
_RESERVED_SURVEY_NAMES = frozenset(("meta",))
_SURVEY_METADATA_TYPES = frozenset(("start", "end", "today", "deviceid"))


class ArtifactInputError(Exception):
    """The submitted/generated artifact cannot be published."""

    def __init__(self, issue: "ValidationIssue") -> None:
        super().__init__(issue.message)
        self.issue = issue


class ArtifactInfrastructureError(Exception):
    """The generator or artifact storage could not produce a stable artifact."""


class ValidatorInfrastructureError(Exception):
    """The configured validator could not complete reliably."""


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    layer: str
    severity: str
    message: str
    owner: Mapping[str, Any] | None = None
    field: str | None = None
    sheet: str | None = None
    column: str | None = None
    row: int | None = None

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "code": self.code,
            "layer": self.layer,
            "severity": self.severity,
            "message": self.message,
        }
        for key in ("owner", "field", "sheet", "column", "row"):
            value = getattr(self, key)
            if value is not None:
                result[key] = dict(value) if key == "owner" else value
        return result

    to_dict = as_dict


def compute_artifact_hash(
    xlsx_bytes: bytes, external_files: Mapping[str, bytes] | None = None
) -> str:
    """Return a stable, unambiguous hash for the complete publication artifact."""

    digest = hashlib.sha256()
    digest.update(b"survey-designer-artifact-v1\0")

    def add_part(value: bytes) -> None:
        digest.update(len(value).to_bytes(8, byteorder="big"))
        digest.update(value)

    add_part(bytes(xlsx_bytes))
    for filename in sorted((external_files or {})):
        name_bytes = str(filename).encode("utf-8")
        add_part(name_bytes)
        add_part(bytes((external_files or {})[filename]))
    return f"sha256:{digest.hexdigest()}"


@dataclass(frozen=True)
class GeneratedSurveyArtifact:
    """The immutable bytes and conversion output for one generated survey."""

    xlsx_bytes: bytes
    external_files: Mapping[str, bytes] = field(default_factory=dict)
    artifact_hash: str | None = None
    xml: str | None = None
    row_source_map: Mapping[str, Any] | None = None
    form_name: str = "survey"

    def __post_init__(self) -> None:
        xlsx_bytes = bytes(self.xlsx_bytes)
        external_files = {
            str(name): bytes(content)
            for name, content in dict(self.external_files).items()
        }
        object.__setattr__(self, "xlsx_bytes", xlsx_bytes)
        object.__setattr__(self, "external_files", MappingProxyType(external_files))
        if self.row_source_map is not None:
            object.__setattr__(
                self,
                "row_source_map",
                MappingProxyType(dict(self.row_source_map)),
            )
        artifact_hash = self.artifact_hash or compute_artifact_hash(
            xlsx_bytes, external_files
        )
        object.__setattr__(self, "artifact_hash", artifact_hash)


@dataclass(frozen=True)
class ValidationResult:
    """Public validation response plus the successful exact artifact internally."""

    valid: bool
    artifact_hash: str = _EMPTY_ARTIFACT_HASH
    errors: Sequence[ValidationIssue] = field(default_factory=tuple)
    warnings: Sequence[ValidationIssue] = field(default_factory=tuple)
    validator: Mapping[str, str] = field(
        default_factory=lambda: {
            "pyxform": PYXFORM_VERSION,
            "compatibility": COMPATIBILITY_VERSION,
        }
    )
    artifact: GeneratedSurveyArtifact | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        errors = tuple(self.errors)
        warnings = tuple(self.warnings)
        object.__setattr__(self, "errors", errors)
        object.__setattr__(self, "warnings", warnings)
        object.__setattr__(self, "valid", not errors)
        object.__setattr__(self, "validator", MappingProxyType(dict(self.validator)))

    def as_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "artifact_hash": self.artifact_hash,
            "errors": [issue.as_dict() for issue in self.errors],
            "warnings": [issue.as_dict() for issue in self.warnings],
            "validator": {
                "pyxform": self.validator.get("pyxform", PYXFORM_VERSION),
                "compatibility": self.validator.get(
                    "compatibility", COMPATIBILITY_VERSION
                ),
            },
        }

    # This alias makes the contract convenient for serializers and callers that
    # use the usual ``to_dict`` naming.
    to_dict = as_dict


def _issue(
    code: str,
    layer: str,
    message: str,
    *,
    severity: str = "error",
    **details: Any,
) -> ValidationIssue:
    return ValidationIssue(
        code=code,
        layer=layer,
        severity=severity,
        message=str(message),
        **{key: value for key, value in details.items() if value is not None},
    )


def _normalise_messages(
    messages: Sequence[Any], *, warning: bool
) -> list[ValidationIssue]:
    return [
        _issue(
            "PYXFORM_WARNING" if warning else "PYXFORM_CONVERSION_ERROR",
            "pyxform",
            str(message),
            severity="warning" if warning else "error",
        )
        for message in messages
        if str(message).strip()
    ]


def validate_xml_compatibility(
    xml: str | bytes | None, external_files: Mapping[str, bytes] | None = None
) -> list[ValidationIssue]:
    """Check minimal pyxform output and exact-artifact file references.

    This is not a JavaRosa or ODK Validate replacement. Pyxform performs the
    XLSForm checks; this seam only confirms the generated XForm shell and that
    referenced CSV files are present in the materialized artifact.
    """

    try:
        root = ET.fromstring(xml)
    except (ET.ParseError, TypeError, ValueError) as exc:
        return [
            _issue(
                "XML_MALFORMED",
                "compatibility",
                f"Generated XML is not well formed: {exc}",
                sheet="survey",
            )
        ]

    issues: list[ValidationIssue] = []
    if root.tag != f"{{{_XHTML_NS}}}html":
        issues.append(
            _issue(
                "XML_ROOT_INVALID",
                "compatibility",
                "Generated XForm must have an XHTML html root element.",
                sheet="survey",
            )
        )

    model = root.find(f".//{{{_XFORMS_NS}}}model")
    body = root.find(f".//{{{_XHTML_NS}}}body")
    instances = root.findall(f".//{{{_XFORMS_NS}}}instance")
    if model is None:
        issues.append(
            _issue(
                "XML_MODEL_MISSING",
                "compatibility",
                "Generated XForm is missing its xforms model.",
                sheet="survey",
            )
        )
    if body is None:
        issues.append(
            _issue(
                "XML_BODY_MISSING",
                "compatibility",
                "Generated XForm is missing its XHTML body.",
                sheet="survey",
            )
        )
    if not instances:
        issues.append(
            _issue(
                "XML_INSTANCE_MISSING",
                "compatibility",
                "Generated XForm is missing a primary instance.",
                sheet="survey",
            )
        )

    available_files = set((external_files or {}).keys())
    for element in root.iter():
        for attribute in ("src", "href"):
            value = element.get(attribute)
            if not value:
                continue
            match = _EXTERNAL_REFERENCE.match(value)
            if match and match.group(1) not in available_files:
                issues.append(
                    _issue(
                        "EXTERNAL_FILE_MISSING",
                        "compatibility",
                        f"Generated XForm references external file '{match.group(1)}', but that file is not materialized.",
                        sheet="survey",
                        field=match.group(1),
                    )
                )
    return issues


def materialize_external_files(
    external_files: Mapping[str, Any] | None,
) -> dict[str, bytes]:
    """Read every selected external file exactly once and retain its bytes."""

    materialized: dict[str, bytes] = {}
    for filename, file_obj in (external_files or {}).items():
        filename = str(filename)
        try:
            stream = file_obj.open("rb")
            try:
                content = stream.read()
            finally:
                stream.close()
        except FileNotFoundError:
            raise ArtifactInputError(
                _issue(
                    "EXTERNAL_FILE_MISSING",
                    "composition",
                    f"External file '{filename}' could not be found.",
                    field=filename,
                )
            )
        except OSError as exc:
            raise ArtifactInfrastructureError(
                f"Unable to read external file '{filename}': {exc}"
            ) from exc

        if not content:
            raise ArtifactInputError(
                _issue(
                    "EXTERNAL_FILE_EMPTY",
                    "composition",
                    f"External file '{filename}' is empty.",
                    field=filename,
                )
            )
        materialized[filename] = content
    return materialized


def _sheet_rows_by_header(
    worksheet: Any,
) -> tuple[dict[str, int], list[tuple[Any, ...]]]:
    rows = list(worksheet.iter_rows(values_only=True))
    if not rows:
        return {}, []

    headers = {
        str(value).strip(): index
        for index, value in enumerate(rows[0])
        if value is not None and str(value).strip()
    }
    return headers, rows[1:]


def _row_value(row: tuple[Any, ...], headers: Mapping[str, int], column: str) -> str:
    index = headers.get(column)
    if index is None or index >= len(row) or row[index] is None:
        return ""
    return str(row[index]).strip()


def _english_label_column(headers: Mapping[str, int]) -> str | None:
    if "label" in headers:
        return "label"
    return next(
        (column for column in headers if _ENGLISH_LABEL_COLUMN.match(column)), None
    )


def _internal_select_declaration(
    row: tuple[Any, ...], survey_headers: Mapping[str, int]
) -> tuple[str, str, str] | None:
    declaration = _row_value(row, survey_headers, "type")
    question_type, _, inline_list_name = declaration.partition(" ")
    if question_type not in _INTERNAL_SELECT_TYPES:
        return None

    list_column = "choice_list" if "choice_list" in survey_headers else "type"
    list_name = (
        _row_value(row, survey_headers, "choice_list")
        if "choice_list" in survey_headers
        else inline_list_name.strip()
    )
    return question_type, list_name, list_column


def _is_valid_choice_list_name(value: str) -> bool:
    return bool(value) and ":" not in value and is_xml_tag(value)


def _normalized_survey_row_type(value: str) -> str:
    return value.lower().replace(" ", "_")


def _generated_survey_owner(row_type: str, name: str = "") -> dict[str, Any]:
    normalized_type = _normalized_survey_row_type(row_type)
    if normalized_type == "begin_group":
        model = "group"
    elif normalized_type == "begin_repeat":
        model = "repeat"
    elif normalized_type in _SURVEY_METADATA_TYPES:
        model = "metadata"
    else:
        model = "question"

    owner = {"model": model}
    if name:
        owner["name"] = name
    if row_type:
        owner["type"] = row_type
    return owner


def _validate_generated_survey_names(
    survey_headers: Mapping[str, int], survey_rows: Sequence[tuple[Any, ...]]
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    first_name_rows: dict[str, tuple[int, Mapping[str, Any]]] = {}

    for row_number, row in enumerate(survey_rows, start=2):
        row_type = _row_value(row, survey_headers, "type")
        name = _row_value(row, survey_headers, "name")
        if not row_type and not name:
            continue

        normalized_type = _normalized_survey_row_type(row_type)
        if normalized_type in _END_SURVEY_ROW_TYPES:
            continue

        owner = _generated_survey_owner(row_type, name)
        if not name:
            issues.append(
                _issue(
                    "CODEBOOK_GENERATED_NAME_MISSING",
                    "composition",
                    f"Survey row {row_number} of type '{row_type}' requires a generated name.",
                    owner=owner,
                    field="name",
                    sheet="survey",
                    column="name",
                    row=row_number,
                )
            )
            continue

        if name in _RESERVED_SURVEY_NAMES:
            issues.append(
                _issue(
                    "CODEBOOK_GENERATED_NAME_INVALID",
                    "composition",
                    f"Generated {owner['model']} name '{name}' is reserved and cannot be emitted on the survey sheet.",
                    owner=owner,
                    field="name",
                    sheet="survey",
                    column="name",
                    row=row_number,
                )
            )
        elif ":" in name or not is_xml_tag(name):
            issues.append(
                _issue(
                    "CODEBOOK_GENERATED_NAME_INVALID",
                    "composition",
                    f"Generated {owner['model']} name '{name}' is invalid. Names must begin with a letter or underscore and contain only letters, digits, underscores, hyphens, or periods.",
                    owner=owner,
                    field="name",
                    sheet="survey",
                    column="name",
                    row=row_number,
                )
            )

        first_name = first_name_rows.setdefault(name, (row_number, owner))
        first_row, first_owner = first_name
        if first_row != row_number:
            duplicate_owner = dict(owner)
            duplicate_owner["first_model"] = first_owner["model"]
            duplicate_owner["first_row"] = first_row
            issues.append(
                _issue(
                    "CODEBOOK_GENERATED_NAME_DUPLICATE",
                    "composition",
                    f"Generated {owner['model']} name '{name}' duplicates a {first_owner['model']} first emitted at survey row {first_row}.",
                    owner=duplicate_owner,
                    field="name",
                    sheet="survey",
                    column="name",
                    row=row_number,
                )
            )

    return issues


def validate_codebook_integrity(xlsx_bytes: bytes) -> list[ValidationIssue]:
    """Validate internal select declarations and exact emitted choice rows."""

    workbook = load_workbook(io.BytesIO(xlsx_bytes), read_only=True, data_only=True)
    try:
        if "survey" not in workbook.sheetnames or "choices" not in workbook.sheetnames:
            return []

        survey_headers, survey_rows = _sheet_rows_by_header(workbook["survey"])
        choices_headers, choices_rows = _sheet_rows_by_header(workbook["choices"])
        issues = (
            _validate_generated_survey_names(survey_headers, survey_rows)
            if "choice_list" not in survey_headers
            else []
        )
        emitted_list_column = (
            "list_name" if "list_name" in choices_headers else "choice_list"
        )
        english_label_column = _english_label_column(choices_headers)
        internal_select_types_by_list: dict[str, set[str]] = defaultdict(set)
        for row in survey_rows:
            declaration = _internal_select_declaration(row, survey_headers)
            if declaration:
                question_type, list_name, _ = declaration
                if list_name:
                    internal_select_types_by_list[list_name].add(question_type)

        emitted_lists: set[str] = set()
        first_choice_value_rows: dict[tuple[str, str], int] = {}
        checked_list_names: set[str] = set()
        reported_invalid_list_names: set[str] = set()
        for row_number, row in enumerate(choices_rows, start=2):
            list_name = _row_value(row, choices_headers, emitted_list_column)
            choice_name = _row_value(row, choices_headers, "name")
            english_label = (
                _row_value(row, choices_headers, english_label_column)
                if english_label_column
                else ""
            )
            if not any((list_name, choice_name, english_label)):
                continue
            if not list_name:
                issues.append(
                    _issue(
                        "CODEBOOK_CHOICE_LIST_NAME_MISSING",
                        "composition",
                        "An emitted choice row does not specify a choice list name.",
                        owner={"model": "choice", "name": choice_name},
                        field=emitted_list_column,
                        sheet="choices",
                        column=emitted_list_column,
                        row=row_number,
                    )
                )
            else:
                emitted_lists.add(list_name)
                if list_name not in checked_list_names:
                    checked_list_names.add(list_name)
                    if not _is_valid_choice_list_name(list_name):
                        reported_invalid_list_names.add(list_name)
                        issues.append(
                            _issue(
                                "CODEBOOK_CHOICE_LIST_NAME_INVALID",
                                "composition",
                                f"Choice list name '{list_name}' is invalid. Names must begin with a letter or underscore and contain only letters, digits, underscores, hyphens, or periods.",
                                owner={"model": "choice_list", "name": list_name},
                                field=emitted_list_column,
                                sheet="choices",
                                column=emitted_list_column,
                                row=row_number,
                            )
                        )

            if not choice_name:
                issues.append(
                    _issue(
                        "CODEBOOK_CHOICE_VALUE_MISSING",
                        "composition",
                        f"Choice list '{list_name}' has an emitted choice with no value.",
                        owner={"model": "choice_list", "name": list_name},
                        field="name",
                        sheet="choices",
                        column="name",
                        row=row_number,
                    )
                )
            elif list_name:
                duplicate_key = (list_name, choice_name)
                first_row = first_choice_value_rows.setdefault(
                    duplicate_key, row_number
                )
                if first_row != row_number:
                    issues.append(
                        _issue(
                            "CODEBOOK_CHOICE_VALUE_DUPLICATE",
                            "composition",
                            f"Choice value '{choice_name}' is duplicated in choice list '{list_name}'; it was first emitted at row {first_row}.",
                            owner={
                                "model": "choice",
                                "name": choice_name,
                                "choice_list": list_name,
                            },
                            field="name",
                            sheet="choices",
                            column="name",
                            row=row_number,
                        )
                    )
                if "select_multiple" in internal_select_types_by_list[
                    list_name
                ] and any(character.isspace() for character in choice_name):
                    issues.append(
                        _issue(
                            "CODEBOOK_CHOICE_VALUE_INVALID",
                            "composition",
                            f"Choice value '{choice_name}' in choice list '{list_name}' contains whitespace, which is not supported by select_multiple questions.",
                            owner={
                                "model": "choice",
                                "name": choice_name,
                                "choice_list": list_name,
                            },
                            field="name",
                            sheet="choices",
                            column="name",
                            row=row_number,
                        )
                    )
            if english_label_column and not english_label:
                issues.append(
                    _issue(
                        "CODEBOOK_CHOICE_LABEL_MISSING",
                        "composition",
                        f"Choice '{choice_name}' in choice list '{list_name}' has no English label.",
                        owner={
                            "model": "choice",
                            "name": choice_name,
                            "choice_list": list_name,
                        },
                        field="label",
                        sheet="choices",
                        column=english_label_column,
                        row=row_number,
                    )
                )

        for row_number, row in enumerate(survey_rows, start=2):
            declaration = _internal_select_declaration(row, survey_headers)
            if not declaration:
                continue

            question_type, list_name, list_column = declaration
            question_name = _row_value(row, survey_headers, "name")
            owner = {"model": "question", "name": question_name}

            if not list_name:
                issues.append(
                    _issue(
                        "CODEBOOK_CHOICE_LIST_MISSING",
                        "composition",
                        f"Question '{question_name}' uses {question_type} but does not specify a choice list.",
                        owner=owner,
                        field="choices",
                        sheet="survey",
                        column=list_column,
                        row=row_number,
                    )
                )
                continue

            if (
                not _is_valid_choice_list_name(list_name)
                and list_name not in reported_invalid_list_names
            ):
                reported_invalid_list_names.add(list_name)
                issues.append(
                    _issue(
                        "CODEBOOK_CHOICE_LIST_NAME_INVALID",
                        "composition",
                        f"Choice list name '{list_name}' is invalid. Names must begin with a letter or underscore and contain only letters, digits, underscores, hyphens, or periods.",
                        owner=owner,
                        field="choices",
                        sheet="survey",
                        column=list_column,
                        row=row_number,
                    )
                )

            if list_name not in emitted_lists:
                issues.append(
                    _issue(
                        "CODEBOOK_CHOICE_LIST_NOT_EMITTED",
                        "composition",
                        f"Question '{question_name}' references choice list '{list_name}', but that list has no emitted choices.",
                        owner=owner,
                        field="choices",
                        sheet="survey",
                        column=list_column,
                        row=row_number,
                    )
                )
        return issues
    finally:
        workbook.close()


def build_generated_artifact(xlsx_form: Any) -> GeneratedSurveyArtifact:
    """Generate a workbook once and materialize its external files once."""

    try:
        xlsx_bytes = xlsx_form.generate()
    except Exception as exc:
        raise ArtifactInfrastructureError(f"Unable to generate XLSX: {exc}") from exc

    external_files = materialize_external_files(xlsx_form.external_files)
    return GeneratedSurveyArtifact(
        xlsx_bytes=xlsx_bytes,
        external_files=external_files,
        form_name=str(xlsx_form.id_name or "survey"),
    )


def validate_generated_artifact(
    artifact: GeneratedSurveyArtifact,
    *,
    converter_cls: Any | None = None,
) -> ValidationResult:
    """Convert and validate one exact artifact without generating it again."""

    try:
        composition_errors = validate_codebook_integrity(artifact.xlsx_bytes)
    except Exception as exc:
        raise ValidatorInfrastructureError(
            f"Unable to inspect the generated XLSX codebook: {exc}"
        ) from exc

    if composition_errors:
        return ValidationResult(
            valid=False,
            artifact_hash=artifact.artifact_hash,
            errors=composition_errors,
            artifact=artifact,
        )

    if converter_cls is None:
        from .xml_conversion import XMLConversion

        converter_cls = XMLConversion

    try:
        conversion = converter_cls(io.BytesIO(artifact.xlsx_bytes))
        xml = conversion.run()
    except Exception as exc:
        raise ValidatorInfrastructureError(
            f"pyxform conversion failed internally: {exc}"
        ) from exc

    errors = _normalise_messages(conversion.errors, warning=False)
    warnings = _normalise_messages(conversion.warnings, warning=True)
    if not errors:
        errors.extend(validate_xml_compatibility(xml, artifact.external_files))

    validated_artifact = replace(artifact, xml=xml)
    return ValidationResult(
        valid=not errors,
        artifact_hash=validated_artifact.artifact_hash or artifact.artifact_hash,
        errors=errors,
        warnings=warnings,
        artifact=validated_artifact,
    )


def failed_validation_result(
    issue: ValidationIssue, *, artifact_hash: str = _EMPTY_ARTIFACT_HASH
) -> ValidationResult:
    return ValidationResult(valid=False, artifact_hash=artifact_hash, errors=(issue,))


__all__ = [
    "ArtifactInfrastructureError",
    "ArtifactInputError",
    "COMPATIBILITY_VERSION",
    "GeneratedSurveyArtifact",
    "PYXFORM_VERSION",
    "ValidatorInfrastructureError",
    "ValidationIssue",
    "ValidationResult",
    "build_generated_artifact",
    "compute_artifact_hash",
    "failed_validation_result",
    "materialize_external_files",
    "validate_codebook_integrity",
    "validate_generated_artifact",
    "validate_xml_compatibility",
]
