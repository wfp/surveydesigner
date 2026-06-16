import pytest
from accounts.admin import GroupAdmin, UserAdmin
from accounts.const import PermissionGroups
from accounts.models import User
from accounts.tests.factories import UserFactory
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import Group, Permission
from django.contrib.messages.storage.fallback import FallbackStorage
from django.urls import reverse
from organization.models import Organization

from survey_designer.apps.core.tests.utils import MockRequest
from survey_designer.apps.core.utils import get_model_admin_base_url

ROLE_ACTIONS = (
    "assign_admin",
    "assign_global_admin",
    "unassign_admin",
    "unassign_global_admin",
    "assign_read_only",
    "unassign_read_only",
    "assign_notifications",
    "unassign_notifications",
)

ROLE_ACTION_CASES = (
    ("assign_admin", PermissionGroups.ADMINS, False),
    ("assign_global_admin", PermissionGroups.GLOBAL_ADMINS, False),
    ("unassign_admin", PermissionGroups.ADMINS, True),
    ("unassign_global_admin", PermissionGroups.GLOBAL_ADMINS, True),
    ("assign_read_only", PermissionGroups.READ_ONLY, False),
    ("unassign_read_only", PermissionGroups.READ_ONLY, True),
    ("assign_notifications", PermissionGroups.NOTIFICATIONS, False),
    ("unassign_notifications", PermissionGroups.NOTIFICATIONS, True),
)


@pytest.fixture
def admin_site():
    return AdminSite()


@pytest.fixture
def group_admin(admin_site):
    return GroupAdmin(Group, admin_site)


@pytest.fixture
def user_admin(admin_site):
    return UserAdmin(User, admin_site)


def _admin_request(request_factory, user):
    request = request_factory.get(reverse("admin:accounts_user_changelist"))
    request.user = user
    request.session = {}
    request._messages = FallbackStorage(request)
    return request


def _org(name):
    return Organization.objects.create(name=name)


def _user(email, *, organization=None, is_staff=True, is_superuser=False):
    return UserFactory(
        email=email,
        organization=organization,
        is_staff=is_staff,
        is_superuser=is_superuser,
    )


def _add_group(user, group_name):
    user.groups.add(Group.objects.get(name=group_name))


def _grant_change_user(user):
    permission = Permission.objects.get(
        content_type__app_label="accounts",
        content_type__model="user",
        codename="change_user",
    )
    user.user_permissions.add(permission)


def _has_group(user, group_name):
    user.refresh_from_db()
    return user.groups.filter(name=group_name).exists()


def _queryset_ids(queryset):
    return set(queryset.values_list("id", flat=True))


def _fieldset_fields(fieldsets):
    fields = []
    for _, options in fieldsets:
        for field in options.get("fields", ()):
            if isinstance(field, (list, tuple)):
                fields.extend(field)
            else:
                fields.append(field)
    return set(fields)


