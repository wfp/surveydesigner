from datetime import timezone as datetime_timezone

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from release_notifications.services import ReleaseRecordingError, record_release


class Command(BaseCommand):
    help = "Record a successfully deployed SurveyDesigner release."

    def add_arguments(self, parser):
        parser.add_argument(
            "--description",
            default="",
            help="Plain-text summary of what the release introduced.",
        )
        parser.add_argument(
            "--release-version",
            required=True,
            dest="release_version",
            help="User-facing deployed version.",
        )
        parser.add_argument(
            "--source-id",
            required=True,
            help="Immutable Azure build or release identifier.",
        )
        parser.add_argument(
            "--deployed-at",
            help="Deployment completion time in ISO 8601 format; defaults to now.",
        )

    @staticmethod
    def _deployed_at(value):
        if not value:
            return timezone.now()

        parsed = parse_datetime(value)
        if parsed is None:
            raise CommandError("--deployed-at must be a valid ISO 8601 date and time.")
        if timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed, datetime_timezone.utc)
        return parsed

    def handle(self, *args, **options):
        try:
            release, created = record_release(
                version=options["release_version"],
                source_id=options["source_id"],
                deployed_at=self._deployed_at(options.get("deployed_at")),
                description=options["description"],
            )
        except ReleaseRecordingError as exc:
            raise CommandError(str(exc)) from exc

        if created:
            message = (
                f"Recorded release '{release.version}' from "
                f"source '{release.source_id}'."
            )
        else:
            message = (
                f"Release '{release.version}' from source "
                f"'{release.source_id}' is already recorded."
            )
        self.stdout.write(self.style.SUCCESS(message))
