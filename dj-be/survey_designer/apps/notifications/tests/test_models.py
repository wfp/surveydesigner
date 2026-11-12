from datetime import timedelta

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
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

pytestmark = pytest.mark.django_db


@pytest.fixture
def release():
    return Release.objects.create(business_version="2.0.1", title="Release 2.0.1")


@pytest.fixture
def notification():
    return Notification.objects.create(title="Survey Designer update")


def test_release_defaults_and_metadata(release, user):
    assert str(release) == "2.0.1"
    assert release.status == ReleaseStatus.DRAFT
    assert release.is_active is True
    assert release.released_at is None
    assert release.published_at is None
    assert release.created_by is None
    assert release.updated_by is None
    assert release.date_created is not None
    assert release.date_updated is not None

    release.github_tag = "v2.0.1"
    release.github_release_id = "12345"
    release.github_url = "https://github.com/wfp/surveydesigner/releases/tag/v2.0.1"
    release.configuration_version = "1.0.1"
    release.body = "<p>Updated validation.</p>"
    release.created_by = user
    release.updated_by = user
    release.full_clean()
    release.save()
    release.refresh_from_db()

    assert release.github_tag == "v2.0.1"
    assert release.github_release_id == "12345"
    assert release.configuration_version == "1.0.1"
    assert release.body == "<p>Updated validation.</p>"
    assert release.created_by == user


def test_release_version_is_unique(release):
    with pytest.raises(IntegrityError), transaction.atomic():
        Release.objects.create(
            business_version=release.business_version, title="Duplicate"
        )


def test_release_ordering_uses_publication_date_not_version_text():
    now = timezone.now()
    older = Release.objects.create(
        business_version="2.10.0", title="Older", published_at=now
    )
    latest = Release.objects.create(
        business_version="2.9.0",
        title="Latest",
        published_at=now + timedelta(minutes=1),
    )

    assert list(Release.objects.all()) == [latest, older]


def test_notification_defaults_and_standalone_records(notification):
    second = Notification.objects.create(title="Standalone announcement")

    assert str(notification) == "Survey Designer update"
    assert notification.release is None
    assert second.release is None
    assert notification.status == NotificationStatus.DRAFT
    assert notification.is_active is True
    assert timezone.is_aware(notification.publish_at)
    assert notification.expires_at is None
    assert notification.abstract == ""
    assert notification.body == ""
    assert notification.date_created is not None
    assert notification.created_by is None
    assert notification.updated_by is None
    notification.full_clean()


def test_release_has_at_most_one_notification(release):
    linked = Notification.objects.create(title="Release update", release=release)

    assert release.notification == linked
    with pytest.raises(IntegrityError), transaction.atomic():
        Notification.objects.create(title="Duplicate announcement", release=release)


def test_linked_release_is_protected_from_hard_deletion(release):
    Notification.objects.create(title="Release update", release=release)

    with pytest.raises(ProtectedError):
        release.delete()


def test_inactive_flag_does_not_delete_content(release, notification):
    release.is_active = False
    release.save(update_fields=("is_active",))
    notification.is_active = False
    notification.save(update_fields=("is_active",))

    assert Release.objects.filter(pk=release.pk, is_active=False).exists()
    assert Notification.objects.filter(pk=notification.pk, is_active=False).exists()


@pytest.mark.parametrize("model", (Release, Notification))
def test_invalid_status_is_rejected_by_validation_and_database(model):
    values = {"title": "Invalid status", "status": "unknown"}
    if model is Release:
        values["business_version"] = "invalid-status"

    with pytest.raises(ValidationError) as raised:
        model(**values).full_clean()
    assert "status" in raised.value.message_dict

    with pytest.raises(IntegrityError), transaction.atomic():
        model.objects.create(**values)


@pytest.mark.parametrize("status", ReleaseStatus.values)
def test_release_accepts_declared_statuses(status):
    release = Release.objects.create(
        business_version=status, title=status, status=status
    )
    release.full_clean()


@pytest.mark.parametrize("status", NotificationStatus.values)
def test_notification_accepts_declared_statuses(status):
    notification = Notification.objects.create(title=status, status=status)
    notification.full_clean()


@pytest.mark.parametrize("offset", (-1, 0))
def test_expiry_must_be_after_publication(offset):
    publish_at = timezone.now()
    values = {
        "title": "Invalid expiry",
        "publish_at": publish_at,
        "expires_at": publish_at + timedelta(seconds=offset),
    }
    with pytest.raises(ValidationError) as raised:
        Notification(**values).full_clean()
    assert "expires_at" in raised.value.message_dict

    with pytest.raises(IntegrityError), transaction.atomic():
        Notification.objects.create(**values)


def test_future_publication_and_valid_expiry_are_preserved():
    publish_at = timezone.now() + timedelta(days=1)
    notification = Notification.objects.create(
        title="Scheduled update",
        status=NotificationStatus.SCHEDULED,
        publish_at=publish_at,
        expires_at=publish_at + timedelta(days=7),
    )
    notification.full_clean()
    notification.refresh_from_db()

    assert notification.publish_at == publish_at
    assert notification.expires_at == publish_at + timedelta(days=7)


