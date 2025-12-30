from core.models import TimestampMixin, UserTrackingMixin
from django.db import models


class Document(TimestampMixin, UserTrackingMixin):
    FILE_TYPE_CHOICES = (
        ("doc", "Document"),
        ("xls", "XLS"),
    )

    document = models.FileField()
    type = models.CharField(max_length=255, choices=FILE_TYPE_CHOICES)
