import csv

from accounts.const import PermissionGroups
from accounts.models import User, UserAPIKey, UserAPISite
from admin_auto_filters.filters import AutocompleteFilter
from core.admin import CollationSafeSearchAdminMixin
from core.permissions import AdminPermissions, ReadOnlyPermissions
from django.contrib import admin, messages
from django.contrib.admin.models import LogEntry
from django.contrib.auth.admin import (
    GroupAdmin as BaseGroupAdmin,
    UserAdmin as BaseUserAdmin,
)
from django.contrib.auth.models import Group
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _


@admin.register(User)
class UserAdmin(CollationSafeSearchAdminMixin, BaseUserAdmin):
    role_management_fields = (
        "is_staff",
        "is_superuser",
        "groups",
        "user_permissions",
    )
    protected_user_management_fields = role_management_fields + ("organization",)
    readonly_fields = (
        "last_login",
        "date_updated",
        "date_created",
    )
    fieldsets = (
        (None, {"fields": ("email", "password", "organization")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            _("Important dates"),
            {
                "fields": (
                    "last_login",
                    "date_updated",
                    "date_created",
                )
            },
        ),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),
    )
    list_display = (
        "email",
        "organization",
        "is_superuser",
        "is_staff",
        "groups_display",
        "is_active",
        "last_login",
    )
    list_filter = (
        "organization",
        "is_staff",
        "is_superuser",
        "is_active",
        "groups",
        "date_created",
        "last_login",
    )
    list_select_related = ("organization",)
    search_fields = (
        "id",
        "email",
    )
    ordering = ("date_created",)
    date_hierarchy = "date_created"
    filter_horizontal = (
        "groups",
        "user_permissions",
    )
    actions = (
        "assign_admin",
        "assign_global_admin",
        "unassign_admin",
        "unassign_global_admin",
        "assign_read_only",
        "unassign_read_only",
        "assign_notifications",
        "unassign_notifications",
        "export_selected_users_to_csv",
    )

    def _can_edit_protected_user_management_fields(self, request):
        return request.user.is_superuser or request.user.is_global_admins_member

    def _remove_fields(self, fields, field_names):
        filtered_fields = []
        for field in fields:
            if isinstance(field, (list, tuple)):
                nested_fields = tuple(
                    nested_field
                    for nested_field in field
                    if nested_field not in field_names
                )
                if nested_fields:
                    filtered_fields.append(nested_fields)
            elif field not in field_names:
                filtered_fields.append(field)
        return tuple(filtered_fields)

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj is None or self._can_edit_protected_user_management_fields(request):
            return fieldsets

        protected_user_management_fields = set(self.protected_user_management_fields)
        filtered_fieldsets = []
        for name, options in fieldsets:
            options = options.copy()
            options["fields"] = self._remove_fields(
                options.get("fields", ()),
                protected_user_management_fields,
            )
            filtered_fieldsets.append((name, options))
        return tuple(filtered_fieldsets)

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.is_superuser and not request.user.is_global_admins_member:
            actions.pop("assign_global_admin", None)
            actions.pop("unassign_global_admin", None)
        return actions

    def get_queryset(self, request):
        if request.user.is_superuser or request.user.is_global_admins_member:
            qs = super().get_queryset(request)
        elif request.user.organization_id is None:
            qs = super().get_queryset(request).filter(pk=request.user.pk)
        else:
            qs = (
                super()
                .get_queryset(request)
                .filter(organization_id=request.user.organization_id)
            )
        return qs.prefetch_related("groups")

    def _has_change_user_permission(self, request):
        return request.user.has_perm(
            f"{self.opts.app_label}.change_{self.opts.model_name}"
        )

    def has_manage_roles_permission(self, request):
        return (
            request.user.is_superuser
            or request.user.is_global_admins_member
            or self._has_change_user_permission(request)
        )

    def _get_authorized_role_action_queryset(
        self, request, queryset, *, global_admin_action=False
    ):
        selected_count = queryset.count()

        if request.user.is_superuser or request.user.is_global_admins_member:
            authorized_queryset = queryset
        elif global_admin_action or not self._has_change_user_permission(request):
            authorized_queryset = queryset.none()
        elif request.user.organization_id is None:
            authorized_queryset = queryset.filter(pk=request.user.pk)
        else:
            authorized_queryset = queryset.filter(
                organization_id=request.user.organization_id
            )

        if authorized_queryset.count() != selected_count:
            messages.error(
                request,
                "You do not have permission to modify one or more selected users.",
            )

        return authorized_queryset

    @admin.display(description="Groups")
    def groups_display(self, obj):
        if not obj.id:
            return "-"
        groups = [group.name for group in obj.groups.all()]
        return ", ".join(groups)

    @admin.action(description="Assign an admin role", permissions=["manage_roles"])
    def assign_admin(self, request, queryset):
        queryset = self._get_authorized_role_action_queryset(request, queryset)
        if not queryset.exists():
            return
        group = Group.objects.filter(name="Admins").first()

        if group:
            for user in queryset:
                user.is_staff = True
                user.groups.add(group)
                user.save()

            messages.success(request, "Admin role assigned.")
        else:
            messages.error(request, "Admins Group does not exist.")

    @admin.action(description="Assign global admin role", permissions=["manage_roles"])
    def assign_global_admin(self, request, queryset):
        queryset = self._get_authorized_role_action_queryset(
            request, queryset, global_admin_action=True
        )
        if not queryset.exists():
            return
        self.assign_admin(request, queryset)
        group = Group.objects.filter(name=PermissionGroups.GLOBAL_ADMINS).first()

        if group:
            for user in queryset:
                user.is_staff = True
                user.groups.add(group)
                user.save()

            messages.success(request, "Global Admin role assigned.")
        else:
            messages.error(request, "Global Admins Group does not exist.")

    @admin.action(description="Remove an admin role", permissions=["manage_roles"])
    def unassign_admin(self, request, queryset):
        queryset = self._get_authorized_role_action_queryset(request, queryset)
        if not queryset.exists():
            return
        group = Group.objects.filter(name="Admins").first()

        if group:
            for user in queryset:
                user.is_staff = False
                user.groups.remove(group)
                user.save()

            messages.success(request, "Admin role removed.")
        else:
            messages.error(request, "Admins Group does not exist.")

    @admin.action(description="Remove global admin role", permissions=["manage_roles"])
    def unassign_global_admin(self, request, queryset):
        queryset = self._get_authorized_role_action_queryset(
            request, queryset, global_admin_action=True
        )
        if not queryset.exists():
            return
        group = Group.objects.filter(name=PermissionGroups.GLOBAL_ADMINS).first()

        if group:
            for user in queryset:
                user.is_staff = False
                user.groups.remove(group)
                user.save()

            messages.success(request, "Global Admin role removed.")
        else:
            messages.error(request, "Global Admins Group does not exist.")

    @admin.action(description="Add to Read Only group", permissions=["manage_roles"])
    def assign_read_only(self, request, queryset):
        queryset = self._get_authorized_role_action_queryset(request, queryset)
        if not queryset.exists():
            return
        group = Group.objects.filter(name="Read Only").first()

        if group:
            for user in queryset:
                user.is_staff = True
                user.groups.add(group)
                user.save()

            messages.success(request, "Added to Read Only group.")
        else:
            messages.error(request, "Read Only Group does not exist.")

    @admin.action(
        description="Remove from Read Only group.",
        permissions=["manage_roles"],
    )
    def unassign_read_only(self, request, queryset):
        queryset = self._get_authorized_role_action_queryset(request, queryset)
        if not queryset.exists():
            return
        group = Group.objects.filter(name="Read Only").first()

        if group:
            for user in queryset:
                user.is_staff = False
                user.groups.remove(group)
                user.save()

            messages.success(request, "Removed from Read Only group.")
        else:
            messages.error(request, "Read Only Group does not exist.")

    @admin.action(
        description="Add to Notifications group", permissions=["manage_roles"]
    )
    def assign_notifications(self, request, queryset):
        queryset = self._get_authorized_role_action_queryset(request, queryset)
        if not queryset.exists():
            return
        group = Group.objects.filter(name="Notifications").first()

        if group:
            for user in queryset:
                user.groups.add(group)

            messages.success(request, "Added to Notifications group.")
        else:
            messages.error(request, "Notifications Group does not exist.")

    @admin.action(
        description="Remove from Notifications group",
        permissions=["manage_roles"],
    )
    def unassign_notifications(self, request, queryset):
        queryset = self._get_authorized_role_action_queryset(request, queryset)
        if not queryset.exists():
            return
        group = Group.objects.filter(name="Notifications").first()

        if group:
            for user in queryset:
                user.groups.remove(group)

            messages.success(request, "Removed from Notifications group.")
        else:
            messages.error(request, "Notifications Group does not exist.")

    @admin.action(description="Export selected users to CSV")
    def export_selected_users_to_csv(self, request, queryset):
        fieldnames = [
            "id",
            "email",
            "organization",
            "is_staff",
            "is_superuser",
            "is_active",
            "last_login",
            "date_created",
        ]
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=users_export.csv"

        writer = csv.writer(response)
        writer.writerow(fieldnames)

        for user in queryset:
            writer.writerow([getattr(user, field) for field in fieldnames])
        return response


admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin):
    actions = ["update_permissions"]

    group_to_permission_class = {
        "Admins": AdminPermissions,
        "Read Only": ReadOnlyPermissions,
    }

    @admin.action(description="Update group permissions")
    def update_permissions(self, request, queryset):
        for group in queryset:
            permission_cls = self.group_to_permission_class.get(group.name)
            if permission_cls:
                permission_cls().set_permissions(group)

        messages.success(request, "Permissions updated.")


class LogEntryUserFilter(AutocompleteFilter):
    title = "User"
    field_name = "user"
    parameter_name = "user__pk"


@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "user",
        "action_time",
    )
    list_select_related = ("user",)
    list_filter = (
        # LogEntryUserFilter,
        "action_time",
    )

    def has_add_permission(self, request):
        return False

    # def has_delete_permission(self, request, obj=None):
    #     return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(UserAPIKey)
class UserAPIKeyAdmin(admin.ModelAdmin):
    readonly_fields = (
        "user",
        "site",
        "name",
    )
    list_display = (
        "user",
        "site",
        "name",
    )
    list_select_related = ("user", "site")
    list_display_links = None

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or (obj and obj.user.id == request.user.id)

    def get_fieldsets(self, request, obj=None):
        # Excludes the API key from the change view.
        fieldsets = super().get_fieldsets(request, obj=obj)
        fields = fieldsets[0][1]["fields"]
        fields.remove("key")
        fieldsets[0][1]["fields"] = fields
        return fieldsets


@admin.register(UserAPISite)
class UserAPISiteAdmin(admin.ModelAdmin):
    list_display = ["name", "url", "api_type"]
