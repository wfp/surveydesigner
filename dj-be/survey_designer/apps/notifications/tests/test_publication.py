from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import close_old_connections, connection, connections
from django.utils import timezone
from notifications.const import NotificationStatus, ReleaseStatus
from notifications.models import (
    Notification,
    NotificationAudience,
    NotificationRead,
    NotificationTranslation,
    Release,
    ReleaseTranslation,
)
from notifications.services import can_publish_release, publish_release

pytestmark = pytest.mark.django_db


@pytest.fixture
def release(user):
    return Release.objects.create(
        business_version="2.0.1",
        title="Release 2.0.1",
        body="<p>Improved survey validation.</p>",
        created_by=user,
        updated_by=user,
    )


def add_translation(release, language="fr"):
    return ReleaseTranslation.objects.create(
        release=release,
        language=language,
        title="Translated title",
        label="<p>Translated body.</p>",
    )


def test_publication_creates_a_draft_snapshot_with_saved_translations(
    release, admin, user
):
    french = add_translation(release)
    arabic = add_translation(release, "ar")
    notification, created = publish_release(release_id=release.pk, actor=admin)
    release.refresh_from_db()

    assert created is True
    assert release.status == ReleaseStatus.PUBLISHED
    assert release.published_at is not None
    assert release.created_by == user
    assert release.updated_by == admin
    assert notification.release == release
    assert notification.title == release.title
    assert notification.body == release.body
    assert notification.abstract == ""
    assert notification.status == NotificationStatus.DRAFT
    assert notification.publish_at == release.published_at
    assert notification.created_by == admin
    assert notification.updated_by == admin
    assert notification.is_active is True
    for original in (french, arabic):
        snapshot = notification.translations.get(language=original.language)
        assert snapshot.title == original.title
        assert snapshot.label == original.label
        assert snapshot.abstract == ""
        assert snapshot.created_by == admin
        assert snapshot.updated_by == admin
    assert NotificationAudience.objects.count() == 0
    assert NotificationRead.objects.count() == 0


def test_release_without_translations_can_be_published(release, admin):
    notification, created = publish_release(release_id=release.pk, actor=admin)
    assert created is True
    assert notification.translations.count() == 0


def test_retry_does_not_overwrite_snapshot_or_reset_state(release, admin, user):
    translation = add_translation(release)
    notification, _ = publish_release(release_id=release.pk, actor=admin)
    read_at = timezone.now()
    read = NotificationRead.objects.create(
        notification=notification, user=user, read_at=read_at, dismissed=True
    )
    release.refresh_from_db()
    published_at = release.published_at
    updated_at = release.date_updated
    Release.objects.filter(pk=release.pk).update(title="Edited after publication")
    translation.title = "Edited translation"
    translation.save()
    notification.title = "Curated notification"
    notification.is_active = False
    notification.save()
    snapshot = notification.translations.get(language="fr")
    snapshot.title = "Curated translation"
    snapshot.save()

    retried, created = publish_release(release_id=release.pk, actor=admin)
    release.refresh_from_db()
    read.refresh_from_db()

    assert created is False
    assert retried.pk == notification.pk
    assert retried.title == "Curated notification"
    assert retried.is_active is False
    assert retried.translations.get(language="fr").title == "Curated translation"
    assert release.published_at == published_at
    assert release.date_updated == updated_at
    assert Notification.objects.count() == 1
    assert NotificationTranslation.objects.count() == 1
    assert read.read_at == read_at
    assert read.dismissed is True


def test_inactive_draft_cannot_be_published(release, admin):
    release.is_active = False
    release.save()
    with pytest.raises(ValidationError, match="Inactive"):
        publish_release(release_id=release.pk, actor=admin)
    release.refresh_from_db()
    assert release.status == ReleaseStatus.DRAFT
    assert release.published_at is None
    assert Notification.objects.count() == 0


@pytest.mark.parametrize("field", ("business_version", "title", "body"))
@pytest.mark.parametrize("value", ("", "   "))
def test_required_publication_content_is_validated(release, admin, field, value):
    Release.objects.filter(pk=release.pk).update(**{field: value})
    with pytest.raises(ValidationError):
        publish_release(release_id=release.pk, actor=admin)
    release.refresh_from_db()
    assert release.status == ReleaseStatus.DRAFT
    assert Notification.objects.count() == 0


