from core.models import TimestampMixin, UserTrackingMixin
from django.db import models


class FrontendContent(UserTrackingMixin, TimestampMixin):
    key = models.CharField(max_length=50, unique=True)
    message = models.TextField()
    is_active = models.BooleanField(default=False)
    severity = models.CharField(
        max_length=20,
        choices=[("info", "Info"), ("warning", "Warning"), ("error", "Error")],
        default="info",
    )

    class Meta:
        verbose_name = "Frontend content"
        verbose_name_plural = "Frontend content"

    def __str__(self):
        return self.key
