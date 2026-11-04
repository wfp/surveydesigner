from datetime import timedelta

import pytest
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from notifications.const import NotificationStatus, ReleaseStatus
from notifications.models import (
    Notification,
    NotificationRead,
    NotificationTranslation,
    Release,
)
from notifications.services import (
    advance_notification_lifecycle,
    currently_published_notifications,
    deactivate_notification,
    publish_notification,
    reconcile_notification_lifecycle,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def scheduler(mocker):
    return mocker.patch(
        "notifications.tasks.ensure_notification_lifecycle_job",
        autospec=True,
        return_value="test-tick",
    )


@pytest.fixture
def notice(user):
    return Notification.objects.create(
        title="Update",
        body="<p>Release notes.</p>",
        created_by=user,
        publish_at=timezone.now() - timedelta(minutes=1),
    )


def test_immediate_publication_preserves_timing_and_does_not_fan_out(
    notice, admin, user
):
    publish_at = notice.publish_at
    updated, changed = publish_notification(notification_id=notice.pk, actor=admin)
    assert changed is True
    assert updated.status == NotificationStatus.PUBLISHED
    assert updated.publish_at == publish_at
    assert updated.created_by == user
    assert updated.updated_by == admin
    assert NotificationRead.objects.count() == 0


def test_scheduling_waits_for_due_time_then_publishes(notice, admin, mocker):
    future = timezone.now() + timedelta(hours=1)
    notice.publish_at = future
    notice.save()
    updated, changed = publish_notification(notification_id=notice.pk, actor=admin)
    assert changed is True
    assert updated.status == NotificationStatus.SCHEDULED
    assert advance_notification_lifecycle(notice.pk) is False
    mocker.patch("notifications.services.timezone.now", return_value=future)
    assert advance_notification_lifecycle(notice.pk) is True
    notice.refresh_from_db()
    assert notice.status == NotificationStatus.PUBLISHED
    assert notice.publish_at == future
    assert advance_notification_lifecycle(notice.pk) is False


def test_republication_does_not_change_timestamps_or_acknowledgements(
    notice, admin, user
):
    publish_notification(notification_id=notice.pk, actor=admin)
    notice.refresh_from_db()
    updated_at = notice.date_updated
    read = NotificationRead.objects.create(
        notification=notice, user=user, read_at=timezone.now(), dismissed=True
    )
    updated, changed = publish_notification(notification_id=notice.pk, actor=admin)
    assert changed is False
    assert updated.date_updated == updated_at
    read.refresh_from_db()
    assert read.state == "dismissed"


def test_deactivation_and_validated_reactivation_preserve_user_state(
    notice, admin, user
):
    publish_notification(notification_id=notice.pk, actor=admin)
    read = NotificationRead.objects.create(
        notification=notice, user=user, read_at=timezone.now()
    )
    deactivated, changed = deactivate_notification(
        notification_id=notice.pk, actor=admin
    )
    assert changed is True
    assert deactivated.status == NotificationStatus.PUBLISHED
    assert deactivated.is_active is False
    assert not currently_published_notifications().filter(pk=notice.pk).exists()
    assert deactivate_notification(notification_id=notice.pk, actor=admin)[1] is False
    assert publish_notification(notification_id=notice.pk, actor=admin)[1] is True
    read.refresh_from_db()
    assert read.state == "read"


@pytest.mark.parametrize("field", ("title", "body"))
@pytest.mark.parametrize("value", ("", "   "))
def test_invalid_content_blocks_publication(notice, admin, field, value):
    Notification.objects.filter(pk=notice.pk).update(**{field: value})
    with pytest.raises(ValidationError):
        publish_notification(notification_id=notice.pk, actor=admin)
    notice.refresh_from_db()
    assert notice.status == NotificationStatus.DRAFT


def test_invalid_translation_blocks_publication(notice, admin):
    NotificationTranslation.objects.create(
        notification=notice, language="unsupported", title="Title", label="Body"
    )
    with pytest.raises(ValidationError, match="Translation"):
        publish_notification(notification_id=notice.pk, actor=admin)


@pytest.mark.parametrize(
    "active,status", ((True, ReleaseStatus.DRAFT), (False, ReleaseStatus.PUBLISHED))
)
def test_linked_release_must_be_active_and_published(notice, admin, active, status):
    notice.release = Release.objects.create(
        business_version="2.0.1",
        title="Release",
        body="Notes",
        is_active=active,
        status=status,
    )
    notice.save()
    with pytest.raises(ValidationError, match="linked release"):
        publish_notification(notification_id=notice.pk, actor=admin)


def test_published_release_notification_can_be_approved(notice, admin):
    notice.release = Release.objects.create(
        business_version="2.0.1",
        title="Release",
        body="Notes",
        status=ReleaseStatus.PUBLISHED,
    )
    notice.save()
    assert (
        publish_notification(notification_id=notice.pk, actor=admin)[0].status
        == NotificationStatus.PUBLISHED
    )


def test_elapsed_expiry_blocks_publication(notice, admin):
    notice.expires_at = timezone.now() - timedelta(seconds=1)
    notice.save()
    with pytest.raises(ValidationError) as raised:
        publish_notification(notification_id=notice.pk, actor=admin)
    assert "expires_at" in raised.value.message_dict


def test_expired_status_is_terminal_even_if_dates_are_changed(notice, admin):
    notice.status = NotificationStatus.EXPIRED
    notice.expires_at = timezone.now() + timedelta(days=1)
    notice.save()
    with pytest.raises(ValidationError, match="cannot be republished"):
        publish_notification(notification_id=notice.pk, actor=admin)


@pytest.mark.parametrize(
    "status", (NotificationStatus.PUBLISHED, NotificationStatus.SCHEDULED)
)
def test_expiry_at_exact_boundary_prevents_late_publication(notice, status, mocker):
    expiry = timezone.now() + timedelta(seconds=1)
    notice.status = status
    notice.expires_at = expiry
    notice.save()
    mocker.patch("notifications.services.timezone.now", return_value=expiry)
    validate = mocker.patch("notifications.services._validate_notification_content")
    assert advance_notification_lifecycle(notice.pk) is True
    notice.refresh_from_db()
    assert notice.status == NotificationStatus.EXPIRED
    validate.assert_not_called()


def test_deactivated_schedule_never_publishes_but_can_expire(notice, admin):
    notice.status = NotificationStatus.SCHEDULED
    notice.expires_at = timezone.now() + timedelta(days=1)
    notice.save()
    deactivate_notification(notification_id=notice.pk, actor=admin)
    assert advance_notification_lifecycle(notice.pk) is False
    Notification.objects.filter(pk=notice.pk).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )
    assert advance_notification_lifecycle(notice.pk) is True
    notice.refresh_from_db()
    assert notice.status == NotificationStatus.EXPIRED
    assert notice.is_active is False


