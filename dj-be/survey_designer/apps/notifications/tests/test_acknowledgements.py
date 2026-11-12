from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import close_old_connections, connection, connections
from django.utils import timezone
from notifications.const import NotificationStatus, ReleaseStatus
from notifications.models import Notification, NotificationRead, Release
from notifications.selectors import notifications_for_user, releases_for_user
from notifications.services import acknowledge_notification

pytestmark = pytest.mark.django_db


@pytest.fixture
def audience(user):
    group = Group.objects.create(name="Notification readers")
    user.groups.add(group)
    return group


@pytest.fixture
def notice(audience):
    notification = Notification.objects.create(
        title="Update",
        body="Release notes",
        status=NotificationStatus.PUBLISHED,
        publish_at=timezone.now() - timedelta(hours=1),
    )
    notification.audience.add(audience)
    return notification


def test_read_creates_own_marker_and_retains_feed_entry(notice, user):
    state, changed = acknowledge_notification(
        notification_id=notice.pk, actor=user, action="read"
    )
    assert changed is True
    assert state.user_id == user.pk
    assert state.notification_id == notice.pk
    assert state.state == "read"
    assert state.read_at is not None
    assert notifications_for_user(user).get(pk=notice.pk).is_read is True
    assert NotificationRead.objects.count() == 1


def test_dismiss_marks_read_and_hides_only_the_requesting_accounts_entry(
    notice, user, admin, audience
):
    admin.groups.add(audience)
    state, changed = acknowledge_notification(
        notification_id=notice.pk, actor=user, action="dismiss"
    )
    assert changed is True
    assert state.state == "dismissed"
    assert state.read_at is not None
    assert not notifications_for_user(user).exists()
    assert notifications_for_user(admin).get(pk=notice.pk).is_read is False
    assert not NotificationRead.objects.filter(user=admin).exists()


@pytest.mark.parametrize("action", ("read", "dismiss"))
def test_retries_preserve_identity_and_original_timestamp(notice, user, action, mocker):
    first = timezone.now()
    clock = mocker.patch("notifications.services.timezone.now", return_value=first)
    state, _ = acknowledge_notification(
        notification_id=notice.pk, actor=user, action=action
    )
    created_at = state.date_created
    clock.return_value = first + timedelta(hours=1)
    retried, changed = acknowledge_notification(
        notification_id=notice.pk, actor=user, action=action
    )
    assert changed is False
    assert retried.pk == state.pk
    assert retried.read_at == first
    assert retried.date_created == created_at
    assert NotificationRead.objects.count() == 1


def test_read_then_dismiss_retains_first_read_time(notice, user, mocker):
    state, _ = acknowledge_notification(
        notification_id=notice.pk, actor=user, action="read"
    )
    first = state.read_at
    mocker.patch(
        "notifications.services.timezone.now", return_value=first + timedelta(minutes=1)
    )
    state, changed = acknowledge_notification(
        notification_id=notice.pk, actor=user, action="dismiss"
    )
    assert changed is True
    assert state.read_at == first
    assert state.state == "dismissed"


def test_late_read_never_undoes_dismissal(notice, user):
    state, _ = acknowledge_notification(
        notification_id=notice.pk, actor=user, action="dismiss"
    )
    late, changed = acknowledge_notification(
        notification_id=notice.pk, actor=user, action="read"
    )
    assert changed is False
    assert late.pk == state.pk
    assert late.state == "dismissed"
    assert not notifications_for_user(user).exists()


@pytest.mark.parametrize("action", ("read", "dismiss"))
def test_existing_unread_marker_is_updated_in_place(notice, user, action):
    old = NotificationRead.objects.create(notification=notice, user=user)
    state, changed = acknowledge_notification(
        notification_id=notice.pk, actor=user, action=action
    )
    assert changed is True
    assert state.pk == old.pk
    assert state.read_at is not None
    assert state.dismissed is (action == "dismiss")