@pytest.mark.parametrize(
    ("model", "owner_field", "fixture"),
    (
        (ReleaseTranslation, "release", "release"),
        (NotificationTranslation, "notification", "notification"),
    ),
)
@pytest.mark.parametrize(
    "language", [code for code, _ in settings.LANGUAGES if code != "en"]
)
def test_supported_translations_reuse_the_body_and_audit_mixins(
    model, owner_field, fixture, language, request, user
):
    owner = request.getfixturevalue(fixture)
    values = {
        owner_field: owner,
        "language": language,
        "title": "Translated title",
        "label": "<p>Translated body.</p>",
        "created_by": user,
        "updated_by": user,
    }
    if model is NotificationTranslation:
        values["abstract"] = "Translated summary"
    translation = model.objects.create(**values)
    translation.full_clean()

    assert owner.translations.get(language=language) == translation
    assert translation.label == "<p>Translated body.</p>"
    assert translation.created_by == user
    assert translation.date_created is not None
    assert translation.date_updated is not None
    assert str(translation) == f"{owner} ({language})"


@pytest.mark.parametrize(
    ("model", "owner_field", "fixture"),
    (
        (ReleaseTranslation, "release", "release"),
        (NotificationTranslation, "notification", "notification"),
    ),
)
def test_translation_language_is_unique_per_owner(model, owner_field, fixture, request):
    owner = request.getfixturevalue(fixture)
    values = {
        owner_field: owner,
        "language": "fr",
        "title": "French title",
        "label": "French body",
    }
    model.objects.create(**values)

    with pytest.raises(IntegrityError), transaction.atomic():
        model.objects.create(**values)

    other = (
        Release.objects.create(business_version="2.0.2", title="Another release")
        if model is ReleaseTranslation
        else Notification.objects.create(title="Another notification")
    )
    values[owner_field] = other
    model.objects.create(**values)


@pytest.mark.parametrize(
    ("model", "owner_field", "fixture"),
    (
        (ReleaseTranslation, "release", "release"),
        (NotificationTranslation, "notification", "notification"),
    ),
)
def test_english_translation_rows_are_rejected(model, owner_field, fixture, request):
    values = {
        owner_field: request.getfixturevalue(fixture),
        "language": "en",
        "title": "English title",
        "label": "English body",
    }
    with pytest.raises(ValidationError) as raised:
        model(**values).full_clean()
    assert "language" in raised.value.message_dict

    with pytest.raises(IntegrityError), transaction.atomic():
        model.objects.bulk_create([model(**values)])


@pytest.mark.parametrize("model", (ReleaseTranslation, NotificationTranslation))
def test_unknown_translation_language_is_rejected(model):
    translation = model(language="unknown", title="Title", label="Body")

    with pytest.raises(ValidationError) as raised:
        translation.full_clean(exclude=("release", "notification"))
    assert "language" in raised.value.message_dict


def test_audience_uses_existing_groups_and_unique_memberships(notification):
    admins = Group.objects.create(name="Notification Admins")
    designers = Group.objects.create(name="Notification Designers")
    notification.audience.add(admins, designers)

    assert set(notification.audience.all()) == {admins, designers}
    assert list(admins.notifications.all()) == [notification]
    entry = notification.audience_entries.get(group=admins)
    assert str(entry) == f"{notification}: {admins}"

    with pytest.raises(IntegrityError), transaction.atomic():
        NotificationAudience.objects.create(notification=notification, group=admins)


def test_notification_state_is_per_account(notification, user):
    other = get_user_model().objects.create_user(email="other-notification@example.com")
    unread = NotificationRead.objects.create(notification=notification, user=user)
    seen = NotificationRead.objects.create(
        notification=notification, user=other, read_at=timezone.now()
    )

    assert unread.state == "unread"
    assert seen.state == "read"
    assert unread.dismissed is False
    assert unread.date_created is not None
    assert list(user.notification_reads.all()) == [unread]
    assert notification.read_states.count() == 2

    with pytest.raises(IntegrityError), transaction.atomic():
        NotificationRead.objects.create(notification=notification, user=user)


def test_dismissed_state_takes_precedence(notification, user):
    read = NotificationRead.objects.create(
        notification=notification, user=user, read_at=timezone.now(), dismissed=True
    )
    read.full_clean()

    assert read.state == "dismissed"
    assert str(read) == f"{user}: {notification} (dismissed)"


def test_dismissed_requires_a_read_timestamp(notification, user):
    values = {"notification": notification, "user": user, "dismissed": True}
    with pytest.raises(ValidationError) as raised:
        NotificationRead(**values).full_clean()
    assert "read_at" in raised.value.message_dict

    with pytest.raises(IntegrityError), transaction.atomic():
        NotificationRead.objects.create(**values)


def test_hard_deleting_notification_cascades_related_rows(notification, user):
    translation = NotificationTranslation.objects.create(
        notification=notification, language="fr", title="Title", label="Body"
    )
    audience = NotificationAudience.objects.create(
        notification=notification, group=Group.objects.create(name="Test audience")
    )
    read = NotificationRead.objects.create(notification=notification, user=user)
    notification.delete()

    assert not NotificationTranslation.objects.filter(pk=translation.pk).exists()
    assert not NotificationAudience.objects.filter(pk=audience.pk).exists()
    assert not NotificationRead.objects.filter(pk=read.pk).exists()


def test_publication_and_read_fanout_are_not_implicit_model_side_effects(user):
    Release.objects.create(
        business_version="2.0.1",
        title="Published release",
        status=ReleaseStatus.PUBLISHED,
        published_at=timezone.now(),
    )
    assert Notification.objects.count() == 0
    Notification.objects.create(
        title="Published message", status=NotificationStatus.PUBLISHED
    )
    assert NotificationRead.objects.count() == 0


def test_deleting_audit_user_preserves_content(release, notification, user):
    for record in (release, notification):
        record.created_by = user
        record.updated_by = user
        record.save()
    user.delete()

    for record in (release, notification):
        record.refresh_from_db()
        assert record.created_by is None
        assert record.updated_by is None
