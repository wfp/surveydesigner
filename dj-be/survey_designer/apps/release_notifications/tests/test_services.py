from datetime import datetime, timezone as datetime_timezone

import pytest
from release_notifications.models import ReleaseEvent
from release_notifications.services import (
    ReleaseRecordingConflict,
    ReleaseRecordingError,
    record_release,
)

pytestmark = pytest.mark.django_db


def test_record_release_creates_an_active_event():
    deployed_at = datetime(2026, 10, 6, 10, 30, tzinfo=datetime_timezone.utc)

    release, created = record_release(
        version="12.9.3",
        source_id="BUILD-1234",
        deployed_at=deployed_at,
        description="Improved survey validation.\nAdded external file checks.",
    )

    assert created is True
    assert release.deployed_at == deployed_at
    assert release.is_active is True
    release.refresh_from_db()
    assert release.description == (
        "Improved survey validation.\nAdded external file checks."
    )


def test_record_release_is_idempotent_for_matching_identifiers():
    first_release, first_created = record_release(
        version="12.9.3",
        source_id="BUILD-1234",
        description="Original release summary.",
    )
    second_release, second_created = record_release(
        version="12.9.3",
        source_id="BUILD-1234",
        description="A retry must not overwrite the original summary.",
    )

    assert first_created is True
    assert second_created is False
    assert second_release == first_release
    assert ReleaseEvent.objects.count() == 1
    second_release.refresh_from_db()
    assert second_release.description == "Original release summary."


def test_record_release_rejects_reused_source_id():
    record_release(version="12.9.3", source_id="BUILD-1234")

    with pytest.raises(ReleaseRecordingConflict, match="already assigned"):
        record_release(version="12.9.4", source_id="BUILD-1234")


def test_record_release_rejects_reused_version():
    record_release(version="12.9.3", source_id="BUILD-1234")

    with pytest.raises(ReleaseRecordingConflict, match="already assigned"):
        record_release(version="12.9.3", source_id="BUILD-1235")


@pytest.mark.parametrize(
    ("version", "source_id", "message"),
    (
        ("", "BUILD-1234", "version must not be empty"),
        ("12.9.3", "  ", "source_id must not be empty"),
    ),
)
def test_record_release_requires_identifiers(version, source_id, message):
    with pytest.raises(ReleaseRecordingError, match=message):
        record_release(version=version, source_id=source_id)
