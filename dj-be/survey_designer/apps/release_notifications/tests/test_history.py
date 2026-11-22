from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from release_notifications.models import ReleaseEvent, UserReleaseState

pytestmark = pytest.mark.django_db


def make_releases(count):
    now = timezone.now()
    return [
        ReleaseEvent.objects.create(
            version=f"history-{i}",
            source_id=f"HISTORY-{i}",
            deployed_at=now - timedelta(seconds=i),
            description=f"Changes {i}",
        )
        for i in range(count)
    ]


@pytest.mark.parametrize(
    "name", ("release-history", "release-recent", "release-clear-recent")
)
def test_history_endpoints_require_authentication(api_client, name):
    method = api_client.post if name == "release-clear-recent" else api_client.get
    assert method(reverse(f"v1:{name}")).status_code in (401, 403)


def test_recent_retains_read_entries_and_scopes_unread_count(
    api_client_authenticated, user
):
    newest, older = make_releases(2)
    UserReleaseState.objects.create(
        user=user, release_event=older, read_at=timezone.now()
    )
    data = api_client_authenticated.get(reverse("v1:release-recent")).data
    assert [(r["id"], r["state"]) for r in data["results"]] == [
        (newest.id, "unread"),
        (older.id, "read"),
    ]
    assert data["unread_count"] == 1
    api_client_authenticated.post(
        reverse("v1:release-read", kwargs={"release_id": newest.id})
    )
    data = api_client_authenticated.get(reverse("v1:release-recent")).data
    assert len(data["results"]) == 2
    assert all(r["state"] == "read" for r in data["results"])
    assert data["unread_count"] == 0


def test_history_paginates_all_eligible_records_including_cleared(
    api_client_authenticated, user
):
    releases = make_releases(25)
    UserReleaseState.objects.create(
        user=user, release_event=releases[0], cleared_at=timezone.now()
    )
    ReleaseEvent.objects.create(
        version="withdrawn-history",
        source_id="withdrawn-history",
        deployed_at=timezone.now(),
        is_active=False,
    )
    ReleaseEvent.objects.create(
        version="future-history",
        source_id="future-history",
        deployed_at=timezone.now() + timedelta(days=1),
    )
    url = reverse("v1:release-history")
    first = api_client_authenticated.get(url).data
    second = api_client_authenticated.get(url, {"page": 2}).data
    assert first["count"] == 25
    assert len(first["results"]) == 20
    assert len(second["results"]) == 5
    assert first["results"][0]["state"] == "cleared"
    assert first["next"] and second["previous"]
    assert first["unread_count"] == 24
    assert set(r["id"] for r in first["results"]).isdisjoint(
        r["id"] for r in second["results"]
    )
    assert api_client_authenticated.get(url, {"page": 99}).status_code == 404


def test_clear_only_affects_supplied_events_and_keeps_history(
    api_client_authenticated, api_client, user
):
    releases = make_releases(6)
    ids = [r.id for r in releases[:5]]
    clear_url = reverse("v1:release-clear-recent")
    assert (
        api_client_authenticated.post(
            clear_url, {"release_ids": ids}, format="json"
        ).status_code
        == 200
    )
    first_timestamps = list(
        UserReleaseState.objects.values_list("cleared_at", flat=True)
    )
    api_client_authenticated.post(clear_url, {"release_ids": ids}, format="json")
    assert (
        list(UserReleaseState.objects.values_list("cleared_at", flat=True))
        == first_timestamps
    )
    recent = api_client_authenticated.get(reverse("v1:release-recent")).data
    assert recent["results"] == []
    assert recent["unread_count"] == 1
    assert (
        api_client_authenticated.get(reverse("v1:release-history")).data["count"] == 6
    )
    other = get_user_model().objects.create_user(email="history-other@example.com")
    api_client.force_authenticate(other)
    assert len(api_client.get(reverse("v1:release-recent")).data["results"]) == 5
    newer = ReleaseEvent.objects.create(
        version="next-history", source_id="NEXT-HISTORY", deployed_at=timezone.now()
    )
    api_client.force_authenticate(user)
    recent = api_client.get(reverse("v1:release-recent")).data
    assert [(r["id"], r["state"]) for r in recent["results"]] == [(newer.id, "unread")]


@pytest.mark.parametrize(
    "payload",
    ({"release_ids": []}, {"release_ids": [0]}, {"release_ids": [1, 2, 3, 4, 5, 6]}),
)
def test_invalid_clear_payload_is_rejected(api_client_authenticated, payload):
    assert (
        api_client_authenticated.post(
            reverse("v1:release-clear-recent"), payload, format="json"
        ).status_code
        == 400
    )
    assert not UserReleaseState.objects.exists()


def test_missing_event_does_not_partially_clear(api_client_authenticated):
    release = make_releases(1)[0]
    response = api_client_authenticated.post(
        reverse("v1:release-clear-recent"),
        {"release_ids": [release.id, release.id + 1]},
        format="json",
    )
    assert response.status_code == 404
    assert not UserReleaseState.objects.exists()
