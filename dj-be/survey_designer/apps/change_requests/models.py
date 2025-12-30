from core.models import OrganizationsModelMixin, TimestampMixin, UserTrackingMixin
from django.db import models

from .const import StatusType


class ChangeRequest(
    UserTrackingMixin, TimestampMixin, OrganizationsModelMixin, models.Model
):
    file = models.FileField(help_text=".xlsx file")
    status = models.CharField(
        max_length=255, choices=StatusType.choices, default=StatusType.PENDING
    )
    description = models.TextField()
    response = models.TextField(blank=True)

    def __str__(self):
        return f"Change Request [{self.id}]"

    class Meta:
        app_label = "change_requests"

    @property
    def is_approved(self):
        return self.status == StatusType.APPROVED

    @property
    def is_rejected(self):
        return self.status == StatusType.REJECTED

    @property
    def can_be_approved(self):
        return self.status in (StatusType.PENDING, StatusType.IN_PROGRESS)

    def user_can_approve(self, user):
        if user.is_global_admins_member or user.is_superuser:
            return True

        if self.organizations.count() != 1:
            return False
        return user.organization == self.organizations.first()
