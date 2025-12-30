from django.db import models


class StatusType(models.TextChoices):
    PENDING = "PENDING", "Pending"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