@pytest.mark.django_db
class TestUserAdmin:
    def test_user_search_view(self, logged_admin_client, admin):
        response = logged_admin_client.get(
            get_model_admin_base_url(User, "_changelist"),
            {"q": admin.email[:5].lower()},
        )
        assert response.status_code == 200
        assert admin.email in response.content.decode()

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

    def test_orgless_standard_user_queryset_only_includes_self(self, user_admin):
        user = _user("orgless-standard@example.com", organization=None)
        other_orgless_user = _user(
            "other-orgless-standard@example.com", organization=None
        )

        qs = user_admin.get_queryset(MockRequest(user=user))

        assert _queryset_ids(qs) == {user.id}
        assert other_orgless_user.id not in _queryset_ids(qs)

    def test_orgless_read_only_user_queryset_only_includes_self(self, user_admin):
        user = _user("orgless-readonly@example.com", organization=None)
        _add_group(user, PermissionGroups.READ_ONLY)
        other_orgless_user = _user(
            "other-orgless-readonly@example.com", organization=None
        )

        qs = user_admin.get_queryset(MockRequest(user=user))

        assert _queryset_ids(qs) == {user.id}
        assert other_orgless_user.id not in _queryset_ids(qs)

    def test_orgless_admin_user_queryset_only_includes_self(self, user_admin):
        user = _user("orgless-admin@example.com", organization=None)
        _add_group(user, PermissionGroups.ADMINS)
        other_orgless_user = _user("other-orgless-admin@example.com", organization=None)

        qs = user_admin.get_queryset(MockRequest(user=user))

        assert _queryset_ids(qs) == {user.id}
        assert other_orgless_user.id not in _queryset_ids(qs)

    def test_orgless_global_admin_queryset_includes_all_users(self, user_admin):
        global_admin = _user("orgless-global@example.com", organization=None)
        _add_group(global_admin, PermissionGroups.GLOBAL_ADMINS)
        other_orgless_user = _user(
            "other-orgless-global@example.com", organization=None
        )
        organized_user = _user(
            "organized-user@example.com",
            organization=_org("Global Admin Visible Organization"),
        )

        qs = user_admin.get_queryset(MockRequest(user=global_admin))

        assert {global_admin.id, other_orgless_user.id, organized_user.id}.issubset(
            _queryset_ids(qs)
        )

    def test_global_admin_has_role_actions_without_change_user_permission(
        self, user_admin, request_factory
    ):
        global_admin = _user("global-no-change@example.com", organization=None)
        _add_group(global_admin, PermissionGroups.ADMINS)
        _add_group(global_admin, PermissionGroups.GLOBAL_ADMINS)
        request = _admin_request(request_factory, global_admin)

        actions = user_admin.get_actions(request)

        assert not user_admin.has_change_permission(request)
        for action_name in ROLE_ACTIONS:
            assert action_name in actions

    def test_mutating_actions_are_manage_roles_gated(self, user_admin):
        for action_name in ROLE_ACTIONS:
            action = getattr(user_admin, action_name)
            assert "manage_roles" in action.allowed_permissions

    def test_get_actions_requires_manage_roles_permission_for_role_actions(
        self, user_admin, request_factory
    ):
        viewer = _user("viewer@example.com", organization=None)
        request = _admin_request(request_factory, viewer)

        actions = user_admin.get_actions(request)

        for action_name in ROLE_ACTIONS:
            assert action_name not in actions
        assert "export_selected_users_to_csv" in actions

    def test_get_actions_allows_change_user_actions_except_global_admin_actions(
        self, user_admin, request_factory
    ):
        requester = _user(
            "same-org-changer@example.com",
            organization=_org("Same Org Changer Organization"),
        )
        _grant_change_user(requester)
        request = _admin_request(request_factory, requester)

        actions = user_admin.get_actions(request)

        assert "assign_admin" in actions
        assert "unassign_admin" in actions
        assert "assign_read_only" in actions
        assert "unassign_read_only" in actions
        assert "assign_notifications" in actions
        assert "unassign_notifications" in actions
        assert "assign_global_admin" not in actions
        assert "unassign_global_admin" not in actions

    def test_change_user_form_excludes_protected_fields_for_same_org_changer(
        self, user_admin, request_factory
    ):
        organization = _org("Role Field Hidden Organization")
        requester = _user(
            "role-field-hidden-requester@example.com",
            organization=organization,
        )
        _grant_change_user(requester)
        target = _user(
            "role-field-hidden-target@example.com", organization=organization
        )
        request = _admin_request(request_factory, requester)

        fieldset_fields = _fieldset_fields(user_admin.get_fieldsets(request, target))
        form = user_admin.get_form(request, obj=target)

        assert set(user_admin.protected_user_management_fields).isdisjoint(
            fieldset_fields
        )
        assert set(user_admin.protected_user_management_fields).isdisjoint(
            form.base_fields
        )
        assert "is_active" in fieldset_fields
        assert "is_active" in form.base_fields

    @pytest.mark.parametrize("actor_kind", ("global_admin", "superuser"))
    def test_change_user_form_keeps_protected_fields_for_privileged_users(
        self, user_admin, request_factory, actor_kind
    ):
        actor = _user(
            f"role-field-{actor_kind}-requester@example.com",
            organization=None,
            is_superuser=actor_kind == "superuser",
        )
        if actor_kind == "global_admin":
            _add_group(actor, PermissionGroups.GLOBAL_ADMINS)
            _grant_change_user(actor)
        target = _user(
            f"role-field-{actor_kind}-target@example.com",
            organization=_org(f"Role Field {actor_kind} Target Organization"),
        )
        request = _admin_request(request_factory, actor)

        fieldset_fields = _fieldset_fields(user_admin.get_fieldsets(request, target))
        form = user_admin.get_form(request, obj=target)

        assert set(user_admin.protected_user_management_fields).issubset(
            fieldset_fields
        )
        assert set(user_admin.protected_user_management_fields).issubset(
            form.base_fields
        )

    def test_change_user_form_ignores_posted_protected_fields_for_same_org_changer(
        self, user_admin, request_factory
    ):
        organization = _org("Role Field Posted Organization")
        other_organization = _org("Role Field Posted Other Organization")
        requester = _user(
            "role-field-posted-requester@example.com",
            organization=organization,
        )
        _grant_change_user(requester)
        target = _user(
            "role-field-posted-target@example.com",
            organization=organization,
            is_staff=False,
        )
        request = _admin_request(request_factory, requester)
        change_user_permission = Permission.objects.get(
            content_type__app_label="accounts",
            content_type__model="user",
            codename="change_user",
        )
        global_admin_group = Group.objects.get(name=PermissionGroups.GLOBAL_ADMINS)
        form_class = user_admin.get_form(request, obj=target)

        form = form_class(
            data={
                "email": target.email,
                "password": target.password,
                "organization": other_organization.pk,
                "is_active": "on",
                "is_staff": "on",
                "is_superuser": "on",
                "groups": [global_admin_group.pk],
                "user_permissions": [change_user_permission.pk],
            },
            instance=target,
        )

        assert form.is_valid(), form.errors
        saved_user = form.save(commit=False)
        user_admin.save_model(request, saved_user, form, change=True)
        user_admin.save_related(request, form, [], change=True)

        target.refresh_from_db()
        assert not target.is_staff
        assert not target.is_superuser
        assert target.organization == organization
        assert not target.groups.filter(pk=global_admin_group.pk).exists()
        assert not target.user_permissions.filter(pk=change_user_permission.pk).exists()

    @pytest.mark.parametrize(
        "action_name, group_name, starts_with_group", ROLE_ACTION_CASES
    )
    def test_orgless_admin_cannot_mutate_other_orgless_user_roles(
        self, user_admin, request_factory, action_name, group_name, starts_with_group
    ):
        requester = _user("orgless-role-admin@example.com", organization=None)
        _add_group(requester, PermissionGroups.ADMINS)
        target = _user(f"target-{action_name}@example.com", organization=None)
        if starts_with_group:
            _add_group(target, group_name)
        request = _admin_request(request_factory, requester)

        getattr(user_admin, action_name)(request, User.objects.filter(pk=target.pk))

        assert _has_group(target, group_name) is starts_with_group

    def test_direct_role_action_requires_change_user_permission_for_same_org(
        self, user_admin, request_factory
    ):
        organization = _org("Direct Role Permission Organization")
        requester = _user("same-org-admin@example.com", organization=organization)
        _add_group(requester, PermissionGroups.ADMINS)
        target = _user("same-org-target@example.com", organization=organization)
        request = _admin_request(request_factory, requester)

        user_admin.assign_read_only(request, User.objects.filter(pk=target.pk))

        assert not _has_group(target, PermissionGroups.READ_ONLY)

    def test_same_org_change_user_can_only_mutate_same_explicit_organization(
        self, user_admin, request_factory
    ):
        organization = _org("Allowed Change Organization")
        other_organization = _org("Denied Change Organization")
        requester = _user("explicit-org-changer@example.com", organization=organization)
        _grant_change_user(requester)
        same_org_target = _user(
            "same-org-allowed@example.com", organization=organization
        )
        other_org_target = _user(
            "other-org-denied@example.com", organization=other_organization
        )
        orgless_target = _user("orgless-denied@example.com", organization=None)
        request = _admin_request(request_factory, requester)

        user_admin.assign_notifications(
            request,
            User.objects.filter(
                pk__in=[same_org_target.pk, other_org_target.pk, orgless_target.pk]
            ),
        )

        assert _has_group(same_org_target, PermissionGroups.NOTIFICATIONS)
        assert not _has_group(other_org_target, PermissionGroups.NOTIFICATIONS)
        assert not _has_group(orgless_target, PermissionGroups.NOTIFICATIONS)

    @pytest.mark.parametrize("actor_kind", ("global_admin", "superuser"))
    @pytest.mark.parametrize(
        "action_name, group_name, starts_with_group", ROLE_ACTION_CASES
    )
    def test_global_admin_and_superuser_can_mutate_roles_across_organizations(
        self,
        user_admin,
        request_factory,
        actor_kind,
        action_name,
        group_name,
        starts_with_group,
    ):
        organization = _org(f"{actor_kind} Role Organization {action_name}")
        other_organization = _org(f"{actor_kind} Other Role Organization {action_name}")
        actor = _user(
            f"{actor_kind}-{action_name}@example.com",
            organization=None,
            is_superuser=actor_kind == "superuser",
        )
        if actor_kind == "global_admin":
            _add_group(actor, PermissionGroups.GLOBAL_ADMINS)
        targets = [
            _user(
                f"{actor_kind}-{action_name}-same@example.com",
                organization=organization,
            ),
            _user(
                f"{actor_kind}-{action_name}-other@example.com",
                organization=other_organization,
            ),
            _user(
                f"{actor_kind}-{action_name}-orgless@example.com",
                organization=None,
            ),
        ]
        if starts_with_group:
            for target in targets:
                _add_group(target, group_name)
        request = _admin_request(request_factory, actor)

        getattr(user_admin, action_name)(
            request, User.objects.filter(pk__in=[target.pk for target in targets])
        )

        for target in targets:
            assert _has_group(target, group_name) is not starts_with_group

    def test_assign_admin(self, user_admin, request_factory):
        user = _user("assign-admin-target@example.com")
        actor = _user("assign-admin-superuser@example.com", is_superuser=True)
        request = _admin_request(request_factory, actor)

        user_admin.assign_admin(request, User.objects.filter(pk=user.pk))

        assert _has_group(user, PermissionGroups.ADMINS)
        user.refresh_from_db()
        assert user.is_staff

    def test_assign_global_admin(self, user_admin, request_factory):
        user = _user("assign-global-target@example.com")
        actor = _user("assign-global-superuser@example.com", is_superuser=True)
        request = _admin_request(request_factory, actor)

        user_admin.assign_global_admin(request, User.objects.filter(pk=user.pk))

        assert _has_group(user, PermissionGroups.GLOBAL_ADMINS)
        user.refresh_from_db()
        assert user.is_staff

    def test_unassign_admin(self, user_admin, request_factory):
        user = _user("unassign-admin-target@example.com", is_staff=True)
        _add_group(user, PermissionGroups.ADMINS)
        actor = _user("unassign-admin-superuser@example.com", is_superuser=True)
        request = _admin_request(request_factory, actor)

        user_admin.unassign_admin(request, User.objects.filter(pk=user.pk))

        assert not _has_group(user, PermissionGroups.ADMINS)

    def test_unassign_global_admin(self, user_admin, request_factory):
        user = _user("unassign-global-target@example.com", is_staff=True)
        _add_group(user, PermissionGroups.GLOBAL_ADMINS)
        actor = _user("unassign-global-superuser@example.com", is_superuser=True)
        request = _admin_request(request_factory, actor)

        user_admin.unassign_global_admin(request, User.objects.filter(pk=user.pk))

        assert not _has_group(user, PermissionGroups.GLOBAL_ADMINS)

    def test_assign_read_only(self, user_admin, request_factory):
        user = _user("assign-readonly-target@example.com")
        actor = _user("assign-readonly-superuser@example.com", is_superuser=True)
        request = _admin_request(request_factory, actor)

        user_admin.assign_read_only(request, User.objects.filter(pk=user.pk))

        assert _has_group(user, PermissionGroups.READ_ONLY)

    def test_unassign_read_only(self, user_admin, request_factory):
        user = _user("unassign-readonly-target@example.com")
        _add_group(user, PermissionGroups.READ_ONLY)
        actor = _user("unassign-readonly-superuser@example.com", is_superuser=True)
        request = _admin_request(request_factory, actor)

        user_admin.unassign_read_only(request, User.objects.filter(pk=user.pk))

        assert not _has_group(user, PermissionGroups.READ_ONLY)

    def test_assign_notifications(self, user_admin, request_factory):
        user = _user("assign-notifications-target@example.com")
        actor = _user("assign-notifications-superuser@example.com", is_superuser=True)
        request = _admin_request(request_factory, actor)

        user_admin.assign_notifications(request, User.objects.filter(pk=user.pk))

        assert _has_group(user, PermissionGroups.NOTIFICATIONS)

    def test_unassign_notifications(self, user_admin, request_factory):
        user = _user("unassign-notifications-target@example.com")
        _add_group(user, PermissionGroups.NOTIFICATIONS)
        actor = _user("unassign-notifications-superuser@example.com", is_superuser=True)
        request = _admin_request(request_factory, actor)

        user_admin.unassign_notifications(request, User.objects.filter(pk=user.pk))

        assert not _has_group(user, PermissionGroups.NOTIFICATIONS)
