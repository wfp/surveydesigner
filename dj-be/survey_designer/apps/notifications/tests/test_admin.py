from datetime import timedelta

import pytest
from django.contrib import admin as django_admin
from django.contrib.auth.models import Group, Permission
from django.urls import reverse
from django.utils import timezone
from notifications.const import NotificationStatus, ReleaseStatus
from notifications.forms import (
    NotificationTranslationAdminForm,
    ReleaseTranslationAdminForm,
)
from notifications.models import (
    Notification,
    NotificationAudience,
    NotificationRead,
    NotificationTranslation,
    Release,
    ReleaseTranslation,
)

pytestmark = pytest.mark.django_db


def management(prefix, total=0, initial=0):
    return {
        f"{prefix}-TOTAL_FORMS": str(total),
        f"{prefix}-INITIAL_FORMS": str(initial),
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
    }


def release_data():
    return {
        "business_version": "2.0.1",
        "configuration_version": "1.0.1",
        "title": "Release 2.0.1",
        "body": "<p>Updated validation.</p>",
        "is_active": "on",
        **management("translations"),
    }


def notification_data():
    return {
        "title": "Survey Designer update",
        "abstract": "Validation improvements",
        "body": "<p>Updated validation.</p>",
        "is_active": "on",
        "publish_at_0": "2026-11-03",
        "publish_at_1": "12:00:00",
        **management("translations"),
        **management("audience_entries"),
    }


@pytest.mark.parametrize("model", (Release, Notification, NotificationRead))
def test_notification_models_are_registered(model):
    assert django_admin.site.is_registered(model)


@pytest.mark.parametrize(
    "model", (ReleaseTranslation, NotificationTranslation, NotificationAudience)
)
def test_child_records_are_managed_through_inlines_only(model):
    assert not django_admin.site.is_registered(model)


@pytest.mark.parametrize("name", ("release", "notification", "notificationread"))
def test_changelists_render_for_admin(logged_admin_client, name):
    response = logged_admin_client.get(
        reverse(f"admin:notifications_{name}_changelist")
    )
    assert response.status_code == 200


@pytest.mark.parametrize("name", ("release", "notification"))
def test_add_forms_render_with_content_inlines(logged_admin_client, name):
    response = logged_admin_client.get(reverse(f"admin:notifications_{name}_add"))
    assert response.status_code == 200
    assert b"translations-TOTAL_FORMS" in response.content
    form = response.context["adminform"].form
    assert "status" not in form.fields
    assert "created_by" not in form.fields
    assert form.fields["body"].label == "Body (English, HTML)"


def test_create_release_with_translation_and_server_owned_audit(
    logged_admin_client, admin, user
):
    data = {
        **release_data(),
        **management("translations", total=1),
        "translations-0-language": "fr",
        "translations-0-title": "Version francaise",
        "translations-0-label": "<p>Validation amelioree.</p>",
        "created_by": str(user.pk),
        "updated_by": str(user.pk),
        "status": ReleaseStatus.PUBLISHED,
        "github_release_id": "forged-id",
    }
    response = logged_admin_client.post(
        reverse("admin:notifications_release_add"), data
    )

    assert response.status_code == 302
    release = Release.objects.get(business_version="2.0.1")
    assert release.created_by == admin
    assert release.updated_by == admin
    assert release.status == ReleaseStatus.DRAFT
    assert release.github_release_id == ""
    assert release.published_at is None
    translation = release.translations.get(language="fr")
    assert translation.label == "<p>Validation amelioree.</p>"
    assert translation.created_by == admin
    assert translation.updated_by == admin
    assert Notification.objects.count() == 0


def test_create_notification_with_translation_and_audience(logged_admin_client, admin):
    group = Group.objects.create(name="Notification audience")
    data = {
        **notification_data(),
        **management("translations", total=1),
        "translations-0-language": "fr",
        "translations-0-title": "Mise a jour",
        "translations-0-abstract": "Resume",
        "translations-0-label": "<p>Nouveautes.</p>",
        **management("audience_entries", total=1),
        "audience_entries-0-group": str(group.pk),
        "status": NotificationStatus.PUBLISHED,
    }
    response = logged_admin_client.post(
        reverse("admin:notifications_notification_add"), data
    )

    assert response.status_code == 302
    notification = Notification.objects.get()
    assert notification.release is None
    assert notification.status == NotificationStatus.DRAFT
    assert notification.created_by == admin
    assert notification.updated_by == admin
    assert list(notification.audience.all()) == [group]
    translation = notification.translations.get(language="fr")
    assert translation.abstract == "Resume"
    assert translation.created_by == admin
    assert translation.updated_by == admin
    assert NotificationRead.objects.count() == 0


