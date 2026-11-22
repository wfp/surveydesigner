from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from release_notifications.models import ReleaseEvent, UserReleaseState
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def test_session_actions_require_and_accept_csrf_token(user, release):
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(user)
    response = client.get(reverse("v1:release-current"))
    assert response.status_code == 200
    token = client.cookies["csrftoken"].value
    url = reverse("v1:release-read", kwargs={"release_id": release.id})
    assert client.post(url).status_code == 403
    assert client.post(url, HTTP_X_CSRFTOKEN=token).status_code == 200


@pytest.fixture
def release():
    return ReleaseEvent.objects.create(
        version="12.9.3",
        source_id="BUILD-1234",
        description="Improved survey validation.",
        deployed_at=timezone.now(),
    )


@pytest.mark.parametrize("name", ("release-current", "release-read", "release-clear"))
def test_signed_out_requests_are_rejected(api_client, release, name):
    kwargs = None if name == "release-current" else {"release_id": release.id}
    url = reverse(f"v1:{name}", kwargs=kwargs)
    response = api_client.get(url) if kwargs is None else api_client.post(url)
    assert response.status_code in (401, 403)
    assert not UserReleaseState.objects.exists()


def test_current_release_is_empty_when_none_are_eligible(api_client_authenticated):
    ReleaseEvent.objects.create(
        version="future",
        source_id="future",
        deployed_at=timezone.now() + timedelta(days=1),
    )
    assert api_client_authenticated.get(reverse("v1:release-current")).data == {
        "release": None
    }


def test_current_returns_latest_active_release_without_marking_read(
    api_client_authenticated, release
):
    ReleaseEvent.objects.create(
        version="withdrawn",
        source_id="withdrawn",
        is_active=False,
        deployed_at=timezone.now(),
    )
    response = api_client_authenticated.get(reverse("v1:release-current"))
    assert response.data["release"]["id"] == release.id
    assert response.data["release"]["description"] == release.description
    assert response.data["release"]["state"] == "unread"
    assert "no-store" in response["Cache-Control"]
    assert not UserReleaseState.objects.exists()


def test_read_is_idempotent_and_retains_release(api_client_authenticated, release):
    url = reverse("v1:release-read", kwargs={"release_id": release.id})
    assert api_client_authenticated.post(url).data["release"]["state"] == "read"
    first_read = UserReleaseState.objects.get().read_at
    api_client_authenticated.post(url)
    assert UserReleaseState.objects.get().read_at == first_read
    assert (
        api_client_authenticated.get(reverse("v1:release-current")).data["release"][
            "id"
        ]
        == release.id
    )


def test_clear_is_private_persistent_and_does_not_clear_new_event(
    api_client_authenticated, api_client, user, release
):
    url = reverse("v1:release-clear", kwargs={"release_id": release.id})
    assert api_client_authenticated.post(url).data["release"]["state"] == "cleared"
    cleared_at = UserReleaseState.objects.get().cleared_at
    api_client_authenticated.post(url)
    api_client_authenticated.post(
        reverse("v1:release-read", kwargs={"release_id": release.id})
    )
    assert UserReleaseState.objects.get().cleared_at == cleared_at
    assert (
        api_client_authenticated.get(reverse("v1:release-current")).data["release"][
            "state"
        ]
        == "cleared"
    )
    other = get_user_model().objects.create_user(
        email="other-release@example.com", password="test"
    )
    api_client.force_authenticate(other)
    assert (
        api_client.get(reverse("v1:release-current")).data["release"]["state"]
        == "unread"
    )
    api_client.force_authenticate(user)
    newer = ReleaseEvent.objects.create(
        version="12.9.4", source_id="BUILD-1235", deployed_at=timezone.now()
    )
    response = api_client.get(reverse("v1:release-current"))
    assert response.data["release"]["id"] == newer.id
    assert response.data["release"]["state"] == "unread"


def test_read_of_displayed_event_cannot_mark_new_event_read(
    api_client_authenticated, release
):
    newer = ReleaseEvent.objects.create(
        version="12.9.4", source_id="BUILD-1235", deployed_at=timezone.now()
    )
    api_client_authenticated.post(
        reverse("v1:release-read", kwargs={"release_id": release.id})
    )
    response = api_client_authenticated.get(reverse("v1:release-current"))
    assert response.data["release"]["id"] == newer.id
    assert response.data["release"]["state"] == "unread"


@pytest.mark.parametrize("action", ("read", "clear"))
def test_unavailable_event_cannot_be_changed(api_client_authenticated, release, action):
    release.is_active = False
    release.save()
    response = api_client_authenticated.post(
        reverse(f"v1:release-{action}", kwargs={"release_id": release.id})
    )
    assert response.status_code == 404
    assert not UserReleaseState.objects.exists()
