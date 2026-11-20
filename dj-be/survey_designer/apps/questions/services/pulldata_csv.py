"""Small, storage-independent helpers for pull-data CSV headers."""

from __future__ import annotations

import codecs
import csv
import hashlib
from typing import BinaryIO

from django.utils.translation import gettext as _

# Header names are metadata only.  Keep the read bounded so validating an
# upload never scans its data rows (or downloads a whole remote object).
PULLDATA_HEADER_MAX_BYTES = 64 * 1024


class PulldataHeaderError(ValueError):
    """The uploaded file does not have a usable UTF-8 CSV header."""


def sha256_upload(uploaded) -> str:
    """Return the SHA-256 digest of an upload's exact bytes.

    CSV parsing and normalisation must not make two different uploads look
    like the same asset. Restore the original position so the upload can be
    validated and saved after the digest is calculated.
    """

    try:
        original_position = uploaded.tell()
    except (AttributeError, OSError, ValueError):
        original_position = 0

    digest = hashlib.sha256()
    try:
        uploaded.seek(0)
        while True:
            chunk = uploaded.read(1024 * 1024)
            if not chunk:
                break
            if isinstance(chunk, str):
                raise TypeError("CSV upload must be binary")
            digest.update(chunk)
    finally:
        try:
            uploaded.seek(original_position)
        except (AttributeError, OSError, ValueError):
            pass
    return digest.hexdigest()


class _BoundedTextLines:
    """Incrementally decode physical lines without reading beyond a bound."""

    def __init__(self, uploaded: BinaryIO):
        self.uploaded = uploaded
        self.decoder = codecs.getincrementaldecoder("utf-8-sig")()
        self.buffer = b""
        self.total_bytes = 0

    def __iter__(self):
        return self

    def __next__(self) -> str:
        while True:
            newline = self.buffer.find(b"\n")
            carriage = self.buffer.find(b"\r")
            if carriage >= 0 and (newline < 0 or carriage < newline):
                # Wait for one more decoded character when CR is the final
                # buffered character so CRLF remains one physical line.
                if carriage + 1 < len(self.buffer):
                    end = carriage + 1 + (self.buffer[carriage + 1] == 10)
                    line, self.buffer = self.buffer[:end], self.buffer[end:]
                    return self.decoder.decode(line, final=False)
            elif newline >= 0:
                line, self.buffer = (
                    self.buffer[: newline + 1],
                    self.buffer[newline + 1 :],
                )
                return self.decoder.decode(line, final=False)
            chunk = self.uploaded.read(4096)
            if not chunk:
                try:
                    line = self.decoder.decode(self.buffer, final=True)
                except UnicodeDecodeError:
                    raise
                self.buffer = b""
                if line:
                    return line
                raise StopIteration
            self.total_bytes += len(chunk)
            if self.total_bytes > PULLDATA_HEADER_MAX_BYTES:
                raise PulldataHeaderError("CSV header is too large or incomplete.")
            if isinstance(chunk, str):
                raise TypeError("CSV upload must be binary")
            self.buffer += chunk


def _filename(uploaded, filename: str | None) -> str:
    return filename or getattr(uploaded, "name", "uploaded file") or "uploaded file"


def read_pulldata_headers(
    uploaded: BinaryIO, *, filename: str | None = None
) -> list[str]:
    """Read and validate only the first CSV record from an upload.

    The upload is rewound for reading and restored to its original position,
    including when decoding or CSV validation fails.  Header names are not
    normalised: case, whitespace inside a name, and quoted values are kept as
    supplied.  Empty/blank and exact duplicate names are rejected.
    """

    name = _filename(uploaded, filename)
    try:
        original_position = uploaded.tell()
    except (AttributeError, OSError):
        original_position = 0

    try:
        uploaded.seek(0)
        lines = _BoundedTextLines(uploaded)
        try:
            headers = next(csv.reader(lines, strict=True))
        except StopIteration as exc:
            raise PulldataHeaderError(
                _("CSV file '%(filename)s' is empty or has no header row.")
                % {"filename": name}
            ) from exc
        except PulldataHeaderError as exc:
            raise PulldataHeaderError(
                _("CSV header in '%(filename)s' is too large or incomplete.")
                % {"filename": name}
            ) from exc
        except UnicodeDecodeError as exc:
            raise PulldataHeaderError(
                _("CSV file '%(filename)s' is not valid UTF-8.") % {"filename": name}
            ) from exc
        except csv.Error as exc:
            raise PulldataHeaderError(
                _("CSV file '%(filename)s' has an invalid header row.")
                % {"filename": name}
            ) from exc
    except (AttributeError, OSError, ValueError) as exc:
        if isinstance(exc, PulldataHeaderError):
            raise
        raise PulldataHeaderError(
            _("Could not read the header from CSV file '%(filename)s'.")
            % {"filename": name}
        ) from exc
    finally:
        try:
            uploaded.seek(original_position)
        except (AttributeError, OSError, ValueError):
            pass

    if not headers:
        raise PulldataHeaderError(
            _("CSV file '%(filename)s' has no header row.") % {"filename": name}
        )
    for header in headers:
        if not header or not header.strip():
            raise PulldataHeaderError(
                _("CSV file '%(filename)s' has an empty or blank header name.")
                % {"filename": name}
            )
    seen: set[str] = set()
    for header in headers:
        if header in seen:
            raise PulldataHeaderError(
                _("CSV file '%(filename)s' has duplicate header '%(header)s'.")
                % {"filename": name, "header": header}
            )
        seen.add(header)
    return headers
