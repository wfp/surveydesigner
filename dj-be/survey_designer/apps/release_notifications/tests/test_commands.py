from datetime import datetime, timezone as datetime_timezone
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from release_notifications.models import ReleaseEvent

pytestmark = pytest.mark.django_db


def test_record_release_command_creates_release():
    stdout = StringIO()

    call_command(
        "record_release",
        release_version="12.9.3",
        source_id="BUILD-1234",
        deployed_at="2026-10-06T10:30:00Z",
        description="Improved survey validation and external choice files.",
        stdout=stdout,
    )

    release = ReleaseEvent.objects.get()
    assert (
        release.description == "Improved survey validation and external choice files."
    )
    assert release.deployed_at == datetime(
        2026, 10, 6, 10, 30, tzinfo=datetime_timezone.utc
    )
    assert "Recorded release '12.9.3'" in stdout.getvalue()


def test_record_release_command_reports_idempotent_retry():
    first_stdout = StringIO()
    retry_stdout = StringIO()

    call_command(
        "record_release",
        release_version="12.9.3",
        source_id="BUILD-1234",
        stdout=first_stdout,
    )
    call_command(
        "record_release",
        release_version="12.9.3",
        source_id="BUILD-1234",
        stdout=retry_stdout,
    )

    assert ReleaseEvent.objects.count() == 1
    assert "already recorded" in retry_stdout.getvalue()


def test_record_release_command_rejects_invalid_deployment_time():
    with pytest.raises(CommandError, match="valid ISO 8601"):
        call_command(
            "record_release",
            release_version="12.9.3",
            source_id="BUILD-1234",
            deployed_at="not-a-date",
        )


def test_record_release_command_reports_identifier_conflict():
    call_command(
        "record_release",
        release_version="12.9.3",
        source_id="BUILD-1234",
        stdout=StringIO(),
    )

    with pytest.raises(CommandError, match="already assigned"):
        call_command(
            "record_release",
            release_version="12.9.4",
            source_id="BUILD-1234",
        )