def test_edit_preserves_creator_and_updates_changed_translation_audit(
    logged_admin_client, admin, user
):
    release = Release.objects.create(
        business_version="2.0.1", title="Original", created_by=user, updated_by=user
    )
    translation = ReleaseTranslation.objects.create(
        release=release,
        language="fr",
        title="Original",
        label="Body",
        created_by=user,
        updated_by=user,
    )
    response = logged_admin_client.post(
        reverse("admin:notifications_release_change", args=(release.pk,)),
        {
            **release_data(),
            **management("translations", total=1, initial=1),
            "translations-0-id": str(translation.pk),
            "translations-0-release": str(release.pk),
            "translations-0-language": "fr",
            "translations-0-title": "Updated translation",
            "translations-0-label": "Updated body",
        },
    )
    assert response.status_code == 302
    release.refresh_from_db()
    translation.refresh_from_db()
    assert release.created_by == user
    assert release.updated_by == admin
    assert translation.created_by == user
    assert translation.updated_by == admin
    assert translation.label == "Updated body"


@pytest.mark.parametrize(
    "form_class", (ReleaseTranslationAdminForm, NotificationTranslationAdminForm)
)
def test_translation_forms_exclude_english_and_keep_language_widget(form_class):
    form = form_class()
    assert "en" not in dict(form.fields["language"].choices)
    assert "fr" in dict(form.fields["language"].choices)
    assert form.fields["label"].label == "Body (HTML)"


def test_english_translation_error_does_not_save_parent(logged_admin_client):
    response = logged_admin_client.post(
        reverse("admin:notifications_release_add"),
        {
            **release_data(),
            **management("translations", total=1),
            "translations-0-language": "en",
            "translations-0-title": "English",
            "translations-0-label": "Body",
        },
    )
    assert response.status_code == 200
    formset = response.context["inline_admin_formsets"][0].formset
    assert "language" in formset.forms[0].errors
    assert Release.objects.count() == 0


def test_duplicate_translations_show_form_errors_without_partial_save(
    logged_admin_client,
):
    data = {**release_data(), **management("translations", total=2)}
    for i in range(2):
        data.update(
            {
                f"translations-{i}-language": "fr",
                f"translations-{i}-title": "French",
                f"translations-{i}-label": "Body",
            }
        )
    response = logged_admin_client.post(
        reverse("admin:notifications_release_add"), data
    )
    assert response.status_code == 200
    assert response.context["inline_admin_formsets"][0].formset.non_form_errors()
    assert Release.objects.count() == 0


def test_duplicate_audience_groups_show_form_errors(logged_admin_client):
    group = Group.objects.create(name="Audience")
    data = {**notification_data(), **management("audience_entries", total=2)}
    for i in range(2):
        data[f"audience_entries-{i}-group"] = str(group.pk)
    response = logged_admin_client.post(
        reverse("admin:notifications_notification_add"), data
    )
    assert response.status_code == 200
    assert response.context["inline_admin_formsets"][1].formset.non_form_errors()
    assert Notification.objects.count() == 0


def test_invalid_expiry_returns_field_error(logged_admin_client):
    response = logged_admin_client.post(
        reverse("admin:notifications_notification_add"),
        {
            **notification_data(),
            "expires_at_0": "2026-11-03",
            "expires_at_1": "11:00:00",
        },
    )
    assert response.status_code == 200
    assert "expires_at" in response.context["adminform"].form.errors
    assert Notification.objects.count() == 0


def test_audience_and_translation_inlines_can_be_removed(logged_admin_client):
    notification = Notification.objects.create(title="Original")
    translation = NotificationTranslation.objects.create(
        notification=notification, language="fr", title="Title", label="Body"
    )
    audience = NotificationAudience.objects.create(
        notification=notification, group=Group.objects.create(name="Audience")
    )
    response = logged_admin_client.post(
        reverse("admin:notifications_notification_change", args=(notification.pk,)),
        {
            **notification_data(),
            **management("translations", total=1, initial=1),
            "translations-0-id": str(translation.pk),
            "translations-0-notification": str(notification.pk),
            "translations-0-language": "fr",
            "translations-0-title": "Title",
            "translations-0-label": "Body",
            "translations-0-DELETE": "on",
            **management("audience_entries", total=1, initial=1),
            "audience_entries-0-id": str(audience.pk),
            "audience_entries-0-notification": str(notification.pk),
            "audience_entries-0-group": str(audience.group_id),
            "audience_entries-0-DELETE": "on",
        },
    )
    assert response.status_code == 302
    assert not notification.translations.exists()
    assert not notification.audience_entries.exists()


