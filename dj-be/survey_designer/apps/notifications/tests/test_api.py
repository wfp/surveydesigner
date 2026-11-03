from datetime import timedelta

import pytest
from django.conf import settings
from django.contrib.auth.models import Group
from django.middleware.csrf import get_token
from django.test import RequestFactory
from django.urls import include, path
from django.utils import timezone
from drf_spectacular.generators import SchemaGenerator
from notifications.const import NotificationStatus, ReleaseStatus
from notifications.models import (
    Notification,
    NotificationRead,
    NotificationTranslation,
    Release,
    ReleaseTranslation,
)
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def audience(user):
    group = Group.objects.create(name="API readers")
    user.groups.add(group)
    return group


@pytest.fixture
def release():
    return Release.objects.create(
        business_version="2.1.0",
        title="Release title",
        body="<p>Release notes</p>",
        status=ReleaseStatus.PUBLISHED,
        published_at=timezone.now() - timedelta(hours=1),
        released_at=timezone.now() - timedelta(hours=2),
    )


@pytest.fixture
def notice(audience, release):
    notice = Notification.objects.create(
        release=release,
        title="Update available",
        abstract="Changes summary",
        body="<p>English notes</p>",
        status=NotificationStatus.PUBLISHED,
        publish_at=timezone.now() - timedelta(minutes=1),
    )
    notice.audience.add(audience)
    return notice


@pytest.fixture
def consumer(api_client, user):
    api_client.force_authenticate(user)
    return api_client


def endpoints(notice, release):
    return (
        ("get", "/api/notifications/"),
        ("get", f"/api/notifications/{notice.pk}/"),
        ("post", f"/api/notifications/{notice.pk}/acknowledge/"),
        ("get", "/api/releases/latest/"),
        ("get", f"/api/releases/{release.pk}/"),
    )


def test_all_endpoints_require_authentication(api_client, notice, release):
    for method, url in endpoints(notice, release):
        response = getattr(api_client, method)(url)
        assert response.status_code == 403
    assert not NotificationRead.objects.exists()


def test_inactive_account_cannot_use_endpoints(consumer, user, notice, release):
    user.is_active = False
    for method, url in endpoints(notice, release):
        assert getattr(consumer, method)(url).status_code == 403
    assert not NotificationRead.objects.exists()


def test_list_and_detail_contract_and_gets_have_no_read_side_effects(consumer, notice):
    listed = consumer.get("/api/notifications/").json()
    assert len(listed) == 1
    assert listed[0] == {
        "id": notice.pk,
        "release_id": notice.release_id,
        "language": "en",
        "title": notice.title,
        "abstract": notice.abstract,
        "publish_at": notice.publish_at.isoformat().replace("+00:00", "Z"),
        "expires_at": None,
        "is_read": False,
    }
    response = consumer.get(f"/api/notifications/{notice.pk}/")
    assert response.json() == {**listed[0], "body": notice.body}
    assert not NotificationRead.objects.exists()
    assert "private" in response["Cache-Control"]
    assert "no-store" in response["Cache-Control"]
    assert {"Cookie", "Authorization", "Accept-Language"} <= set(
        response["Vary"].split(", ")
    )


def test_empty_feed_and_no_eligible_release(consumer):
    assert consumer.get("/api/notifications/").json() == []
    assert consumer.get("/api/releases/latest/").status_code == 404


def test_feed_keeps_read_items_excludes_dismissed_and_orders_by_publication(
    consumer, notice, audience, user
):
    older = Notification.objects.create(
        title="Older",
        body="Notes",
        status=NotificationStatus.PUBLISHED,
        publish_at=notice.publish_at - timedelta(hours=1),
    )
    older.audience.add(audience)
    NotificationRead.objects.create(
        notification=notice, user=user, read_at=timezone.now()
    )
    assert [row["id"] for row in consumer.get("/api/notifications/").json()] == [
        notice.pk,
        older.pk,
    ]
    assert consumer.get("/api/notifications/").json()[0]["is_read"] is True
    NotificationRead.objects.create(
        notification=older, user=user, read_at=timezone.now(), dismissed=True
    )
    # Query parameters must not expose internal selector options.
    data = consumer.get("/api/notifications/?include_dismissed=true&user=999").json()
    assert [row["id"] for row in data] == [notice.pk]
    assert consumer.get(f"/api/notifications/{older.pk}/").status_code == 404


