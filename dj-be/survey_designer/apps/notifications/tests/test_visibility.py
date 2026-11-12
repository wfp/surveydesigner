from datetime import timedelta

import pytest
from django.contrib.auth.models import AnonymousUser, Group
from django.utils import timezone
from notifications.const import NotificationStatus, ReleaseStatus
from notifications.models import Notification, NotificationRead, Release
from notifications.selectors import notifications_for_user, releases_for_user

pytestmark = pytest.mark.django_db


@pytest.fixture
def audience(user):
    group = Group.objects.create(name="Survey designers")
    user.groups.add(group)
    return group


@pytest.fixture
def notice(audience):
    notice = Notification.objects.create(
        title="Release update",
        body="English notes",
        status=NotificationStatus.PUBLISHED,
        publish_at=timezone.now() - timedelta(minutes=1),
    )
    notice.audience.add(audience)
    return notice


def published_release(version="2.0.1", **values):
    return Release.objects.create(
        business_version=version,
        title="Release",
        body="Release notes",
        status=ReleaseStatus.PUBLISHED,
        published_at=timezone.now() - timedelta(minutes=1),
        **values,
    )


def test_matching_group_sees_notification_without_read_side_effects(user, notice):
    visible = notifications_for_user(user).get(pk=notice.pk)
    assert visible.is_read is False
    assert NotificationRead.objects.count() == 0


def test_empty_audience_is_a_broadcast_to_authenticated_users_without_groups(
    user, notice
):
    notice.audience.clear()
    user.groups.clear()
    assert notifications_for_user(user).get() == notice
    assert NotificationRead.objects.count() == 0


def test_broadcast_still_excludes_anonymous_and_inactive_users(user, notice):
    notice.audience.clear()
    assert not notifications_for_user(AnonymousUser()).exists()
    user.is_active = False
    assert not notifications_for_user(user).exists()


def test_no_groups_and_unmatched_groups_are_denied(user, notice):
    user.groups.clear()
    user.groups.add(Group.objects.create(name="Unrelated group"))
    assert not notifications_for_user(user).exists()
    user.groups.clear()
    assert not notifications_for_user(user).exists()


def test_matching_any_group_is_sufficient_and_does_not_duplicate_rows(user, notice):
    second = Group.objects.create(name="Codebook editors")
    third = Group.objects.create(name="Other role")
    notice.audience.add(second, third)
    assert notifications_for_user(user).count() == 1
    user.groups.add(second)
    assert list(notifications_for_user(user)) == [notice]


@pytest.mark.parametrize("actor", (None, AnonymousUser()))
def test_anonymous_users_cannot_see_notifications_or_releases(actor, notice):
    assert not notifications_for_user(actor).exists()
    assert not releases_for_user(actor).exists()


def test_inactive_users_cannot_see_content(user, notice):
    user.is_active = False
    assert not notifications_for_user(user).exists()
    assert not releases_for_user(user).exists()


def test_superuser_does_not_bypass_audiences(admin, notice, audience):
    assert not notifications_for_user(admin).exists()
    admin.groups.add(audience)
    assert notifications_for_user(admin).get() == notice


def test_current_group_membership_is_used_without_user_permission_cache(
    user, notice, audience
):
    assert notifications_for_user(user).exists()
    user.groups.remove(audience)
    assert not notifications_for_user(user).exists()
    user.groups.add(audience)
    assert notifications_for_user(user).exists()


def test_read_retains_but_dismissed_hides_for_that_account_only(
    user, notice, admin, audience
):
    admin.groups.add(audience)
    state = NotificationRead.objects.create(
        notification=notice, user=user, read_at=timezone.now()
    )
    assert notifications_for_user(user).get().is_read is True
    assert notifications_for_user(admin).get().is_read is False
    state.dismissed = True
    state.save()
    assert not notifications_for_user(user).exists()
    assert notifications_for_user(admin).get() == notice


