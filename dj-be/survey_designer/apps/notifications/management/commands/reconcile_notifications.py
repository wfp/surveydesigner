from django.core.management.base import BaseCommand
from notifications.services import reconcile_notification_lifecycle
from notifications.tasks import ensure_notification_lifecycle_job


class Command(BaseCommand):
    help = (
        "Process due notification transitions and ensure the recurring RQ job exists."
    )

    def handle(self, *args, **options):
        result = reconcile_notification_lifecycle()
        job_id = ensure_notification_lifecycle_job()
        self.stdout.write(
            f"Notifications: {result['changed']} changed, {result['invalid']} invalid. "
            f"Lifecycle job: {job_id}."
        )
