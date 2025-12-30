from core.validators import validate_name
from django.conf import settings
from django.contrib.postgres.fields.citext import CICharField
from django.db import models


class TimestampMixin(models.Model):
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-date_created", "-date_updated"]

    @property
    def created_at(self):
        return self.date_created.isoformat()

    @property
    def updated_at(self):
        return self.date_updated.isoformat()


class SoftDeleteMixin(models.Model):
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class UserTrackingMixin(models.Model):
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="%(app_label)s_%(class)s_created_set",
        null=True,
        blank=True,
    )

    updated_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="%(app_label)s_%(class)s_updated_set",
        null=True,
        blank=True,
    )

    class Meta:
        abstract = True


class BaseWFPModelMixin(UserTrackingMixin, TimestampMixin, SoftDeleteMixin):
    name = CICharField("Name", max_length=255, unique=True, validators=[validate_name])
    description = models.TextField(blank=True)
    label = models.TextField("Label (en)")

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class OrganizationsModelMixin(models.Model):
    organizations = models.ManyToManyField(
        "organization.Organization",
    )

    class Meta:
        abstract = True


class BaseTranslationMixin(UserTrackingMixin, TimestampMixin):
    language = models.CharField(max_length=255, choices=settings.LANGUAGES)
    label = models.TextField()

    class Meta:
        abstract = True


class OrderFieldMixin(models.Model):
    order = models.PositiveIntegerField(default=0, blank=False, null=False)

    def save(self, *args, **kwargs):
        """
        Overrides the save method to automatically assign a unique order value
        to new objects based on the maximum existing order value.
        This is not required in models where the post-save signal handles this
        e.g. BaseQuestion
        """
        if not self.pk:
            existing_max = self.__class__.objects.all().aggregate(models.Max("order"))[
                "order__max"
            ]
            self.order = (existing_max or 0) + 1
        super().save(*args, **kwargs)

    class Meta:
        abstract = True