@pytest.mark.parametrize(
    "condition",
    [
        "no_audience",
        "wrong_group",
        "draft",
        "scheduled",
        "expired",
        "inactive",
        "future",
        "elapsed",
        "release_draft",
        "release_inactive",
    ],
)
def test_hidden_notifications_are_unavailable_on_all_notification_routes(
    consumer, notice, condition
):
    if condition == "no_audience":
        notice.audience.clear()
    elif condition == "wrong_group":
        notice.audience.set([Group.objects.create(name="Other readers")])
    elif condition in ("draft", "scheduled", "expired"):
        notice.status = condition
    elif condition == "inactive":
        notice.is_active = False
    elif condition == "future":
        notice.publish_at = timezone.now() + timedelta(hours=1)
    elif condition == "elapsed":
        notice.expires_at = timezone.now() - timedelta(seconds=1)
    else:
        if condition == "release_draft":
            notice.release.status = ReleaseStatus.DRAFT
        else:
            notice.release.is_active = False
        notice.release.save()
    notice.save()
    assert consumer.get("/api/notifications/").json() == []
    assert consumer.get(f"/api/notifications/{notice.pk}/").status_code == 404
    assert (
        consumer.post(
            f"/api/notifications/{notice.pk}/acknowledge/",
            {"action": "read"},
            format="json",
        ).status_code
        == 404
    )
    assert not NotificationRead.objects.exists()


def test_superuser_still_requires_matching_audience(api_client, admin, notice, release):
    api_client.force_authenticate(admin)
    assert api_client.get("/api/notifications/").json() == []
    assert api_client.get(f"/api/releases/{release.pk}/").status_code == 404
    assert (
        api_client.post(
            f"/api/notifications/{notice.pk}/acknowledge/",
            {"action": "read"},
            format="json",
        ).status_code
        == 404
    )


def test_language_selection_and_whole_message_fallback(consumer, notice, release):
    NotificationTranslation.objects.create(
        notification=notice,
        language="fr",
        title="Mise a jour",
        abstract="Resume",
        label="<p>Details</p>",
    )
    ReleaseTranslation.objects.create(
        release=release, language="fr", title="Version", label="<p>Nouveautes</p>"
    )
    for url in (
        "/api/notifications/",
        f"/api/notifications/{notice.pk}/",
        "/api/releases/latest/",
        f"/api/releases/{release.pk}/",
    ):
        response = consumer.get(url, {"lang": "fr-CA"})
        content = (
            response.json()[0] if url == "/api/notifications/" else response.json()
        )
        assert content["language"] == "fr"
        assert content["title"] in ("Mise a jour", "Version")
        assert "translations" not in content
        fallback = consumer.get(url, {"lang": "es"}).json()
        fallback = fallback[0] if isinstance(fallback, list) else fallback
        assert fallback["language"] == "en"
    assert not NotificationRead.objects.exists()


def test_incomplete_translation_does_not_mix_languages(consumer, notice):
    NotificationTranslation.objects.create(
        notification=notice, language="fr", title="Titre", label="", abstract="Resume"
    )
    content = consumer.get(f"/api/notifications/{notice.pk}/?lang=fr").json()
    assert content["language"] == "en"
    assert content["title"] == notice.title
    assert content["abstract"] == notice.abstract
    assert content["body"] == notice.body


def test_header_language_used_when_query_language_absent(consumer, notice):
    NotificationTranslation.objects.create(
        notification=notice, language="fr", title="Titre", label="Texte"
    )
    assert (
        consumer.get(
            f"/api/notifications/{notice.pk}/", HTTP_ACCEPT_LANGUAGE="fr"
        ).json()["language"]
        == "fr"
    )


