import pytest
from accounts.admin import GroupAdmin, UserAdmin
from accounts.models import User
from accounts.tests.factories import UserFactory
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import Group
from django.contrib.messages.storage.fallback import FallbackStorage
from django.urls import reverse

from survey_designer.apps.core.tests.utils import MockRequest


@pytest.fixture
def admin_site():
    return AdminSite()


@pytest.fixture
def group_admin(admin_site):
    return GroupAdmin(Group, admin_site)


@pytest.fixture
def user_admin(admin_site):
    return UserAdmin(User, admin_site)


@pytest.mark.django_db
class TestUserAdmin:
    def test_admin_queryset(self, user_admin):
        user = UserFactory(is_staff=True)
        qs = user_admin.get_queryset(
            MockRequest(
                user=user,
                headers={"Referer": "/admin/accounts/user/"},
            )
        )
        assert qs.count() == 1
        assert qs.first().id == user.id

    def test_assign_admin(self, user_admin, request_factory):
        user = UserFactory()
        request = request_factory.get(reverse("admin:accounts_user_changelist"))
        setattr(request, "session", "session")
        setattr(request, "_messages", FallbackStorage(request))
        user_admin.assign_admin(request, User.objects.filter(pk=user.pk))
        assert user.is_staff
        assert user.groups.filter(name="Admins").exists()

    def test_assign_global_admin(self, user_admin, request_factory):
        user = UserFactory()
        request = request_factory.get(reverse("admin:accounts_user_changelist"))
        setattr(request, "session", "session")
        setattr(request, "_messages", FallbackStorage(request))
        user_admin.assign_global_admin(request, User.objects.filter(pk=user.pk))
        assert user.is_staff
        assert user.groups.filter(name="Global Admins").exists()

    def test_unassign_admin(self, user_admin, request_factory):
        user = UserFactory(is_staff=True)
        admin_group = Group.objects.get(name="Admins")
        user.groups.add(admin_group)
        request = request_factory.get(reverse("admin:accounts_user_changelist"))
        setattr(request, "session", "session")
        setattr(request, "_messages", FallbackStorage(request))
        user_admin.unassign_admin(request, User.objects.filter(pk=user.pk))
        assert not user.groups.filter(name="Admins").exists()

    def test_unassign_global_admin(self, user_admin, request_factory):
        user = UserFactory(is_staff=True)
        global_admin_group = Group.objects.get(name="Global Admins")
        user.groups.add(global_admin_group)
        request = request_factory.get(reverse("admin:accounts_user_changelist"))
        setattr(request, "session", "session")
        setattr(request, "_messages", FallbackStorage(request))
        user_admin.unassign_global_admin(request, User.objects.filter(pk=user.pk))
        assert not user.groups.filter(name="Global Admins").exists()

    def test_assign_read_only(self, user_admin, request_factory):
        user = UserFactory()
        request = request_factory.get(reverse("admin:accounts_user_changelist"))
        setattr(request, "session", "session")
        setattr(request, "_messages", FallbackStorage(request))
        user_admin.assign_read_only(request, User.objects.filter(pk=user.pk))
        assert user.groups.filter(name="Read Only").exists()

    def test_unassign_read_only(self, user_admin, request_factory):
        user = UserFactory()
        read_only_group = Group.objects.get(name="Read Only")
        user.groups.add(read_only_group)
        request = request_factory.get(reverse("admin:accounts_user_changelist"))
        setattr(request, "session", "session")
        setattr(request, "_messages", FallbackStorage(request))
        user_admin.unassign_read_only(request, User.objects.filter(pk=user.pk))
        assert not user.groups.filter(name="Read Only").exists()

    def test_assign_notifications(self, user_admin, request_factory):
        user = UserFactory()
        request = request_factory.get(reverse("admin:accounts_user_changelist"))
        setattr(request, "session", "session")
        setattr(request, "_messages", FallbackStorage(request))
        user_admin.assign_notifications(request, User.objects.filter(pk=user.pk))
        assert user.groups.filter(name="Notifications").exists()

    def test_unassign_notifications(self, user_admin, request_factory):
        user = UserFactory()
        notifications_group = Group.objects.get(name="Notifications")
        user.groups.add(notifications_group)
        request = request_factory.get(reverse("admin:accounts_user_changelist"))
        setattr(request, "session", "session")
        setattr(request, "_messages", FallbackStorage(request))
        user_admin.unassign_notifications(request, User.objects.filter(pk=user.pk))
        assert not user.groups.filter(name="Notifications").exists()
