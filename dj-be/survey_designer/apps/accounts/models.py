import base64
import os

from core.models import SoftDeleteMixin, TimestampMixin
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.db.models import Q
from django.utils.functional import cached_property
from organization.models import Organization
from organization.utils import get_organizations

from .const import PermissionGroups, UserAPISiteAPITypes
from .managers import UserManager


class User(SoftDeleteMixin, TimestampMixin, PermissionsMixin, AbstractBaseUser):
    """Custom user model."""

    email = models.EmailField(
        max_length=255,
        unique=True,
        db_collation="case_insensitive",
    )

    organization = models.ForeignKey(
        Organization, on_delete=models.SET_NULL, blank=True, null=True
    )

    is_staff = models.BooleanField(default=True)

    objects = UserManager()

    USERNAME_FIELD = "email"

    def display_name(self) -> str:
        return self.get_short_name()

    def get_full_name(self) -> str:
        return self.email

    def get_short_name(self) -> str:
        return self.email.split("@")[0]

    @property
    def can_bulk_upload(self):
        return (
            self.is_superuser
            or self.groups.filter(
                Q(name="Bulk Upload")
                | Q(name="Admins", permissions__codename="can_bulk_upload")
            ).exists()
        )

    @cached_property
    def can_manage_change_requests(self) -> bool:
        return (
            self.is_superuser
            or self.groups.filter(name=PermissionGroups.CHANGE_REQUESTS).exists()
        )

    @property
    def read_only_member(self) -> bool:
        return self.groups.filter(name="Read Only").exists()

    @property
    def is_admins_member(self) -> bool:
        return self.groups.filter(name="Admins").exists()

    @property
    def is_global_admins_member(self) -> bool:
        return self.groups.filter(name=PermissionGroups.GLOBAL_ADMINS).exists()

    def save(self, *args, **kwargs):
        """
        Modify user input.
        - Make sure the user's email is all lowercase.
        - Assign organization if none assigned
        """
        self.email = self.email.lower()
        if not self.organization:
            self.organization = Organization.get_organization_by_email(self.email)
        super().save(*args, **kwargs)

    def has_perm(self, perm, obj=None):
        if super().has_perm(perm, None) is False:
            return False
        permission_type = perm.split(".")[1].split("_")[0]
        if (
            self.is_superuser
            or (obj and not obj.id)
            or self.is_global_admins_member
            or permission_type
            not in (
                "change",
                "delete",
            )
        ):
            return True
        try:
            obj_organization = get_organizations(obj)
        except NotImplementedError:
            # Object organization check not implemented on this object, so not required.
            return True

        return (
            obj_organization.count() == 1
            and obj_organization.first() == self.organization
        )


class UserAPISite(TimestampMixin):
    api_type = models.CharField(max_length=255, choices=UserAPISiteAPITypes.choices)
    name = models.CharField(max_length=255, unique=True)
    url = models.URLField()

    def __str__(self):
        return self.name

    @property
    def is_ona(self) -> bool:
        return self.api_type == UserAPISiteAPITypes.ONA

    @property
    def is_kobo(self) -> bool:
        return self.api_type == UserAPISiteAPITypes.KOBO

    @property
    def is_moda(self) -> bool:
        """
        Moda deployments currently share the ONA API type but expose a Moda-specific base URL.
        """
        return "moda" in (self.url or "").lower()


class UserAPIKey(TimestampMixin):
    user = models.ForeignKey(User, related_name="api_keys", on_delete=models.CASCADE)
    key = models.TextField()
    name = models.CharField(max_length=255, blank=True, db_collation="case_insensitive")
    salt = models.BinaryField()
    site = models.ForeignKey(
        UserAPISite, on_delete=models.CASCADE, related_name="user_api_keys", null=True
    )

    class Meta:
        unique_together = ("user", "site", "name")

    def _get_fernet(self, salt):
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend(),
        )

        secret_key = base64.urlsafe_b64encode(
            kdf.derive(settings.SECRET_KEY.encode("utf-8"))
        )
        return Fernet(secret_key)

    def set_key(self, raw_key):
        self.salt = base64.b64encode(os.urandom(12))
        f = self._get_fernet(self.salt)
        self.key = f.encrypt(raw_key.encode()).decode()

    def get_key(self):
        if self.key and self.salt:
            if isinstance(self.salt, bytes):
                salt = self.salt
            else:
                salt = self.salt.tobytes()
            f = self._get_fernet(salt)
            return f.decrypt(self.key.encode()).decode()
        return ""

    @property
    def site_url(self) -> str:
        return UserAPISiteAPITypes.get_base_url(self.site)
