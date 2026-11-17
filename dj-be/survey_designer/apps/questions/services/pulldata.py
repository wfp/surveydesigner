"""Match a question's pulldata() calls to the CSV files attached to it.

``pulldata('wfl_0_2_girls', 'minZScore', 'Length', ${height})`` reads
``wfl_0_2_girls.csv``: the first argument is the file name without ``.csv``.
"""

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from django.utils.translation import gettext as _

from .expression_validation import analyse_expression
from .form_validation import ValidationIssue

PULLDATA_FILE_EXTENSION = ".csv"
PULLDATA_FILES_FIELD = "pulldata_files"
# These are the pulldata issues also rendered by the live status panel.  Forms
# mark only these server errors so JavaScript can retire exact duplicates while
# leaving unrelated expression/required errors in the Django error list.
PULLDATA_LIVE_ISSUE_CODES = frozenset(
    (
        "PULLDATA_SOURCE_INVALID",
        "PULLDATA_COLUMN_MISSING",
        "PULLDATA_COLUMNS_UNAVAILABLE",
    )
)

_PULLDATA_CALL = re.compile(r"\bpulldata\s*\(")
# Starts with a letter or "_" so pyxform can use it as the instance id, and
# uses only characters storage keeps unchanged.
_FILE_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]*")
_FILE_NAME_RULE = (
    "File names must start with a letter or '_' and use only letters, digits, "
    "'_', '-' or '.'."
)


def pulldata_filename_error(filename: str) -> str | None:
    """Why an uploaded file name cannot be used by pulldata(), if it cannot."""

    if not filename.endswith(PULLDATA_FILE_EXTENSION):
        return (
            f"'{filename}' is not a .csv file. Pull data files are named after "
            "the pulldata() call, for example wfl_0_2_girls.csv."
        )
    stem = filename[: -len(PULLDATA_FILE_EXTENSION)]
    if not _FILE_NAME.fullmatch(stem):
        return f"'{filename}' cannot be used by pulldata(). {_FILE_NAME_RULE}"
    return None


def _source_error(source: str | None) -> str | None:
    if source is None:
        return (
            "has a pulldata() call whose first argument is not a quoted file "
            "name. Write it as pulldata('file_name', ...)."
        )
    if source.lower().endswith(PULLDATA_FILE_EXTENSION):
        stem = source[: -len(PULLDATA_FILE_EXTENSION)]
        return (
            f"passes '{source}' to pulldata(). Leave out .csv: "
            f"pulldata('{stem}', ...) reads {stem}{PULLDATA_FILE_EXTENSION}."
        )
    if not _FILE_NAME.fullmatch(source):
        return f"passes '{source}' to pulldata(). {_FILE_NAME_RULE}"
    return None


def _issue(code: str, message: str, owner: Mapping[str, Any], field: str):
    return ValidationIssue(
        code=code,
        layer="model",
        severity="error",
        message=message,
        owner=dict(owner),
        field=field,
    )


def _count(number: int, noun: str) -> str:
    return f"{number} {noun}" if number == 1 else f"{number} {noun}s"


@dataclass
class PulldataRequirements:
    """The CSV files that the pulldata() calls in a question need."""

    # Each required file name, with the fields whose calls read it.
    files: dict[str, list[str]] = field(default_factory=dict)
    # Literal return/lookup columns, grouped by required filename.  Dynamic
    # expressions are represented by ``None`` in the parser and are omitted.
    column_references: dict[str, list[tuple[str, str]]] = field(default_factory=dict)
    # (field, explanation) for calls whose first argument can't name a file.
    source_errors: list[tuple[str, str]] = field(default_factory=list)
    # False when a call couldn't be read, so ``files`` may be incomplete.
    # Syntax errors themselves are reported by expression validation.
    complete: bool = True


def pulldata_requirements(values: Mapping[str, str]) -> PulldataRequirements:
    """Find the files read by pulldata() in ``values`` (field name -> text)."""

    requirements = PulldataRequirements()
    for field_name, value in values.items():
        expression = str(value or "").strip()
        if not _PULLDATA_CALL.search(expression):
            continue
        analysis = analyse_expression(expression)
        if not analysis.valid:
            requirements.complete = False
            continue
        for arguments in analysis.pulldata_calls:
            source = arguments[0] if arguments else None
            error = _source_error(source)
            if error:
                requirements.complete = False
                requirements.source_errors.append((field_name, error))
                continue
            filename = f"{source}{PULLDATA_FILE_EXTENSION}"
            fields = requirements.files.setdefault(filename, [])
            if field_name not in fields:
                fields.append(field_name)
            references = requirements.column_references.setdefault(filename, [])
            for argument in arguments[1:3]:
                if argument is not None and (field_name, argument) not in references:
                    references.append((field_name, argument))
    return requirements


def _attached_file_map(attached_files: Iterable[Any]) -> dict[str, Any]:
    """Map filenames to objects while accepting the live-status name API."""

    result = {}
    for attached_file in attached_files:
        if isinstance(attached_file, str):
            result[attached_file] = attached_file
            continue
        filename = getattr(attached_file, "filename", None)
        if filename:
            result[filename] = attached_file
    return result


