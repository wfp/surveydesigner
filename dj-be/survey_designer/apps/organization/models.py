from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models

from survey_designer.apps.core.models import (
    SoftDeleteMixin,
    TimestampMixin,
    UserTrackingMixin,
)


class OrganizationQuerySet(models.QuerySet):
    def visible_for_user(self, user):
        if user.is_global_admins_member or user.is_superuser:
            return self
        return self.filter(id=user.organization_id)


class Organization(UserTrackingMixin, TimestampMixin, SoftDeleteMixin, models.Model):
    name = models.CharField(max_length=120, unique=True)
    allowed_domains = ArrayField(
        base_field=models.CharField(max_length=30, blank=True),
        blank=True,
        default=list,
        help_text=(
            "The domains must be added with comma separator e.g `firstone.com,secondone.com`. Do not include `@`!"
        ),
    )
    objects = OrganizationQuerySet.as_manager()

    def _validate_allowed_domains(self):
        """
        Validate if allowed_domains are unique over all organizations
        """
        if Organization.objects.filter(
            allowed_domains__overlap=self.allowed_domains
        ).exists():
            raise ValidationError(
                {
                    "allowed_domains": (
                        "One of listed domains is already assigned to other organization. "
                        "Domains should be unique across all organizations."
                    )
                }
            )

    def validate_unique(self, *args, **kwargs):
        self._validate_allowed_domains()
        super().validate_unique(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @staticmethod
    def get_organization_by_email(email: str):
        domain = email.split("@")[-1]
        return Organization.objects.filter(allowed_domains__contains=[domain]).first()
