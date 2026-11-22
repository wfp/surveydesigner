from datetime import datetime, timezone as datetime_timezone

from django.db import IntegrityError, transaction
from django.utils import timezone
from release_notifications.models import ReleaseEvent, UserReleaseState


class ReleaseRecordingError(ValueError):
    pass


class ReleaseRecordingConflict(ReleaseRecordingError):
    pass


def _normalize_identifier(value, field_name):
    normalized = str(value or "").strip()
    if not normalized:
        raise ReleaseRecordingError(f"{field_name} must not be empty.")
    return normalized


def _normalize_deployed_at(value):
    if value is None:
        return timezone.now()
    if not isinstance(value, datetime):
        raise ReleaseRecordingError("deployed_at must be a datetime.")
    if timezone.is_naive(value):
        return timezone.make_aware(value, datetime_timezone.utc)
    return value


def _find_existing_release(version, source_id):
    source_match = ReleaseEvent.objects.filter(source_id=source_id).first()
    version_match = ReleaseEvent.objects.filter(version=version).first()

    if source_match and source_match.version != version:
        raise ReleaseRecordingConflict(
            f"Source ID '{source_id}' is already assigned to release "
            f"'{source_match.version}'."
        )
    if version_match and version_match.source_id != source_id:
        raise ReleaseRecordingConflict(
            f"Release '{version}' is already assigned to source ID "
            f"'{version_match.source_id}'."
        )
    return source_match or version_match


def record_release(*, version, source_id, deployed_at=None, description=""):
    """Create one immutable release event, or return the matching existing event."""

    version = _normalize_identifier(version, "version")
    source_id = _normalize_identifier(source_id, "source_id")
    deployed_at = _normalize_deployed_at(deployed_at)

    existing = _find_existing_release(version, source_id)
    if existing:
        return existing, False

    try:
        with transaction.atomic():
            release = ReleaseEvent.objects.create(
                version=version,
                source_id=source_id,
                deployed_at=deployed_at,
                description=description,
            )
    except IntegrityError:
        # Another deployment process may have recorded this event concurrently.
        existing = _find_existing_release(version, source_id)
        if existing:
            return existing, False
        raise

    return release, True


@transaction.atomic
def update_release_state(*, user, release_event, action):
    """Serialize read/clear updates and preserve the first action timestamp."""
    if action not in ("read", "clear"):
        raise ValueError("Unsupported release notification action.")
    state, _ = UserReleaseState.objects.get_or_create(
        user=user, release_event=release_event
    )
    state = UserReleaseState.objects.select_for_update().get(pk=state.pk)
    field = "read_at" if action == "read" else "cleared_at"
    if getattr(state, field) is None:
        setattr(state, field, timezone.now())
        state.save(update_fields=(field, "date_updated"))
    return state
