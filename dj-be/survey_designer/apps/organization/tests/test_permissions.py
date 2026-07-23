import pytest
from accounts.const import PermissionGroups
from django.contrib.admin import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.urls import reverse
from modules.admin import (
    ModuleAdmin,
    SubmoduleMappingAdmin,
    SubmoduleMappingSurveyTypeInline,
)
from modules.models import (
    Module,
    Submodule,
    SubmoduleMapping,
    SubmoduleMappingSurveyType,
)
from organization.permissions import can_mutate_object
from questions.admin import RootQuestionAdmin
from questions.models import RootQuestion

pytestmark = pytest.mark.django_db


def _user_with_module_permissions(
    email, *, organization=None, group_name=PermissionGroups.ADMINS, actions=()
):
    user = get_user_model().objects.create_user(
        email=email,
        password="test_user",
        is_staff=True,
        organization=organization,
    )
    group, _ = Group.objects.get_or_create(name=group_name)
    group.permissions.add(
        *Permission.objects.filter(
            content_type__app_label="modules",
            content_type__model="module",
            codename__in=[f"{action}_module" for action in actions],
        )
    )
    user.groups.add(group)
    return user


def _grant_model_permissions(user, model, actions):
    group = user.groups.get(name=PermissionGroups.ADMINS)
    group.permissions.add(
        *Permission.objects.filter(
            content_type__app_label=model._meta.app_label,
            content_type__model=model._meta.model_name,
            codename__in=[f"{action}_{model._meta.model_name}" for action in actions],
        )
    )


@pytest.fixture
def organization_content(organization_1, organization_2):
    own = Module.objects.create(name="OwnModule", label="Own module")
    own.organizations.set([organization_1])
    foreign = Module.objects.create(name="ForeignModule", label="Foreign module")
    foreign.organizations.set([organization_2])
    shared = Module.objects.create(name="SharedModule", label="Shared module")
    shared.organizations.set([organization_1, organization_2])
    unassigned = Module.objects.create(name="UnassignedModule", label="Unassigned")
    return own, foreign, shared, unassigned


def test_assigned_admin_can_only_mutate_exclusively_owned_content(
    organization_1, organization_content, request_factory
):
    user = _user_with_module_permissions(
        "org-admin@example.com",
        organization=organization_1,
        actions=("add", "change", "delete", "view"),
    )
    own, foreign, shared, unassigned = organization_content

    assert can_mutate_object(user, own)
    assert not can_mutate_object(user, foreign)
    assert not can_mutate_object(user, shared)
    assert not can_mutate_object(user, unassigned)

    module_admin = ModuleAdmin(Module, AdminSite())
    request = request_factory.get("/")
    request.user = user
    assert module_admin.has_add_permission(request)
    assert module_admin.has_change_permission(request, own)
    assert module_admin.has_delete_permission(request, own)
    assert not module_admin.has_change_permission(request, foreign)
    assert not module_admin.has_delete_permission(request, shared)


@pytest.mark.parametrize(
    "group_name,organization_fixture",
    [
        (PermissionGroups.READ_ONLY, "organization_1"),
        (PermissionGroups.ADMINS, None),
    ],
)
def test_read_only_and_orgless_users_cannot_mutate_content(
    request, request_factory, group_name, organization_fixture, organization_content
):
    organization = (
        request.getfixturevalue(organization_fixture) if organization_fixture else None
    )
    user = _user_with_module_permissions(
        f"{group_name.lower().replace(' ', '-')}-user@example.com",
        organization=organization,
        group_name=group_name,
        actions=("add", "change", "delete", "view"),
    )

    assert all(not can_mutate_object(user, obj) for obj in organization_content)
    module_admin = ModuleAdmin(Module, AdminSite())
    admin_request = request_factory.get("/")
    admin_request.user = user
    assert not module_admin.has_add_permission(admin_request)
    assert not module_admin.has_change_permission(admin_request)
    assert not module_admin.has_delete_permission(admin_request)


@pytest.mark.parametrize("global_kind", ["global_admin", "superuser"])
def test_global_admins_and_superusers_can_mutate_all_content(
    global_kind, organization_content
):
    if global_kind == "superuser":
        user = get_user_model().objects.create_superuser(
            email="superuser@example.com", password="test_user"
        )
    else:
        user = _user_with_module_permissions(
            "global-admin@example.com",
            group_name=PermissionGroups.GLOBAL_ADMINS,
            actions=("add", "change", "delete", "view"),
        )

    assert all(can_mutate_object(user, obj) for obj in organization_content)


@pytest.mark.parametrize(
    "group_name,assigned",
    [
        (PermissionGroups.ADMINS, True),
        (PermissionGroups.READ_ONLY, True),
        (PermissionGroups.ADMINS, False),
    ],
)
def test_admin_queryset_reads_all_content_for_every_role(
    organization_1, organization_content, request_factory, group_name, assigned
):
    user = _user_with_module_permissions(
        f"reader-{group_name.lower().replace(' ', '-')}-{assigned}@example.com",
        organization=organization_1 if assigned else None,
        group_name=group_name,
        actions=("view",),
    )
    request = request_factory.get(reverse("admin:modules_module_changelist"))
    request.user = user
    queryset = ModuleAdmin(Module, AdminSite()).get_queryset(request)

    assert set(organization_content).issubset(set(queryset))