@pytest.mark.parametrize("translated", [False, True])
def test_html_is_sanitized_without_changing_saved_content(
    consumer, notice, release, translated
):
    raw = '<p onclick="bad()">Notes <strong>bold</strong></p><script>alert(1)</script><img src=x onerror="bad()"><a href="javascript:bad()">unsafe</a><a href="https://example.org" title="Docs">safe</a><iframe src="https://example.org"></iframe><p style="color:red">End</p>'
    if translated:
        message = NotificationTranslation.objects.create(
            notification=notice, language="fr", title="Titre", label=raw
        )
        notes = ReleaseTranslation.objects.create(
            release=release, language="fr", title="Version", label=raw
        )
    else:
        notice.body = release.body = raw
        notice.save()
        release.save()
        message, notes = notice, release
    for url in (f"/api/notifications/{notice.pk}/", f"/api/releases/{release.pk}/"):
        body = consumer.get(url, {"lang": "fr" if translated else "en"}).json()["body"]
        for unsafe in (
            "<script",
            "<iframe",
            "<img",
            "onclick",
            "onerror",
            "javascript:",
            "style=",
        ):
            assert unsafe not in body
        assert "<strong>bold</strong>" in body
        assert 'href="https://example.org"' in body
    for instance in (message, notes):
        instance.refresh_from_db()
        assert getattr(instance, "label" if translated else "body") == raw


def test_read_dismiss_retries_and_cross_device_reconciliation(consumer, notice, user):
    url = f"/api/notifications/{notice.pk}/acknowledge/"
    first = consumer.post(url, {"action": "read"}, format="json")
    assert first.status_code == 200
    assert first.json()["id"] == notice.pk
    assert first.json()["state"] == "read"
    assert first.json()["read_at"] is not None
    assert first.json()["dismissed"] is False
    assert consumer.post(url, {"action": "read"}, format="json").json() == first.json()
    device = APIClient()
    device.force_login(user)
    assert device.get("/api/notifications/").json()[0]["is_read"] is True
    dismissed = device.post(url, {"action": "dismiss"}, format="json")
    assert dismissed.status_code == 200
    assert dismissed.json()["state"] == "dismissed"
    assert dismissed.json()["read_at"] == first.json()["read_at"]
    assert (
        consumer.post(url, {"action": "dismiss"}, format="json").json()
        == dismissed.json()
    )
    assert (
        consumer.post(url, {"action": "read"}, format="json").json() == dismissed.json()
    )
    assert consumer.get("/api/notifications/").json() == []
    assert NotificationRead.objects.filter(notification=notice, user=user).count() == 1


def test_action_on_old_id_does_not_read_new_notification(
    consumer, notice, audience, user
):
    newer = Notification.objects.create(
        title="New", body="Notes", status=NotificationStatus.PUBLISHED
    )
    newer.audience.add(audience)
    consumer.post(
        f"/api/notifications/{notice.pk}/acknowledge/",
        {"action": "read"},
        format="json",
    )
    assert not NotificationRead.objects.filter(notification=newer, user=user).exists()
    assert consumer.get("/api/notifications/").json()[0]["is_read"] is False


def test_account_switch_and_logout_do_not_leak_state(
    consumer, user, admin, audience, notice
):
    consumer.post(
        f"/api/notifications/{notice.pk}/acknowledge/",
        {"action": "dismiss"},
        format="json",
    )
    admin.groups.add(audience)
    consumer.force_authenticate(admin)
    assert consumer.get("/api/notifications/").json()[0]["is_read"] is False
    assert not NotificationRead.objects.filter(user=admin).exists()
    consumer.force_authenticate(user=None)
    assert consumer.get("/api/notifications/").status_code == 403


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"action": "clear"},
        {"action": "READ"},
        {"action": None},
        {"action": ""},
        {"action": "read", "user": 999},
        {"action": "read", "notification_id": 999},
        [],
        "read",
    ],
)
def test_bad_actions_and_owner_injection_rejected_without_writes(
    consumer, notice, payload
):
    response = consumer.post(
        f"/api/notifications/{notice.pk}/acknowledge/", payload, format="json"
    )
    assert response.status_code == 400
    assert not NotificationRead.objects.exists()


def test_missing_ids_return_404(consumer):
    assert consumer.get("/api/notifications/999999/").status_code == 404
    assert consumer.get("/api/releases/999999/").status_code == 404
    assert (
        consumer.post(
            "/api/notifications/999999/acknowledge/",
            {"action": "dismiss"},
            format="json",
        ).status_code
        == 404
    )


@pytest.mark.parametrize(
    "condition", ["draft", "inactive", "future", "missing_date", "no_audience"]
)
def test_unavailable_release_cannot_be_retrieved(consumer, notice, release, condition):
    if condition == "draft":
        release.status = ReleaseStatus.DRAFT
    elif condition == "inactive":
        release.is_active = False
    elif condition == "future":
        release.published_at = timezone.now() + timedelta(hours=1)
    elif condition == "missing_date":
        release.published_at = None
    else:
        notice.audience.clear()
    release.save()
    assert consumer.get(f"/api/releases/{release.pk}/").status_code == 404
    assert consumer.get("/api/releases/latest/").status_code == 404


