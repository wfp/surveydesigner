from core.permissions import AdminPermissions, ReadOnlyPermissions
from django.contrib.auth.models import Group
from django.core.management import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "Update group permissions"
    group_to_permission_class = {
        "Admins": AdminPermissions,
        "Read Only": ReadOnlyPermissions,
    }

    def handle(self, *args, **options):
        with transaction.atomic():
            for group in Group.objects.all():
                permission_cls = self.group_to_permission_class.get(group.name)
                if permission_cls:
                    permission_cls().set_permissions(group)
            self.stdout.write(self.style.SUCCESS("Permissions updated."))
