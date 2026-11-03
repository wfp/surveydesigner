from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from .const import NotificationStatus, ReleaseStatus
from .models import Notification, NotificationTranslation, Release


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
    for translation in translations:
        try:
            translation.full_clean()
            if not translation.title.strip() or not translation.label.strip():
                raise ValidationError(
                    "The translated title and body must not be blank."
                )
        except ValidationError as exc:
            details = (
                "; ".join(
                    f"{field}: {'; '.join(errors)}"
                    for field, errors in exc.message_dict.items()
                )
                if hasattr(exc, "message_dict")
                else "; ".join(exc.messages)
            )
            raise ValidationError(
                f"Translation '{translation.language}': {details}"
            ) from exc

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
