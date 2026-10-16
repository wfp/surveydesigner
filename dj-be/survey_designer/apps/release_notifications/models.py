from core.models import TimestampMixin
from django.conf import settings
from django.db import models


class ReleaseEvent(TimestampMixin):
    version = models.CharField(max_length=255, unique=True)
    source_id = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, default="")
    deployed_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("-deployed_at", "-id")
        indexes = [
            models.Index(
                fields=("is_active", "-deployed_at"),
                name="release_event_current_idx",
            )
        ]

    def __str__(self):
        return self.version


class UserReleaseState(TimestampMixin):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="release_notification_states",
    )
    release_event = models.ForeignKey(
        ReleaseEvent,
        on_delete=models.CASCADE,
        related_name="user_states",
    )
    read_at = models.DateTimeField(blank=True, null=True)
    cleared_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("user", "release_event"),
                name="unique_user_release_state",
            )
        ]

    @property
    def state(self):
        if self.cleared_at is not None:
            return "cleared"
        if self.read_at is not None:
            return "read"
        return "unread"

    def __str__(self):
        return f"{self.user}: {self.release_event} ({self.state})"
