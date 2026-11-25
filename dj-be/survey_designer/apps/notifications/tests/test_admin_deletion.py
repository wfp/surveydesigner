import pytest
from django.contrib import admin as django_admin
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.admin.models import DELETION, LogEntry
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse
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
from notifications.services import publish_release

pytestmark = pytest.mark.django_db


def draft(name):
    if name == "release":
        return Release.objects.create(
            business_version="2.0.1", title="Release", body="Release notes"
        )
    return Notification.objects.create(title="Notification", body="Message")


def admin_url(record, action):
    return reverse(
        f"admin:notifications_{record._meta.model_name}_{action}", args=(record.pk,)
    )


@pytest.mark.parametrize("name", ("release", "notification"))
def test_draft_delete_requires_confirmation_and_records_audit(
    logged_admin_client, admin, name
):
    record = draft(name)
    if name == "release":
        translation = ReleaseTranslation.objects.create(
            release=record, language="fr", title="Titre", label="Contenu"
        )
    else:
        translation = NotificationTranslation.objects.create(
            notification=record, language="fr", title="Titre", label="Contenu"
        )
        group = Group.objects.create(name="Draft audience")
        audience = NotificationAudience.objects.create(notification=record, group=group)

    change = logged_admin_client.get(admin_url(record, "change"))
    assert change.context["has_delete_permission"] is True
    confirmation = logged_admin_client.get(admin_url(record, "delete"))
    assert confirmation.status_code == 200
    assert type(record).objects.filter(pk=record.pk).exists()

    response = logged_admin_client.post(admin_url(record, "delete"), {"post": "yes"})

    assert response.status_code == 302
    assert not type(record).objects.filter(pk=record.pk).exists()
    assert not type(translation).objects.filter(pk=translation.pk).exists()
    assert LogEntry.objects.filter(
        user=admin,
        content_type__app_label="notifications",
        content_type__model=name,
        object_id=str(record.pk),
        action_flag=DELETION,
    ).exists()
    if name == "notification":
        assert not NotificationAudience.objects.filter(pk=audience.pk).exists()
        assert Group.objects.filter(pk=group.pk).exists()


def test_deleting_manually_linked_draft_notification_unblocks_release_publication(
    logged_admin_client, admin
):
    release = draft("release")
    notification = Notification.objects.create(release=release, title="Manual draft")
    with pytest.raises(ValidationError, match="already has a linked notification"):
        publish_release(release_id=release.pk, actor=admin)

    response = logged_admin_client.post(
        admin_url(notification, "delete"), {"post": "yes"}
    )
    assert response.status_code == 302
    assert Release.objects.filter(pk=release.pk).exists()

    generated, created = publish_release(release_id=release.pk, actor=admin)
    release.refresh_from_db()
    assert created is True
    assert release.status == ReleaseStatus.PUBLISHED
    assert generated.release_id == release.pk
    assert generated.status == NotificationStatus.DRAFT


def test_linked_draft_release_requires_notification_to_be_deleted_first(
    logged_admin_client,
):
    release = draft("release")
    notification = Notification.objects.create(release=release, title="Manual draft")

    response = logged_admin_client.post(admin_url(release, "delete"), {"post": "yes"})
    assert response.status_code == 200
    assert response.context["protected"]
    assert Release.objects.filter(pk=release.pk).exists()
    assert Notification.objects.filter(pk=notification.pk).exists()

    logged_admin_client.post(admin_url(notification, "delete"), {"post": "yes"})
    response = logged_admin_client.post(admin_url(release, "delete"), {"post": "yes"})
    assert response.status_code == 302
    assert not Release.objects.filter(pk=release.pk).exists()


@pytest.mark.parametrize(
    "status",
    (
        NotificationStatus.SCHEDULED,
        NotificationStatus.PUBLISHED,
        NotificationStatus.EXPIRED,
    ),
)
@pytest.mark.parametrize("is_active", (True, False))
def test_approved_notifications_cannot_be_deleted(
    logged_admin_client, status, is_active
):
    notification = Notification.objects.create(
        title="Approved", status=status, is_active=is_active
    )
    response = logged_admin_client.post(
        admin_url(notification, "delete"), {"post": "yes"}
    )
    assert response.status_code == 403
    assert Notification.objects.filter(pk=notification.pk).exists()


def test_draft_notification_with_published_release_is_preserved(logged_admin_client):
    release = draft("release")
    release.status = ReleaseStatus.PUBLISHED
    release.published_at = timezone.now()
    release.save()
    notification = Notification.objects.create(release=release, title="Generated draft")

    response = logged_admin_client.post(
        admin_url(notification, "delete"), {"post": "yes"}
    )
    assert response.status_code == 403
    assert Notification.objects.filter(pk=notification.pk).exists()


def test_draft_notification_with_read_history_is_preserved(logged_admin_client, user):
    notification = draft("notification")
    state = NotificationRead.objects.create(
        notification=notification, user=user, read_at=timezone.now()
    )

    response = logged_admin_client.post(
        admin_url(notification, "delete"), {"post": "yes"}
    )
    assert response.status_code == 403
    assert NotificationRead.objects.filter(pk=state.pk).exists()
    assert Notification.objects.filter(pk=notification.pk).exists()


def test_draft_release_with_publication_history_is_preserved(logged_admin_client):
    release = draft("release")
    release.published_at = timezone.now()
    release.save()

    response = logged_admin_client.post(admin_url(release, "delete"), {"post": "yes"})
    assert response.status_code == 403
    assert Release.objects.filter(pk=release.pk).exists()


@pytest.mark.parametrize("name", ("release", "notification"))
@pytest.mark.parametrize("can_delete", (True, False))
def test_deleting_a_draft_requires_its_delete_permission(
    django_client, user, name, can_delete
):
    record = draft(name)
    user.is_staff = True
    user.save()
    codenames = [f"view_{name}", f"change_{name}"]
    if can_delete:
        codenames.append(f"delete_{name}")
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="notifications", codename__in=codenames
        )
    )
    django_client.force_login(user)

    response = django_client.post(admin_url(record, "delete"), {"post": "yes"})
    assert response.status_code == (302 if can_delete else 403)
    assert type(record).objects.filter(pk=record.pk).exists() is not can_delete


@pytest.mark.parametrize("name", ("release", "notification"))
def test_bulk_delete_is_not_enabled(logged_admin_client, name):
    record = draft(name)
    url = reverse(f"admin:notifications_{name}_changelist")
    response = logged_admin_client.get(url)
    actions = response.context["action_form"].fields["action"].choices
    assert "delete_selected" not in dict(actions)

    logged_admin_client.post(
        url,
        {"action": "delete_selected", ACTION_CHECKBOX_NAME: [record.pk], "post": "yes"},
    )
    assert type(record).objects.filter(pk=record.pk).exists()


@pytest.mark.parametrize("name", ("release", "notification"))
def test_delete_rechecks_current_status_instead_of_using_a_stale_draft(admin, rf, name):
    record = draft(name)
    type(record).objects.filter(pk=record.pk).update(status="published")
    request = rf.post(admin_url(record, "delete"), {"post": "yes"})
    request.user = admin
    model_admin = django_admin.site._registry[type(record)]

    with pytest.raises(PermissionDenied):
        model_admin.delete_model(request, record)

    assert type(record).objects.filter(pk=record.pk).exists()