def _column_problems(
    requirements: PulldataRequirements,
    attached: Mapping[str, Any],
) -> list[tuple[str, str, str, str]]:
    """Return missing literal columns for files whose metadata is available."""

    problems = []
    for filename, references in requirements.column_references.items():
        attached_file = attached.get(filename)
        if attached_file is None or isinstance(attached_file, str):
            continue
        if not hasattr(attached_file, "columns"):
            # The live status helper historically accepted filenames.  A
            # filename alone cannot prove anything about columns, so retain
            # that API's compatibility while model instances expose metadata.
            continue
        columns = getattr(attached_file, "columns", None)
        if not columns:
            seen_fields: set[str] = set()
            for field_name, _column in references:
                if field_name in seen_fields:
                    continue
                seen_fields.add(field_name)
                problems.append(
                    (
                        field_name,
                        "",
                        _(
                            "Column metadata is unavailable for '%(filename)s'. "
                            "Re-upload the file before using literal pulldata columns."
                        )
                        % {"filename": filename},
                        "PULLDATA_COLUMNS_UNAVAILABLE",
                    )
                )
            continue
        for field_name, column in references:
            if column in columns:
                continue
            problems.append(
                (
                    field_name,
                    column,
                    _("Column '%(column)s' does not exist in '%(filename)s'.")
                    % {"column": column, "filename": filename},
                    "PULLDATA_COLUMN_MISSING",
                )
            )
    return problems


def pulldata_file_status(
    values: Mapping[str, str], attached_filenames: Iterable[Any]
) -> dict[str, Any]:
    """Each file's status, for the question form to show while editing."""

    requirements = pulldata_requirements(values)
    attached_by_filename = _attached_file_map(attached_filenames)
    attached = set(attached_by_filename)
    files = [
        {
            "filename": filename,
            "status": "attached" if filename in attached else "missing",
            "fields": fields,
        }
        for filename, fields in requirements.files.items()
    ]
    files += [
        {
            "filename": filename,
            # Only call a file unused once every call has been read.
            "status": "unused" if requirements.complete else "unchecked",
            "fields": [],
        }
        for filename in sorted(attached)
        if filename not in requirements.files
    ]
    problems = [
        f"Field '{field_name}' {error}"
        for field_name, error in requirements.source_errors
    ]
    problems.extend(
        _("Field '%(field)s': %(message)s") % {"field": field_name, "message": message}
        for field_name, _column, message, _code in _column_problems(
            requirements, attached_by_filename
        )
    )
    return {
        "files": files,
        "problems": problems,
        "complete": requirements.complete,
    }


def validate_pulldata_files(
    owner: Mapping[str, Any],
    values: Mapping[str, str],
    attached_files: Iterable[Any],
) -> list[ValidationIssue]:
    """Check that the attached files are exactly the files pulldata() needs.

    ``values`` maps expression field names to their text. ``attached_files``
    are the question's pull data files (anything with a ``filename``).
    """

    label = f"{owner.get('model')} '{owner.get('name')}'"
    requirements = pulldata_requirements(values)
    required = requirements.files
    issues = [
        _issue(
            "PULLDATA_SOURCE_INVALID",
            f"{label} field '{field_name}' {error}",
            owner,
            field_name,
        )
        for field_name, error in requirements.source_errors
    ]
    # File names are unique, so each name is attached at most once.
    attached_files = list(attached_files)
    attached_by_filename = _attached_file_map(attached_files)
    attached = set(attached_by_filename)

    for filename, fields in required.items():
        if filename in attached:
            continue
        stem = filename[: -len(PULLDATA_FILE_EXTENSION)]
        where = ", ".join(f"'{name}'" for name in fields)
        issues.append(
            _issue(
                "PULLDATA_FILE_MISSING",
                f"Missing file: {label} uses pulldata('{stem}', ...) in {where} "
                f"but '{filename}' is not attached. Upload it or select it in "
                "Pull data files.",
                owner,
                PULLDATA_FILES_FIELD,
            )
        )

    # Unknown and mapping checks need every required file.
    if not requirements.complete:
        return issues

    for field_name, column, detail, code in _column_problems(
        requirements, attached_by_filename
    ):
        issues.append(
            _issue(
                code,
                _("%(label)s field '%(field)s': %(detail)s")
                % {"label": label, "field": field_name, "detail": detail},
                owner,
                field_name,
            )
        )

    for filename in sorted(attached):
        if filename in required:
            continue
        stem = filename[: -len(PULLDATA_FILE_EXTENSION)]
        issues.append(
            _issue(
                "PULLDATA_FILE_UNKNOWN",
                f"Unknown file: '{filename}' is attached to {label} but no "
                f"pulldata() call uses '{stem}'. Remove the file or review the "
                "pulldata function.",
                owner,
                PULLDATA_FILES_FIELD,
            )
        )

    if len(attached) != len(required):
        issues.append(
            _issue(
                "PULLDATA_FILE_MAPPING_FAILED",
                f"Mapping failed: {label} needs "
                f"{_count(len(required), 'pull data file')} but "
                f"{len(attached)} {'is' if len(attached) == 1 else 'are'} "
                "attached. Review the files and the pulldata function.",
                owner,
                PULLDATA_FILES_FIELD,
            )
        )
    return issues