def test_old_id_never_consumes_a_newer_notification(notice, user, audience):
    newer = Notification.objects.create(
        title="Newer release", body="Newer notes", status=NotificationStatus.PUBLISHED
    )
    newer.audience.add(audience)
    acknowledge_notification(notification_id=notice.pk, actor=user, action="dismiss")
    assert notifications_for_user(user).get(pk=newer.pk).is_read is False
    assert not NotificationRead.objects.filter(notification=newer).exists()


def test_accounts_keep_independent_markers(notice, user, admin, audience):
    admin.groups.add(audience)
    other, _ = acknowledge_notification(
        notification_id=notice.pk, actor=admin, action="read"
    )
    own, _ = acknowledge_notification(
        notification_id=notice.pk, actor=user, action="dismiss"
    )
    other.refresh_from_db()
    assert own.pk != other.pk
    assert other.state == "read"
    assert NotificationRead.objects.count() == 2


def test_another_session_of_the_same_account_uses_the_existing_marker(notice, user):
    first, _ = acknowledge_notification(
        notification_id=notice.pk, actor=user, action="read"
    )
    fresh_actor = get_user_model().objects.get(pk=user.pk)
    second, changed = acknowledge_notification(
        notification_id=notice.pk, actor=fresh_actor, action="dismiss"
    )
    assert changed is True
    assert first.pk == second.pk
    assert first.read_at == second.read_at
    assert NotificationRead.objects.count() == 1


@pytest.mark.parametrize("actor", (None, AnonymousUser()))
def test_unauthenticated_requests_are_rejected(notice, actor):
    with pytest.raises(PermissionDenied):
        acknowledge_notification(notification_id=notice.pk, actor=actor, action="read")
    assert NotificationRead.objects.count() == 0


def test_inactive_account_is_rejected_without_writing_state(notice, user):
    user.is_active = False
    with pytest.raises(PermissionDenied):
        acknowledge_notification(notification_id=notice.pk, actor=user, action="read")
    assert NotificationRead.objects.count() == 0


@pytest.mark.parametrize("action", ("clear", "unread", "READ", "", None))
def test_unsupported_action_is_rejected_without_writing_state(notice, user, action):
    with pytest.raises(ValidationError) as raised:
        acknowledge_notification(notification_id=notice.pk, actor=user, action=action)
    assert "action" in raised.value.message_dict
    assert NotificationRead.objects.count() == 0


@pytest.mark.parametrize("mode", ("removed", "unrelated", "superuser"))
def test_audience_cannot_be_bypassed(notice, user, admin, mode):
    actor = user
    if mode == "removed":
        user.groups.clear()
    elif mode == "unrelated":
        user.groups.clear()
        user.groups.add(Group.objects.create(name="Other audience"))
    else:
        actor = admin
    with pytest.raises(Notification.DoesNotExist):
        acknowledge_notification(notification_id=notice.pk, actor=actor, action="read")
    assert NotificationRead.objects.count() == 0


@pytest.mark.parametrize(
    "mode", ("draft", "scheduled", "expired", "inactive", "future", "elapsed")
)
def test_lifecycle_restrictions_apply_to_acknowledgements(notice, user, mode):
    values = {"status": mode}
    if mode == "inactive":
        values = {"is_active": False}
    elif mode == "future":
        values = {"publish_at": timezone.now() + timedelta(days=1)}
    elif mode == "elapsed":
        values = {"expires_at": timezone.now() - timedelta(seconds=1)}
    Notification.objects.filter(pk=notice.pk).update(**values)
    with pytest.raises(Notification.DoesNotExist):
        acknowledge_notification(
            notification_id=notice.pk, actor=user, action="dismiss"
        )
    assert NotificationRead.objects.count() == 0


def test_missing_and_unavailable_ids_use_same_error(notice, user):
    for notification_id in (notice.pk + 1000, notice.pk):
        user.groups.clear()
        with pytest.raises(Notification.DoesNotExist):
            acknowledge_notification(
                notification_id=notification_id, actor=user, action="read"
            )
    assert NotificationRead.objects.count() == 0


