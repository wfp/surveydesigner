from django.contrib.auth.models import Group, Permission


def test_can_bulk_upload_no_permission(user):
    assert not user.can_bulk_upload


def test_can_bulk_upload_superuser(admin):
    assert admin.can_bulk_upload


def test_can_bulk_upload_bulk_upload_group(user):
    group = Group.objects.get(name="Bulk Upload")
    user.groups.add(group)
    assert user.can_bulk_upload


def test_can_bulk_upload_admins_group_with_permission(user):
    group = Group.objects.get(name="Admins")
    group.permissions.add(Permission.objects.get(codename="can_bulk_upload"))
    user.groups.add(group)
    assert user.can_bulk_upload
