from datetime import datetime, timezone as datetime_timezone
from io import StringIO

import pytest
from django.core.management import call_command
from notifications.tasks import (
    ensure_notification_lifecycle_job,
    process_notification_lifecycle,
)
from rq.job import JobStatus

pytestmark = pytest.mark.django_db


@pytest.fixture
def queue(mocker):
    queue = mocker.MagicMock()
    queue.fetch_job.return_value = None
    mocker.patch("notifications.tasks.django_rq.get_queue", return_value=queue)
    mocker.patch(
        "notifications.tasks.timezone.now",
        return_value=datetime(2026, 11, 3, 12, 0, 15, tzinfo=datetime_timezone.utc),
    )
    return queue


def test_tick_is_scheduled_at_next_utc_minute_with_retry(queue):
    job_id = ensure_notification_lifecycle_job()
    args, kwargs = queue.enqueue_at.call_args
    assert args[0] == datetime(2026, 11, 3, 12, 1, tzinfo=datetime_timezone.utc)
    assert args[1] == process_notification_lifecycle
    assert kwargs["job_id"] == job_id
    assert kwargs["result_ttl"] == 300
    assert kwargs["retry"].intervals == [15, 60, 300]
    queue.connection.lock.assert_called_once()


@pytest.mark.parametrize(
    "status", (JobStatus.SCHEDULED, JobStatus.QUEUED, JobStatus.STARTED)
)
def test_existing_pending_tick_is_not_duplicated(queue, status):
    queue.fetch_job.return_value = type(
        "ExistingJob", (), {"get_status": lambda self: status}
    )()
    ensure_notification_lifecycle_job()
    queue.enqueue_at.assert_not_called()


def test_scheduler_failure_is_reported(queue, caplog):
    queue.enqueue_at.side_effect = RuntimeError("Redis unavailable")
    with pytest.raises(RuntimeError, match="Redis unavailable"):
        ensure_notification_lifecycle_job()
    assert "Could not schedule notification lifecycle job" in caplog.text


def test_tick_reconciles_and_registers_its_successor(mocker):
    reconcile = mocker.patch(
        "notifications.tasks.reconcile_notification_lifecycle",
        return_value={"changed": 2, "invalid": 0},
    )
    schedule = mocker.patch("notifications.tasks.ensure_notification_lifecycle_job")
    assert process_notification_lifecycle() == {"changed": 2, "invalid": 0}
    reconcile.assert_called_once()
    schedule.assert_called_once()


def test_tick_still_registers_successor_when_processing_fails(mocker):
    mocker.patch(
        "notifications.tasks.reconcile_notification_lifecycle",
        side_effect=RuntimeError("Database unavailable"),
    )
    schedule = mocker.patch("notifications.tasks.ensure_notification_lifecycle_job")
    with pytest.raises(RuntimeError, match="Database unavailable"):
        process_notification_lifecycle()
    schedule.assert_called_once()


def test_reconcile_command_processes_work_and_bootstraps_jobs(mocker):
    mocker.patch(
        "notifications.management.commands.reconcile_notifications.reconcile_notification_lifecycle",
        return_value={"changed": 2, "invalid": 1},
    )
    schedule = mocker.patch(
        "notifications.management.commands.reconcile_notifications.ensure_notification_lifecycle_job",
        return_value="test-job",
    )
    output = StringIO()
    call_command("reconcile_notifications", stdout=output)
    assert "2 changed, 1 invalid" in output.getvalue()
    assert "test-job" in output.getvalue()
    schedule.assert_called_once()