def test_standalone_notification_has_no_release_link(consumer, notice):
    notice.release = None
    notice.save()
    content = consumer.get(f"/api/notifications/{notice.pk}/").json()
    assert content["release_id"] is None
    assert consumer.get("/api/releases/latest/").status_code == 404


def test_existing_token_authentication_uses_token_owner(user, notice):
    token = Token.objects.create(user=user)
    client = APIClient(enforce_csrf_checks=True)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    response = client.post(
        f"/api/notifications/{notice.pk}/acknowledge/",
        {"action": "read"},
        format="json",
    )
    assert response.status_code == 200
    assert NotificationRead.objects.get(notification=notice).user == user


def test_latest_release_uses_only_eligible_published_notes(
    consumer, notice, release, audience
):
    # A newer publication for another audience must not become this user's latest.
    hidden = Release.objects.create(
        business_version="9.0.0",
        title="Hidden",
        body="Notes",
        status=ReleaseStatus.PUBLISHED,
        published_at=timezone.now(),
    )
    Notification.objects.create(
        release=hidden,
        title="Hidden",
        body="Notes",
        status=NotificationStatus.PUBLISHED,
    )
    result = consumer.get("/api/releases/latest/").json()
    assert result["id"] == release.pk
    assert result["business_version"] == "2.1.0"
    assert result["released_at"] and result["published_at"]
    assert "github_release_id" not in result
    assert consumer.get(f"/api/releases/{hidden.pk}/").status_code == 404
    latest = Release.objects.create(
        business_version="2.2.0",
        title="Latest",
        body="Notes",
        status=ReleaseStatus.PUBLISHED,
        published_at=timezone.now(),
    )
    n = Notification.objects.create(release=latest, title="Latest", body="Notes")
    n.audience.add(audience)
    assert consumer.get("/api/releases/latest/").json()["id"] == latest.pk


@pytest.mark.parametrize("condition", ["dismissed", "expired", "inactive"])
def test_release_notes_remain_accessible_after_message_hidden(
    consumer, notice, release, user, condition
):
    if condition == "dismissed":
        NotificationRead.objects.create(
            notification=notice, user=user, read_at=timezone.now(), dismissed=True
        )
    elif condition == "expired":
        notice.status = NotificationStatus.EXPIRED
    else:
        notice.is_active = False
    notice.save()
    assert consumer.get(f"/api/notifications/{notice.pk}/").status_code == 404
    assert consumer.get(f"/api/releases/{release.pk}/").status_code == 200
    assert consumer.get("/api/releases/latest/").json()["id"] == release.pk


def test_session_acknowledgement_requires_csrf(user, notice):
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(user)
    url = f"/api/notifications/{notice.pk}/acknowledge/"
    assert client.get("/api/notifications/").status_code == 200
    assert client.post(url, {"action": "read"}, format="json").status_code == 403
    assert not NotificationRead.objects.exists()
    token = get_token(RequestFactory().get("/"))
    client.cookies[settings.CSRF_COOKIE_NAME] = token
    response = client.post(
        url, {"action": "read"}, format="json", HTTP_X_CSRFTOKEN=token
    )
    assert response.status_code == 200


def test_unsupported_methods_cannot_modify_content(consumer, notice, release):
    for method, url in (
        ("post", "/api/notifications/"),
        ("patch", f"/api/notifications/{notice.pk}/"),
        ("delete", f"/api/releases/{release.pk}/"),
        ("get", f"/api/notifications/{notice.pk}/acknowledge/"),
    ):
        assert getattr(consumer, method)(url).status_code == 405
    assert not NotificationRead.objects.exists()


def test_api_schema_documents_consumer_contract():
    schema = SchemaGenerator(
        patterns=[path("api/", include("notifications.urls"))]
    ).get_schema(public=True)
    assert len(schema["paths"]) == 5
    assert "post" in schema["paths"]["/api/notifications/{id}/acknowledge/"]
    assert "body" in schema["components"]["schemas"]["NotificationDetail"]["properties"]
    assert (
        "body" not in schema["components"]["schemas"]["NotificationList"]["properties"]
    )