def test_foreign_admin_change_url_renders_read_only(
    django_client, organization_1, organization_content
):
    user = _user_with_module_permissions(
        "foreign-reader@example.com",
        organization=organization_1,
        actions=("change", "view"),
    )
    foreign = organization_content[1]
    django_client.force_login(user)

    response = django_client.get(
        reverse("admin:modules_module_change", args=[foreign.pk])
    )

    assert response.status_code == 200
    assert response.context["has_change_permission"] is False
    assert b'name="_save"' not in response.content


def test_editable_related_fields_only_accept_mutation_safe_content(
    organization_1, organization_2, request_factory
):
    user = _user_with_module_permissions(
        "related-fields@example.com",
        organization=organization_1,
        actions=("add", "change", "view"),
    )
    own_module = Module.objects.create(name="RelatedOwn", label="Related own")
    own_module.organizations.set([organization_1])
    foreign_module = Module.objects.create(
        name="RelatedForeign", label="Related foreign"
    )
    foreign_module.organizations.set([organization_2])
    shared_module = Module.objects.create(name="RelatedShared", label="Related shared")
    shared_module.organizations.set([organization_1, organization_2])
    own_submodule = Submodule.objects.create(
        module=own_module, name="RelatedOwnSubmodule", label="Related own submodule"
    )
    foreign_submodule = Submodule.objects.create(
        module=foreign_module,
        name="RelatedForeignSubmodule",
        label="Related foreign submodule",
    )
    shared_submodule = Submodule.objects.create(
        module=shared_module,
        name="RelatedSharedSubmodule",
        label="Related shared submodule",
    )
    request = request_factory.get(reverse("admin:questions_rootquestion_add"))
    request.user = user

    form_class = RootQuestionAdmin(RootQuestion, AdminSite()).get_form(request)

    assert set(form_class.base_fields["submodule"].queryset) == {own_submodule}
    assert foreign_submodule not in form_class.base_fields["submodule"].queryset
    assert shared_submodule not in form_class.base_fields["submodule"].queryset


def test_direct_organization_choices_are_forced_to_assigned_organization(
    organization_1, organization_2, request_factory
):
    user = _user_with_module_permissions(
        "organization-field@example.com",
        organization=organization_1,
        actions=("add", "change", "view"),
    )
    request = request_factory.get(reverse("admin:modules_module_add"))
    request.user = user

    form_class = ModuleAdmin(Module, AdminSite()).get_form(request)

    assert list(form_class.base_fields["organizations"].queryset) == [organization_1]
    assert organization_2 not in form_class.base_fields["organizations"].queryset


def test_read_only_export_action_remains_available(organization_1, request_factory):
    user = _user_with_module_permissions(
        "readonly-export@example.com",
        organization=organization_1,
        group_name=PermissionGroups.READ_ONLY,
        actions=("view",),
    )
    request = request_factory.get(reverse("admin:modules_module_changelist"))
    request.user = user

    actions = ModuleAdmin(Module, AdminSite()).get_actions(request)

    assert "export_action" in actions


def test_mapping_and_nested_edits_follow_parent_organization(
    organization_1, organization_2, request_factory
):
    user = _user_with_module_permissions(
        "nested-mapping@example.com",
        organization=organization_1,
        actions=("view",),
    )
    _grant_model_permissions(
        user, SubmoduleMapping, ("add", "change", "delete", "view")
    )
    _grant_model_permissions(
        user, SubmoduleMappingSurveyType, ("add", "change", "delete", "view")
    )

    own_module = Module.objects.create(name="NestedOwn", label="Nested own")
    own_module.organizations.set([organization_1])
    foreign_module = Module.objects.create(name="NestedForeign", label="Nested foreign")
    foreign_module.organizations.set([organization_2])
    own_mapping = SubmoduleMapping.objects.create()
    foreign_mapping = SubmoduleMapping.objects.create()
    Submodule.objects.create(
        module=own_module,
        mapping=own_mapping,
        name="NestedOwnSubmodule",
        label="Nested own submodule",
    )
    Submodule.objects.create(
        module=foreign_module,
        mapping=foreign_mapping,
        name="NestedForeignSubmodule",
        label="Nested foreign submodule",
    )

    request = request_factory.get("/")
    request.user = user
    admin_site = AdminSite()
    mapping_admin = SubmoduleMappingAdmin(SubmoduleMapping, admin_site)
    mapping_inline = SubmoduleMappingSurveyTypeInline(SubmoduleMapping, admin_site)

    assert mapping_admin.has_change_permission(request, own_mapping)
    assert not mapping_admin.has_change_permission(request, foreign_mapping)
    assert mapping_inline.has_change_permission(request, own_mapping)
    assert not mapping_inline.has_change_permission(request, foreign_mapping)
