from datetime import timedelta

import pytest
from django.db import IntegrityError
from django.utils import timezone
from release_notifications.models import ReleaseEvent, UserReleaseState

pytestmark = pytest.mark.django_db


@pytest.fixture
def release_event():
    return ReleaseEvent.objects.create(
        version="12.9.3",
        source_id="BUILD-1234",
        deployed_at=timezone.now(),
    )


def test_release_event_uses_version_as_its_label(release_event):
    assert str(release_event) == "12.9.3"
    assert release_event.is_active is True
    assert release_event.description == ""


def test_release_events_are_ordered_by_latest_deployment(release_event):
    latest_release = ReleaseEvent.objects.create(
        version="12.9.4",
        source_id="BUILD-1235",
        deployed_at=release_event.deployed_at + timedelta(minutes=1),
    )

    assert list(ReleaseEvent.objects.all()) == [latest_release, release_event]


def test_user_release_state_is_unread_by_default(user, release_event):
    user_state = UserReleaseState.objects.create(
        user=user,
        release_event=release_event,
    )

    assert user_state.state == "unread"


def test_user_release_state_is_read_when_read_at_is_present(user, release_event):
    user_state = UserReleaseState.objects.create(
        user=user,
        release_event=release_event,
        read_at=timezone.now(),
    )

    assert user_state.state == "read"


def test_cleared_state_takes_precedence_over_read(user, release_event):
    now = timezone.now()
    user_state = UserReleaseState.objects.create(
        user=user,
        release_event=release_event,
        read_at=now,
        cleared_at=now,
    )

    assert user_state.state == "cleared"


def test_user_can_have_only_one_state_per_release(user, release_event):
    UserReleaseState.objects.create(user=user, release_event=release_event)

    with pytest.raises(IntegrityError):
        UserReleaseState.objects.create(user=user, release_event=release_event)
