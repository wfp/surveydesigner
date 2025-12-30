from django.contrib.auth.models import UserManager as UM
from django.db import models


class UserQuerySet(models.QuerySet):
    def active(self):
        """Return all active users.

        `User` uses soft delete. If the user is not active, they have been
        deleted.
        """
        return self.filter(is_active=True)


class UserManager(UM):
    def _create_user(self, email, password, **extra_fields):
        """Override default `create_user` so `email` is a required field.

        :param email: Email of the user being created.
        :param password: Password of the user being created.
        :return: User object.
        """
        if not email:
            raise ValueError("The given email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def active(self):
        """See :class:`UserQuerySet` :meth:`active`."""
        return self.get_queryset().active()

    def create_user(self, email, password=None, **extra_fields):
        """See :meth:`_create_user`."""
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        """
        Create and return a `User` with superuser powers.
        """
        if password is None:
            raise TypeError("Superusers must have a password.")

        user = self.create_user(email, password, **extra_fields)
        user.is_superuser = True
        user.is_staff = True
        user.save()

        return user

    def get_queryset(self):
        return UserQuerySet(self.model, using=self._db)