@pytest.mark.parametrize(
    "values",
    (
        {"language": "unsupported"},
        {"title": ""},
        {"label": ""},
        {"title": "   "},
        {"label": "   "},
    ),
)
def test_invalid_saved_translation_blocks_publication(release, admin, values):
    translation = add_translation(release)
    ReleaseTranslation.objects.filter(pk=translation.pk).update(**values)
    with pytest.raises(ValidationError, match="Translation"):
        publish_release(release_id=release.pk, actor=admin)
    release.refresh_from_db()
    assert release.status == ReleaseStatus.DRAFT
    assert release.published_at is None
    assert Notification.objects.count() == 0


def test_existing_manual_link_is_not_overwritten(release, admin):
    existing = Notification.objects.create(
        release=release, title="Manually curated", body="Manual body"
    )
    with pytest.raises(ValidationError, match="already has a linked notification"):
        publish_release(release_id=release.pk, actor=admin)
    release.refresh_from_db()
    existing.refresh_from_db()
    assert release.status == ReleaseStatus.DRAFT
    assert existing.title == "Manually curated"
    assert Notification.objects.count() == 1


@pytest.mark.parametrize("has_notification", (True, False))
def test_incomplete_published_record_is_not_silently_repaired(
    release, admin, has_notification
):
    release.status = ReleaseStatus.PUBLISHED
    release.published_at = None if has_notification else timezone.now()
    release.save()
    if has_notification:
        Notification.objects.create(release=release, title="Existing")
    with pytest.raises(ValidationError, match="no complete publication record"):
        publish_release(release_id=release.pk, actor=admin)
    assert Notification.objects.count() == int(has_notification)


def test_translation_save_failure_rolls_back_release_and_entire_snapshot(
    release, admin, mocker
):
    add_translation(release)
    add_translation(release, "ar")
    original_save = NotificationTranslation.save

    def save_snapshot(instance, *args, **kwargs):
        if instance.language == "ar":
            raise RuntimeError("Simulated translation write failure")
        return original_save(instance, *args, **kwargs)

    mocker.patch.object(NotificationTranslation, "save", save_snapshot)
    with pytest.raises(RuntimeError, match="Simulated"):
        publish_release(release_id=release.pk, actor=admin)
    release.refresh_from_db()
    assert release.status == ReleaseStatus.DRAFT
    assert release.published_at is None
    assert Notification.objects.count() == 0
    assert NotificationTranslation.objects.count() == 0


def test_release_update_failure_rolls_back_the_notification(release, admin, mocker):
    add_translation(release)
    mocker.patch.object(
        Release, "save", side_effect=RuntimeError("Simulated release failure")
    )
    with pytest.raises(RuntimeError, match="Simulated"):
        publish_release(release_id=release.pk, actor=admin)
    release.refresh_from_db()
    assert release.status == ReleaseStatus.DRAFT
    assert Notification.objects.count() == 0
    assert NotificationTranslation.objects.count() == 0


def test_publication_requires_permissions_even_outside_admin(release, user):
    assert can_publish_release(user) is False
    assert can_publish_release(AnonymousUser()) is False
    assert can_publish_release(None) is False
    with pytest.raises(PermissionDenied):
        publish_release(release_id=release.pk, actor=user)
    assert Notification.objects.count() == 0


def test_normal_user_with_all_publication_permissions_can_publish(release, user):
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="notifications",
            codename__in=(
                "change_release",
                "add_notification",
                "add_notificationtranslation",
            ),
        )
    )
    add_translation(release)
    notification, created = publish_release(release_id=release.pk, actor=user)
    assert created is True
    assert notification.created_by == user


def test_inactive_admin_cannot_publish(release, admin):
    admin.is_active = False
    admin.save()
    with pytest.raises(PermissionDenied):
        publish_release(release_id=release.pk, actor=admin)


@pytest.mark.django_db(transaction=True)
def test_concurrent_publication_creates_one_snapshot(admin):
    if not connection.features.has_select_for_update:
        pytest.skip("Requires a database supporting row locks.")
    release = Release.objects.create(
        business_version="concurrent", title="Concurrent release", body="Release notes"
    )
    add_translation(release)
    actor_id = admin.pk
    barrier = Barrier(2)

    def publish():
        close_old_connections()
        try:
            actor = get_user_model().objects.get(pk=actor_id)
            barrier.wait(timeout=10)
            notification, created = publish_release(release_id=release.pk, actor=actor)
            return notification.pk, created
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: publish(), range(2)))

    assert results[0][0] == results[1][0]
    assert sorted(created for _, created in results) == [False, True]
    assert Notification.objects.filter(release=release).count() == 1
    assert NotificationTranslation.objects.count() == 1