@pytest.mark.parametrize(
    "values",
    (
        {"status": NotificationStatus.DRAFT},
        {"status": NotificationStatus.SCHEDULED},
        {"status": NotificationStatus.EXPIRED},
        {"is_active": False},
        {"publish_at": timezone.now() + timedelta(days=1)},
        {"expires_at": timezone.now() - timedelta(seconds=1)},
    ),
)
def test_feed_enforces_lifecycle_even_without_worker_updates(user, notice, values):
    if "expires_at" in values:
        values = {**values, "expires_at": timezone.now() - timedelta(seconds=1)}
    Notification.objects.filter(pk=notice.pk).update(**values)
    assert not notifications_for_user(user).exists()


def test_linked_release_must_be_active_and_published(user, notice):
    release = published_release()
    notice.release = release
    notice.save()
    assert notifications_for_user(user).exists()
    Release.objects.filter(pk=release.pk).update(is_active=False)
    assert not notifications_for_user(user).exists()
    Release.objects.filter(pk=release.pk).update(
        is_active=True, status=ReleaseStatus.DRAFT
    )
    assert not notifications_for_user(user).exists()


def test_detail_lookup_cannot_bypass_feed_filters(user, notice):
    user.groups.clear()
    with pytest.raises(Notification.DoesNotExist):
        notifications_for_user(user).get(pk=notice.pk)


@pytest.mark.parametrize("published_at", (None, "future"))
def test_notification_does_not_link_to_release_notes_that_are_not_yet_available(
    user, notice, published_at
):
    release = published_release()
    release.published_at = (
        timezone.now() + timedelta(days=1) if published_at == "future" else None
    )
    release.save()
    notice.release = release
    notice.save()
    assert not notifications_for_user(user).exists()
    assert not releases_for_user(user).exists()


def test_release_catalogue_inherits_audience_and_hides_unlinked_content(user, notice):
    release = published_release()
    other = published_release("2.0.2")
    notice.release = release
    notice.save()
    assert list(releases_for_user(user)) == [release]
    with pytest.raises(Release.DoesNotExist):
        releases_for_user(user).get(pk=other.pk)
    user.groups.clear()
    assert not releases_for_user(user).exists()
    notice.audience.clear()
    assert list(releases_for_user(user)) == [release]


def test_broadcast_dismissal_is_per_user_and_retains_release_notes(user, admin, notice):
    release = published_release()
    notice.release = release
    notice.save()
    notice.audience.clear()
    user.groups.clear()
    assert notifications_for_user(user).get() == notice
    assert notifications_for_user(admin).get() == notice
    NotificationRead.objects.create(
        notification=notice, user=user, read_at=timezone.now(), dismissed=True
    )
    assert not notifications_for_user(user).exists()
    assert notifications_for_user(admin).get() == notice
    assert releases_for_user(user).get() == release
    assert not releases_for_user(AnonymousUser()).exists()
    user.is_active = False
    assert not releases_for_user(user).exists()


def test_release_notes_remain_available_after_notice_dismissal_or_expiry(user, notice):
    release = published_release()
    notice.release = release
    notice.status = NotificationStatus.EXPIRED
    notice.save()
    NotificationRead.objects.create(
        notification=notice, user=user, read_at=timezone.now(), dismissed=True
    )
    assert not notifications_for_user(user).exists()
    assert releases_for_user(user).get() == release


@pytest.mark.parametrize(
    "values",
    (
        {"status": ReleaseStatus.DRAFT},
        {"is_active": False},
        {"published_at": None},
        {"published_at": timezone.now() + timedelta(days=1)},
    ),
)
def test_release_catalogue_excludes_unpublished_inactive_or_future_notes(
    user, notice, values
):
    release = published_release()
    notice.release = release
    notice.save()
    Release.objects.filter(pk=release.pk).update(**values)
    assert not releases_for_user(user).exists()


def test_release_ordering_uses_publication_time_not_version_text(user, audience):
    first = published_release("2.10.0")
    latest = published_release("2.9.0")
    for release in (first, latest):
        notification = Notification.objects.create(
            title="Announcement", release=release
        )
        notification.audience.add(audience)
    assert releases_for_user(user).first() == latest
