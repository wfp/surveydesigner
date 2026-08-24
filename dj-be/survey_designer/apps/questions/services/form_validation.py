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
from dataclasses import dataclass, field, replace
from importlib.metadata import PackageNotFoundError, version as package_version
from types import MappingProxyType
from typing import Any, Mapping, Sequence
from xml.etree import ElementTree as ET

import pyxform


def _installed_pyxform_version() -> str | None:
    version_from_module = getattr(pyxform, "__version__", None)
    if version_from_module:
        return str(version_from_module)
    try:
        return package_version("pyxform")
    except PackageNotFoundError:
        return None


PYXFORM_INSTALLED_VERSION = _installed_pyxform_version()

PYXFORM_VERSION = "4.5.0"
COMPATIBILITY_VERSION = "1.0"
_EMPTY_ARTIFACT_HASH = "sha256:" + hashlib.sha256(b"").hexdigest()
_XFORMS_NS = "http://www.w3.org/2002/xforms"
_XHTML_NS = "http://www.w3.org/1999/xhtml"
_EXTERNAL_REFERENCE = re.compile(r"jr://(?:file-csv|images)/([^/]+)$")
_NCNAME = re.compile(r"^[A-Za-z_][A-Za-z0-9._-]*$")


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


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def validate_xml_compatibility(
    xml: str | bytes, external_files: Mapping[str, bytes] | None = None
) -> list[ValidationIssue]:
    """Run the intentionally small, no-Java XML structure compatibility check.

    This is not presented as a JavaRosa implementation.  It checks the stable
    structural contract that must hold before XML is stored or sent to Enketo,
    and is an extension seam for compatibility rules learned from the target
    deployment.
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

    # Empty bind paths are never useful to the renderer and usually indicate a
    # malformed emitted row.  Leave expression grammar to pyxform/compatibility
    # extensions rather than trying to reproduce the target validator here.
    for bind in root.findall(f".//{{{_XFORMS_NS}}}bind"):
        if not (bind.get("nodeset") or "").strip():
            issues.append(
                _issue(
                    "XML_BIND_PATH_MISSING",
                    "compatibility",
                    "Every xforms bind must identify a nodeset.",
                    sheet="survey",
                    column="bind",
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

    # Names in the primary instance are the stable part of the generated
    # structure.  Duplicate sibling names and invalid NCNames are deterministic
    # publication errors, while identical names in separate repeat scopes are
    # intentionally left to the target validator.
    for parent in instances:
        for element in parent.iter():
            child_names = [
                _local_name(child.tag)
                for child in list(element)
                if child.tag is not ET.Comment
            ]
            duplicates = sorted(
                name for name in set(child_names) if child_names.count(name) > 1
            )
            for name in duplicates:
                issues.append(
                    _issue(
                        "XML_DUPLICATE_NODE_NAME",
                        "compatibility",
                        f"Generated XForm has duplicate sibling node name '{name}'.",
                        sheet="survey",
                        column="name",
                    )
                )

    for element in root.iter():
        name = element.get("name")
        if name and not _NCNAME.fullmatch(name):
            issues.append(
                _issue(
                    "XML_NAME_INVALID",
                    "compatibility",
                    f"Generated XForm name '{name}' is not a valid XML name.",
                    sheet="survey",
                    column="name",
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
        if not filename:
            raise ArtifactInputError(
                _issue(
                    "EXTERNAL_FILE_NAME_MISSING",
                    "composition",
                    "An external file has no filename.",
                    sheet="survey",
                )
            )
        if file_obj is None:
            raise ArtifactInputError(
                _issue(
                    "EXTERNAL_FILE_MISSING",
                    "composition",
                    f"External file '{filename}' could not be materialized.",
                    field=filename,
                )
            )

        try:
            close = None
            if isinstance(file_obj, (bytes, bytearray, memoryview)):
                content = bytes(file_obj)
            elif hasattr(file_obj, "open"):
                opened = file_obj.open("rb")
                reader = getattr(file_obj, "read", None) or getattr(
                    opened, "read", None
                )
                if reader is None:
                    raise TypeError("external file has no readable stream")
                close = getattr(file_obj, "close", None)
                try:
                    content = reader()
                finally:
                    if close:
                        close()
            else:
                reader = getattr(file_obj, "read", None)
                if reader is None:
                    raise TypeError("external file has no readable stream")
                content = reader()
                seek = getattr(file_obj, "seek", None)
                if seek:
                    seek(0)
            if isinstance(content, str):
                content = content.encode("utf-8")
            content = bytes(content)
        except FileNotFoundError:
            raise ArtifactInputError(
                _issue(
                    "EXTERNAL_FILE_MISSING",
                    "composition",
                    f"External file '{filename}' could not be found.",
                    field=filename,
                )
            )
        except (OSError, IOError) as exc:
            raise ArtifactInfrastructureError(
                f"Unable to read external file '{filename}': {exc}"
            ) from exc
        except Exception as exc:
            raise ArtifactInfrastructureError(
                f"Unable to materialize external file '{filename}': {exc}"
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


def build_generated_artifact(xlsx_form: Any) -> GeneratedSurveyArtifact:
    """Generate a workbook once and materialize its external files once."""

    try:
        xlsx_bytes = xlsx_form.generate()
        if hasattr(xlsx_bytes, "getvalue"):
            xlsx_bytes = xlsx_bytes.getvalue()
        xlsx_bytes = bytes(xlsx_bytes)
    except Exception as exc:
        raise ArtifactInfrastructureError(f"Unable to generate XLSX: {exc}") from exc

    external_files = materialize_external_files(
        getattr(xlsx_form, "external_files", {})
    )
    return GeneratedSurveyArtifact(
        xlsx_bytes=xlsx_bytes,
        external_files=external_files,
        form_name=str(getattr(xlsx_form, "id_name", "survey") or "survey"),
    )


def validate_generated_artifact(
    artifact: GeneratedSurveyArtifact,
    *,
    converter_cls: Any | None = None,
) -> ValidationResult:
    """Convert and validate one exact artifact without generating it again."""

    if str(PYXFORM_INSTALLED_VERSION) != PYXFORM_VERSION:
        raise ValidatorInfrastructureError(
            f"Expected pyxform {PYXFORM_VERSION}, found {PYXFORM_INSTALLED_VERSION}."
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

    errors = _normalise_messages(getattr(conversion, "errors", []), warning=False)
    warnings = _normalise_messages(getattr(conversion, "warnings", []), warning=True)
    if xml is None and not errors:
        errors.append(
            _issue(
                "PYXFORM_NO_XML",
                "pyxform",
                "pyxform did not produce an XForm for the generated XLSX artifact.",
            )
        )
    if xml is not None and not errors:
        try:
            errors.extend(validate_xml_compatibility(xml, artifact.external_files))
        except Exception as exc:
            raise ValidatorInfrastructureError(
                f"Compatibility validation failed internally: {exc}"
            ) from exc

    validated_artifact = replace(artifact, xml=xml)
    return ValidationResult(
        valid=not errors,
        artifact_hash=validated_artifact.artifact_hash or artifact.artifact_hash,
        errors=errors,
        warnings=warnings,
        artifact=validated_artifact,
    )


def validate_xlsform(
    xlsx_bytes: bytes,
    *,
    filename: str = "survey.xlsx",
    external_files: Mapping[str, bytes] | None = None,
) -> ValidationResult:
    """Validate already-materialized XLSX bytes through the shared contract.

    Endpoint code normally calls :func:`validate_generated_artifact` after the
    generator has materialized external files.  This convenience entry point
    keeps the service usable by workers and unit tests without introducing a
    second conversion path.
    """

    del filename  # Reserved for future source-map diagnostics.
    artifact = GeneratedSurveyArtifact(
        xlsx_bytes=xlsx_bytes,
        external_files=external_files or {},
    )
    return validate_generated_artifact(artifact)


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
    "validate_generated_artifact",
    "validate_xlsform",
    "validate_xml_compatibility",
]
