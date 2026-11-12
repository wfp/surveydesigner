from core.models import (
    BaseTranslationMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UserTrackingMixin,
)
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from .const import NotificationStatus, ReleaseStatus


class Release(UserTrackingMixin, TimestampMixin, SoftDeleteMixin):
    business_version = models.CharField(max_length=255, unique=True)
    github_tag = models.CharField(max_length=255, blank=True)
    github_release_id = models.CharField(max_length=255, blank=True)
    github_url = models.URLField(max_length=2048, blank=True)
    configuration_version = models.CharField(max_length=255, blank=True)
    title = models.TextField()
    body = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=ReleaseStatus.choices, default=ReleaseStatus.DRAFT
    )
    released_at = models.DateTimeField(blank=True, null=True)
    published_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("-published_at", "-id")
        indexes = [
            models.Index(
                fields=("is_active", "status", "-published_at"),
                name="notification_release_idx",
            )
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=ReleaseStatus.values),
                name="notification_release_status_valid",
            )
        ]

    def __str__(self):
        return self.business_version


class ReleaseTranslation(BaseTranslationMixin):
    release = models.ForeignKey(
        Release, on_delete=models.CASCADE, related_name="translations"
    )
    title = models.TextField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("release", "language"),
                name="notification_release_language_unique",
            ),
            models.CheckConstraint(
                condition=~models.Q(language="en"),
                name="notification_release_language_not_en",
            ),
        ]

    def clean(self):
        super().clean()
        if self.language == "en":
            raise ValidationError(
                {"language": "English content is stored on the release."}
            )

    def __str__(self):
        return f"{self.release} ({self.language})"


class Notification(UserTrackingMixin, TimestampMixin, SoftDeleteMixin):
    release = models.OneToOneField(
        Release,
        on_delete=models.PROTECT,
        related_name="notification",
        blank=True,
        null=True,
    )
    title = models.TextField()
    abstract = models.TextField(blank=True)
    body = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=NotificationStatus.choices,
        default=NotificationStatus.DRAFT,
    )
    publish_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(blank=True, null=True)
    audience = models.ManyToManyField(
        "auth.Group",
        through="NotificationAudience",
        related_name="notifications",
        blank=True,
    )

    class Meta:
        ordering = ("-publish_at", "-id")
        indexes = [
            models.Index(
                fields=("is_active", "status", "publish_at"),
                name="notification_feed_idx",
            )
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=NotificationStatus.values),
                name="notification_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(expires_at__isnull=True)
                | models.Q(expires_at__gt=models.F("publish_at")),
                name="notification_expiry_after_publish",
            ),
        ]

    def clean(self):
        super().clean()
        if self.expires_at and self.publish_at and self.expires_at <= self.publish_at:
            raise ValidationError(
                {"expires_at": "Expiry must be after the publication time."}
            )

    def __str__(self):
        return self.title


class NotificationTranslation(BaseTranslationMixin):
    notification = models.ForeignKey(
        Notification, on_delete=models.CASCADE, related_name="translations"
    )
    title = models.TextField()
    abstract = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("notification", "language"),
                name="notification_message_language_unique",
            ),
            models.CheckConstraint(
                condition=~models.Q(language="en"),
                name="notification_message_language_not_en",
            ),
        ]

    def clean(self):
        super().clean()
        if self.language == "en":
            raise ValidationError(
                {"language": "English content is stored on the notification."}
            )

    def __str__(self):
        return f"{self.notification} ({self.language})"


class NotificationAudience(models.Model):
    notification = models.ForeignKey(
        Notification, on_delete=models.CASCADE, related_name="audience_entries"
    )
    group = models.ForeignKey(
        "auth.Group", on_delete=models.CASCADE, related_name="notification_audiences"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("notification", "group"), name="notification_audience_unique"
            )
        ]

    def __str__(self):
        return f"{self.notification}: {self.group}"


class NotificationRead(models.Model):
    notification = models.ForeignKey(
        Notification, on_delete=models.CASCADE, related_name="read_states"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_reads",
    )
    read_at = models.DateTimeField(blank=True, null=True)
    dismissed = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(
                fields=("user", "dismissed"), name="notification_user_state_idx"
            )
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("notification", "user"), name="notification_user_read_unique"
            ),
            models.CheckConstraint(
                condition=models.Q(dismissed=False) | models.Q(read_at__isnull=False),
                name="notification_dismissed_is_read",
            ),
        ]

    def clean(self):
        super().clean()
        if self.dismissed and self.read_at is None:
            raise ValidationError(
                {"read_at": "Dismissed notifications must have a read timestamp."}
            )

    @property
    def state(self):
        if self.dismissed:
            return "dismissed"
        return "read" if self.read_at is not None else "unread"

    def __str__(self):
        return f"{self.user}: {self.notification} ({self.state})"
