from datetime import timedelta

import pytest
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.auth.models import Group, Permission
from django.urls import reverse
from django.utils import timezone
from notifications.const import NotificationStatus
from notifications.models import (
    Notification,
    NotificationAudience,
    NotificationRead,
    NotificationTranslation,
)

pytestmark = pytest.mark.django_db


def action(client, notice, name):
    return client.post(
        reverse("admin:notifications_notification_changelist"),
        {"action": name, "index": "0", ACTION_CHECKBOX_NAME: [str(notice.pk)]},
        follow=True,
    )


@pytest.fixture
def notice():
    return Notification.objects.create(
        title="Original title",
        body="Original body",
        publish_at=timezone.now() - timedelta(minutes=1),
    )


def test_admin_can_publish_schedule_and_deactivate(logged_admin_client, notice):
    response = action(logged_admin_client, notice, "publish_notifications")
    assert response.status_code == 200
    notice.refresh_from_db()
    assert notice.status == NotificationStatus.PUBLISHED
    action(logged_admin_client, notice, "deactivate_notifications")
    notice.refresh_from_db()
    assert notice.is_active is False
    notice.publish_at = timezone.now() + timedelta(hours=1)
    notice.save()
    action(logged_admin_client, notice, "publish_notifications")
    notice.refresh_from_db()
    assert notice.is_active is True
    assert notice.status == NotificationStatus.SCHEDULED


@pytest.mark.parametrize(
    "status",
    (
        NotificationStatus.SCHEDULED,
        NotificationStatus.PUBLISHED,
        NotificationStatus.EXPIRED,
    ),
)
def test_approved_content_and_timing_are_readonly(logged_admin_client, notice, status):
    notice.status = status
    notice.save()
    response = logged_admin_client.get(
        reverse("admin:notifications_notification_change", args=(notice.pk,))
    )
    assert response.status_code == 200
    fields = response.context["adminform"].form.fields
    for field in ("title", "body", "publish_at", "expires_at", "release", "is_active"):
        assert field not in fields


def test_forged_edit_cannot_modify_active_content_or_translations(
    logged_admin_client, notice
):
    notice.status = NotificationStatus.SCHEDULED
    notice.save()
    translation = NotificationTranslation.objects.create(
        notification=notice,
        language="fr",
        title="Original translation",
        label="Original body",
    )
    group = Group.objects.create(name="Original group")
    other = Group.objects.create(name="Other group")
    audience = NotificationAudience.objects.create(notification=notice, group=group)
    response = logged_admin_client.post(
        reverse("admin:notifications_notification_change", args=(notice.pk,)),
        {
            "title": "Forged title",
            "body": "Forged body",
            "publish_at_0": "2099-01-01",
            "publish_at_1": "12:00:00",
            "translations-TOTAL_FORMS": "1",
            "translations-INITIAL_FORMS": "1",
            "translations-0-id": str(translation.pk),
            "translations-0-notification": str(notice.pk),
            "translations-0-language": "fr",
            "translations-0-title": "Forged translation",
            "translations-0-label": "Forged body",
            "audience_entries-TOTAL_FORMS": "1",
            "audience_entries-INITIAL_FORMS": "1",
            "audience_entries-0-id": str(audience.pk),
            "audience_entries-0-notification": str(notice.pk),
            "audience_entries-0-group": str(other.pk),
        },
    )
    assert response.status_code == 302
    notice.refresh_from_db()
    translation.refresh_from_db()
    audience.refresh_from_db()
    assert notice.title == "Original title"
    assert notice.publish_at.year != 2099
    assert translation.title == "Original translation"
    assert audience.group == group


def test_deactivated_content_can_be_edited_without_silently_reactivating(
    logged_admin_client, notice
):
    notice.status = NotificationStatus.PUBLISHED
    notice.is_active = False
    notice.save()
    response = logged_admin_client.post(
        reverse("admin:notifications_notification_change", args=(notice.pk,)),
        {
            "title": "Edited title",
            "body": "Edited notes",
            "is_active": "on",
            "publish_at_0": "2026-11-03",
            "publish_at_1": "12:00:00",
            "translations-TOTAL_FORMS": "0",
            "translations-INITIAL_FORMS": "0",
            "audience_entries-TOTAL_FORMS": "0",
            "audience_entries-INITIAL_FORMS": "0",
        },
    )
    assert response.status_code == 302
    notice.refresh_from_db()
    assert notice.title == "Edited title"
    assert notice.is_active is False


def test_expired_publication_error_is_readable(logged_admin_client, notice):
    notice.expires_at = timezone.now() - timedelta(seconds=1)
    notice.save()
    response = action(logged_admin_client, notice, "publish_notifications")
    assert any(
        "expires_at" in str(message) and "already passed" in str(message)
        for message in response.context["messages"]
    )
    notice.refresh_from_db()
    assert notice.status == NotificationStatus.DRAFT


def test_actions_preserve_read_and_dismiss_state(logged_admin_client, notice, user):
    state = NotificationRead.objects.create(
        notification=notice, user=user, read_at=timezone.now(), dismissed=True
    )
    action(logged_admin_client, notice, "publish_notifications")
    action(logged_admin_client, notice, "deactivate_notifications")
    action(logged_admin_client, notice, "publish_notifications")
    state.refresh_from_db()
    assert state.state == "dismissed"


def test_view_only_staff_cannot_use_lifecycle_actions(django_client, notice, user):
    user.user_permissions.add(
        Permission.objects.get(
            codename="view_notification", content_type__app_label="notifications"
        )
    )
    django_client.force_login(user)
    action(django_client, notice, "publish_notifications")
    action(django_client, notice, "deactivate_notifications")
    notice.refresh_from_db()
    assert notice.status == NotificationStatus.DRAFT
    assert notice.is_active is True