def test_worker_revalidates_scheduled_content(notice):
    Notification.objects.filter(pk=notice.pk).update(
        status=NotificationStatus.SCHEDULED, body=""
    )
    with pytest.raises(ValidationError):
        advance_notification_lifecycle(notice.pk)
    notice.refresh_from_db()
    assert notice.status == NotificationStatus.SCHEDULED


def test_reconciliation_catches_missed_work_and_isolates_invalid_records(
    notice, caplog
):
    notice.status = NotificationStatus.SCHEDULED
    notice.save()
    expired = Notification.objects.create(
        title="Expired",
        body="Notes",
        status=NotificationStatus.PUBLISHED,
        publish_at=timezone.now() - timedelta(days=2),
        expires_at=timezone.now() - timedelta(days=1),
    )
    invalid = Notification.objects.create(
        title="Invalid",
        status=NotificationStatus.SCHEDULED,
        publish_at=timezone.now() - timedelta(minutes=1),
    )
    future = Notification.objects.create(
        title="Future",
        body="Notes",
        status=NotificationStatus.SCHEDULED,
        publish_at=timezone.now() + timedelta(days=1),
    )
    draft = Notification.objects.create(title="Draft", body="Notes")
    assert reconcile_notification_lifecycle() == {"changed": 2, "invalid": 1}
    for item in (notice, expired, invalid, future, draft):
        item.refresh_from_db()
    assert notice.status == NotificationStatus.PUBLISHED
    assert expired.status == NotificationStatus.EXPIRED
    assert invalid.status == NotificationStatus.SCHEDULED
    assert future.status == NotificationStatus.SCHEDULED
    assert draft.status == NotificationStatus.DRAFT
    assert str(invalid.pk) in caplog.text
    assert reconcile_notification_lifecycle() == {"changed": 0, "invalid": 1}


def test_time_filtered_queryset_hides_expired_even_when_worker_is_down(notice):
    notice.status = NotificationStatus.PUBLISHED
    notice.save()
    expired = Notification.objects.create(
        title="Expired",
        body="Notes",
        status=NotificationStatus.PUBLISHED,
        publish_at=timezone.now() - timedelta(days=2),
        expires_at=timezone.now() - timedelta(days=1),
    )
    future = Notification.objects.create(
        title="Future",
        body="Notes",
        status=NotificationStatus.PUBLISHED,
        publish_at=timezone.now() + timedelta(days=1),
    )
    Notification.objects.create(title="Draft", body="Notes")
    Notification.objects.create(
        title="Inactive",
        body="Notes",
        status=NotificationStatus.PUBLISHED,
        is_active=False,
    )
    assert list(currently_published_notifications()) == [notice]
    expired.refresh_from_db()
    assert expired.status == NotificationStatus.PUBLISHED
    assert future not in currently_published_notifications()


@pytest.mark.parametrize("operation", (publish_notification, deactivate_notification))
def test_lifecycle_actions_require_change_permission(notice, user, operation):
    with pytest.raises(PermissionDenied):
        operation(notification_id=notice.pk, actor=user)


def test_editor_can_publish_without_release_management_permissions(notice, user):
    user.user_permissions.add(
        Permission.objects.get(
            codename="change_notification", content_type__app_label="notifications"
        )
    )
    assert publish_notification(notification_id=notice.pk, actor=user)[1] is True


def test_scheduling_is_registered_only_after_commit(
    notice, admin, scheduler, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        publish_notification(notification_id=notice.pk, actor=admin)
        scheduler.assert_not_called()
    scheduler.assert_called_once()


def test_rollback_does_not_register_background_work(
    notice, admin, scheduler, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        with pytest.raises(RuntimeError), transaction.atomic():
            publish_notification(notification_id=notice.pk, actor=admin)
            raise RuntimeError("Rollback")
    scheduler.assert_not_called()
    notice.refresh_from_db()
    assert notice.status == NotificationStatus.DRAFT


def test_redis_failure_is_logged_and_database_intent_remains_recoverable(
    notice, admin, scheduler, django_capture_on_commit_callbacks, caplog
):
    notice.publish_at = timezone.now() + timedelta(hours=1)
    notice.save()
    scheduler.side_effect = RuntimeError("Redis unavailable")
    with django_capture_on_commit_callbacks(execute=True):
        publish_notification(notification_id=notice.pk, actor=admin)
    notice.refresh_from_db()
    assert notice.status == NotificationStatus.SCHEDULED
    assert "Redis unavailable" in caplog.text
