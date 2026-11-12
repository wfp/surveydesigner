import logging
from datetime import datetime, timezone as datetime_timezone

import django_rq
from django.utils import timezone
from rq import Retry
from rq.job import JobStatus

from .services import reconcile_notification_lifecycle

logger = logging.getLogger(__name__)


def ensure_notification_lifecycle_job():
    # One minute-bucket ID deduplicates bootstrap, admin, and worker requests.
    next_minute = (int(timezone.now().timestamp()) // 60 + 1) * 60
    when = datetime.fromtimestamp(next_minute, tz=datetime_timezone.utc)
    job_id = f"notification-lifecycle-{next_minute}"
    try:
        queue = django_rq.get_queue("generic")
        with queue.connection.lock(
            "notification-lifecycle-schedule-lock", timeout=30, blocking_timeout=5
        ):
            existing = queue.fetch_job(job_id)
            if existing and existing.get_status() in (
                JobStatus.SCHEDULED,
                JobStatus.QUEUED,
                JobStatus.STARTED,
            ):
                return job_id
            queue.enqueue_at(
                when,
                process_notification_lifecycle,
                job_id=job_id,
                retry=Retry(max=3, interval=[15, 60, 300]),
                result_ttl=300,
            )
    except Exception:
        logger.exception("Could not schedule notification lifecycle job %s", job_id)
        raise
    return job_id


@django_rq.job("generic")
def process_notification_lifecycle():
    try:
        return reconcile_notification_lifecycle()
    finally:
        ensure_notification_lifecycle_job()