def test_broadcast_can_be_read_and_dismissed_by_user_without_groups(notice, user):
    notice.audience.clear()
    user.groups.clear()
    state, _ = acknowledge_notification(
        notification_id=notice.pk, actor=user, action="read"
    )
    assert state.state == "read"
    state, _ = acknowledge_notification(
        notification_id=notice.pk, actor=user, action="dismiss"
    )
    assert state.state == "dismissed"


def test_dismiss_retries_still_require_current_access(notice, user):
    state, _ = acknowledge_notification(
        notification_id=notice.pk, actor=user, action="dismiss"
    )
    user.groups.clear()
    with pytest.raises(Notification.DoesNotExist):
        acknowledge_notification(
            notification_id=notice.pk, actor=user, action="dismiss"
        )
    state.refresh_from_db()
    assert state.state == "dismissed"


def test_dismiss_does_not_remove_release_catalogue_access(notice, user):
    release = Release.objects.create(
        business_version="2.0.1",
        title="Release",
        body="Notes",
        status=ReleaseStatus.PUBLISHED,
        published_at=timezone.now() - timedelta(minutes=1),
    )
    notice.release = release
    notice.save()
    acknowledge_notification(notification_id=notice.pk, actor=user, action="dismiss")
    assert releases_for_user(user).get() == release


@pytest.mark.parametrize(
    "status,active", ((ReleaseStatus.DRAFT, True), (ReleaseStatus.PUBLISHED, False))
)
def test_unavailable_linked_release_blocks_acknowledgement(
    notice, user, status, active
):
    notice.release = Release.objects.create(
        business_version="2.0.1",
        title="Release",
        body="Notes",
        status=status,
        is_active=active,
        published_at=timezone.now() - timedelta(minutes=1),
    )
    notice.save()
    with pytest.raises(Notification.DoesNotExist):
        acknowledge_notification(notification_id=notice.pk, actor=user, action="read")
    assert NotificationRead.objects.count() == 0


def test_failed_new_marker_creation_rolls_back(notice, user, mocker):
    mocker.patch.object(
        NotificationRead, "save", side_effect=RuntimeError("Write failed")
    )
    with pytest.raises(RuntimeError, match="Write failed"):
        acknowledge_notification(notification_id=notice.pk, actor=user, action="read")
    assert NotificationRead.objects.count() == 0


def test_failed_existing_marker_update_preserves_state(notice, user, mocker):
    state = NotificationRead.objects.create(notification=notice, user=user)
    mocker.patch.object(
        NotificationRead, "save", side_effect=RuntimeError("Write failed")
    )
    with pytest.raises(RuntimeError):
        acknowledge_notification(
            notification_id=notice.pk, actor=user, action="dismiss"
        )
    state.refresh_from_db()
    assert state.state == "unread"


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    "actions",
    (
        ("read", "read"),
        ("read", "dismiss"),
        ("dismiss", "read"),
        ("dismiss", "dismiss"),
    ),
)
def test_concurrent_acknowledgements_have_one_marker_and_never_undo_dismissal(
    notice, user, actions
):
    if not connection.features.has_select_for_update:
        pytest.skip("Requires a database supporting row locks.")
    actor_id = user.pk
    barrier = Barrier(2)

    def acknowledge(action):
        close_old_connections()
        try:
            actor = get_user_model().objects.get(pk=actor_id)
            barrier.wait(timeout=10)
            state, changed = acknowledge_notification(
                notification_id=notice.pk, actor=actor, action=action
            )
            return state.pk, changed
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(acknowledge, actions))
    assert results[0][0] == results[1][0]
    state = NotificationRead.objects.get(notification=notice, user=user)
    assert state.read_at is not None
    assert state.dismissed is ("dismiss" in actions)
    assert NotificationRead.objects.count() == 1