@pytest.mark.parametrize("name", ("release", "notification"))
def test_content_delete_is_disabled_even_for_admin(logged_admin_client, name):
    record = (
        Release.objects.create(business_version="2.0.1", title="Release")
        if name == "release"
        else Notification.objects.create(title="Notification")
    )
    response = logged_admin_client.post(
        reverse(f"admin:notifications_{name}_delete", args=(record.pk,)),
        {"post": "yes"},
    )
    assert response.status_code == 403
    assert type(record).objects.filter(pk=record.pk).exists()


def test_content_can_be_deactivated_without_deletion(logged_admin_client):
    release = Release.objects.create(business_version="2.0.1", title="Release")
    data = release_data()
    data.pop("is_active")
    response = logged_admin_client.post(
        reverse("admin:notifications_release_change", args=(release.pk,)), data
    )
    assert response.status_code == 302
    release.refresh_from_db()
    assert release.is_active is False


def test_read_state_is_inspectable_but_not_editable(logged_admin_client, user):
    notification = Notification.objects.create(title="Message")
    state = NotificationRead.objects.create(notification=notification, user=user)
    change_url = reverse(
        "admin:notifications_notificationread_change", args=(state.pk,)
    )
    assert logged_admin_client.get(change_url).status_code == 200
    assert logged_admin_client.post(change_url, {"dismissed": "on"}).status_code == 403
    assert (
        logged_admin_client.get(
            reverse("admin:notifications_notificationread_add")
        ).status_code
        == 403
    )
    assert (
        logged_admin_client.post(
            reverse("admin:notifications_notificationread_delete", args=(state.pk,)),
            {"post": "yes"},
        ).status_code
        == 403
    )
    state.refresh_from_db()
    assert state.state == "unread"


def test_admin_search_handles_case_insensitive_user_email(logged_admin_client, user):
    notification = Notification.objects.create(title="Message")
    NotificationRead.objects.create(notification=notification, user=user)
    response = logged_admin_client.get(
        reverse("admin:notifications_notificationread_changelist"),
        {"q": "TEST@EXAMPLE.COM"},
    )
    assert response.status_code == 200
    assert response.context["cl"].result_count == 1


def test_release_search_and_status_filter(logged_admin_client):
    Release.objects.create(business_version="2.0.1", title="Validation release")
    Release.objects.create(
        business_version="2.0.2", title="Other release", status=ReleaseStatus.PUBLISHED
    )
    response = logged_admin_client.get(
        reverse("admin:notifications_release_changelist"),
        {"q": "validation", "status__exact": "draft"},
    )
    assert response.status_code == 200
    assert response.context["cl"].result_count == 1


def test_staff_without_permissions_cannot_edit_content(django_client, user):
    user.is_staff = True
    user.save()
    django_client.force_login(user)
    for name in ("release", "notification"):
        assert (
            django_client.get(reverse(f"admin:notifications_{name}_add")).status_code
            == 403
        )


def test_view_only_staff_cannot_mutate_content(django_client, user):
    release = Release.objects.create(business_version="2.0.1", title="Original")
    user.user_permissions.add(
        Permission.objects.get(
            codename="view_release", content_type__app_label="notifications"
        )
    )
    django_client.force_login(user)
    url = reverse("admin:notifications_release_change", args=(release.pk,))
    assert django_client.get(url).status_code == 200
    assert django_client.post(url, release_data()).status_code == 403
    release.refresh_from_db()
    assert release.title == "Original"


def test_read_states_do_not_change_when_notification_content_is_edited(
    logged_admin_client, user
):
    notification = Notification.objects.create(title="Original")
    now = timezone.now() - timedelta(minutes=1)
    state = NotificationRead.objects.create(
        notification=notification, user=user, read_at=now, dismissed=True
    )
    response = logged_admin_client.post(
        reverse("admin:notifications_notification_change", args=(notification.pk,)),
        notification_data(),
    )
    assert response.status_code == 302
    state.refresh_from_db()
    assert state.read_at == now
    assert state.dismissed is True
