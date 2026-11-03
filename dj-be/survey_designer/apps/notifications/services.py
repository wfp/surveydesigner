import logging

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .const import NotificationStatus, ReleaseStatus
from .models import Notification, NotificationTranslation, Release

logger = logging.getLogger(__name__)


def validation_error_message(error):
    if hasattr(error, "message_dict"):
        return "; ".join(
            f"{field}: {'; '.join(errors)}"
            for field, errors in error.message_dict.items()
        )
    return "; ".join(error.messages)


def _validate_translations(translations):
    for translation in translations:
        try:
            translation.full_clean()
            if not translation.title.strip() or not translation.label.strip():
                raise ValidationError(
                    "The translated title and body must not be blank."
                )
        except ValidationError as exc:
            raise ValidationError(
                f"Translation '{translation.language}': {validation_error_message(exc)}"
            ) from exc


def can_publish_release(actor):
    return bool(
        actor
        and actor.is_authenticated
        and actor.is_active
        and actor.has_perms(
            (
                "notifications.change_release",
                "notifications.add_notification",
                "notifications.add_notificationtranslation",
            )
        )
    )


@transaction.atomic
def publish_release(*, release_id, actor):
    """Publish once and snapshot saved content into a linked draft notification."""
    if not can_publish_release(actor):
        raise PermissionDenied(
            "Publishing requires permission to change releases and create "
            "notifications and their translations."
        )

    # Serialize concurrent publication attempts and read the authoritative record.
    release = Release.objects.select_for_update().get(pk=release_id)
    existing = Notification.objects.select_for_update().filter(release=release).first()
    if release.status == ReleaseStatus.PUBLISHED:
        if existing is None or release.published_at is None:
            raise ValidationError(
                "This release is already marked published but has no complete "
                "publication record. Review its publication date and linked notification."
            )
        return existing, False

    if not release.is_active:
        raise ValidationError("Inactive releases cannot be published.")
    if existing is not None:
        raise ValidationError(
            "This draft release already has a linked notification. Review it and "
            "remove its release link before publishing; existing content will not be overwritten."
        )

    release.full_clean()
    for field in ("business_version", "title", "body"):
        if not getattr(release, field).strip():
            raise ValidationError({field: "This field is required before publication."})

    translations = list(release.translations.select_for_update().order_by("pk"))
    _validate_translations(translations)

    published_at = timezone.now()
    notification = Notification(
        release=release,
        title=release.title,
        body=release.body,
        status=NotificationStatus.DRAFT,
        publish_at=published_at,
        created_by=actor,
        updated_by=actor,
    )
    # Release has no abstract; summaries remain empty for later editorial work.
    notification.full_clean()
    notification.save()
    for translation in translations:
        snapshot = NotificationTranslation(
            notification=notification,
            language=translation.language,
            title=translation.title,
            label=translation.label,
            created_by=actor,
            updated_by=actor,
        )
        snapshot.full_clean()
        snapshot.save()

    release.status = ReleaseStatus.PUBLISHED
    release.published_at = published_at
    release.updated_by = actor
    release.save(update_fields=("status", "published_at", "updated_by", "date_updated"))
    return notification, True


def can_publish_notification(actor):
    return bool(
        actor
        and actor.is_authenticated
        and actor.is_active
        and actor.has_perm("notifications.change_notification")
    )


def _validate_notification_content(notification):
    notification.full_clean()
    for field in ("title", "body"):
        if not getattr(notification, field).strip():
            raise ValidationError({field: "This field is required before publication."})
    if notification.release_id and (
        not notification.release.is_active
        or notification.release.status != ReleaseStatus.PUBLISHED
    ):
        raise ValidationError("The linked release must be active and published.")
    _validate_translations(notification.translations.select_for_update().order_by("pk"))


def _ensure_lifecycle_processing():
    from .tasks import ensure_notification_lifecycle_job

    # Database state is authoritative; Redis failure is logged and reconciled later.
    transaction.on_commit(ensure_notification_lifecycle_job, robust=True)


@transaction.atomic
def publish_notification(*, notification_id, actor):
    """Approve immediate or scheduled publication without resetting user state."""
    if not can_publish_notification(actor):
        raise PermissionDenied(
            "Publishing requires permission to change notifications."
        )
    notification = Notification.objects.select_for_update().get(pk=notification_id)
    now = timezone.now()
    if notification.status == NotificationStatus.EXPIRED:
        raise ValidationError(
            "Expired notifications cannot be republished. Create a new notification."
        )
    if notification.expires_at is not None and notification.expires_at <= now:
        raise ValidationError({"expires_at": "The expiry time has already passed."})
    _validate_notification_content(notification)
    status = (
        NotificationStatus.SCHEDULED
        if notification.publish_at > now
        else NotificationStatus.PUBLISHED
    )
    changed = notification.status != status or not notification.is_active
    if changed:
        notification.status = status
        notification.is_active = True
        notification.updated_by = actor
        notification.save(
            update_fields=("status", "is_active", "updated_by", "date_updated")
        )
    _ensure_lifecycle_processing()
    return notification, changed


@transaction.atomic
def deactivate_notification(*, notification_id, actor):
    if not can_publish_notification(actor):
        raise PermissionDenied(
            "Deactivation requires permission to change notifications."
        )
    notification = Notification.objects.select_for_update().get(pk=notification_id)
    changed = notification.is_active
    if changed:
        notification.is_active = False
        notification.updated_by = actor
        notification.save(update_fields=("is_active", "updated_by", "date_updated"))
    _ensure_lifecycle_processing()
    return notification, changed


@transaction.atomic
def advance_notification_lifecycle(notification_id):
    notification = Notification.objects.select_for_update().get(pk=notification_id)
    now = timezone.now()
    status = notification.status
    if status not in (NotificationStatus.SCHEDULED, NotificationStatus.PUBLISHED):
        return False
    if notification.expires_at is not None and notification.expires_at <= now:
        notification.status = NotificationStatus.EXPIRED
    elif (
        notification.is_active
        and status == NotificationStatus.SCHEDULED
        and notification.publish_at <= now
    ):
        _validate_notification_content(notification)
        notification.status = NotificationStatus.PUBLISHED
    else:
        return False
    notification.save(update_fields=("status", "date_updated"))
    return True


def reconcile_notification_lifecycle():
    now = timezone.now()
    due = Notification.objects.filter(
        Q(status=NotificationStatus.SCHEDULED, is_active=True, publish_at__lte=now)
        | Q(
            status__in=(NotificationStatus.SCHEDULED, NotificationStatus.PUBLISHED),
            expires_at__lte=now,
        )
    ).order_by("pk")
    changed = 0
    invalid = 0
    for notification_id in due.values_list("pk", flat=True).iterator():
        try:
            changed += int(advance_notification_lifecycle(notification_id))
        except Notification.DoesNotExist:
            continue
        except ValidationError as exc:
            invalid += 1
            logger.warning(
                "Notification %s lifecycle validation failed: %s",
                notification_id,
                validation_error_message(exc),
            )
    return {"changed": changed, "invalid": invalid}


def currently_published_notifications():
    """Lifecycle eligibility only; callers must still enforce audience/user rules."""
    now = timezone.now()
    return Notification.objects.filter(
        is_active=True,
        status=NotificationStatus.PUBLISHED,
        publish_at__lte=now,
    ).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=now),
        Q(release__isnull=True)
        | Q(release__is_active=True, release__status=ReleaseStatus.PUBLISHED),
    )
