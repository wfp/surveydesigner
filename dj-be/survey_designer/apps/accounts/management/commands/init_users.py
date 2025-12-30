from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

USERS = [
    {
        "is_superuser": True,
        "email": "me@me",
        "is_staff": True,
        "is_active": True,
        "password": "123",
    },
    {
        "is_superuser": False,
        "email": "user@wfp.org",
        "is_staff": False,
        "is_active": True,
        "password": "123",
    },
    {
        "is_superuser": True,
        "email": "admin@wfp.org",
        "is_staff": True,
        "is_active": True,
        "password": "123",
    },
]


User = get_user_model()


class Command(BaseCommand):
    """
    Initialize users
    """

    @transaction.atomic
    def _init_users(self):
        if User.objects.exists():
            self.stdout.write(self.style.WARNING("Users already initialized"))
            return
        for user in USERS:
            password = user.pop("password")
            newuser = User.objects.create(**user)
            newuser.set_password(password)
            newuser.save()
        self.stdout.write(self.style.SUCCESS("%d users inserted" % len(USERS)))

    def handle(self, *args, **options):
        self._init_users()
