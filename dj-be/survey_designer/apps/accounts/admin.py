import csv

from accounts.const import PermissionGroups
from accounts.models import User, UserAPIKey, UserAPISite
from admin_auto_filters.filters import AutocompleteFilter
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
class UserAdmin(BaseUserAdmin):
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

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.is_superuser and not request.user.is_global_admins_member:
            del actions["assign_global_admin"]
            del actions["unassign_global_admin"]
        return actions

    def get_queryset(self, request):
        if request.user.is_superuser or request.user.is_global_admins_member:
            qs = super().get_queryset(request)
        else:
            qs = (
                super()
                .get_queryset(request)
                .filter(organization=request.user.organization_id)
            )
        return qs.prefetch_related("groups")

    @admin.display(description="Groups")
    def groups_display(self, obj):
        if not obj.id:
            return "-"
        groups = [group.name for group in obj.groups.all()]
        return ", ".join(groups)

    @admin.action(description="Assign an admin role")
    def assign_admin(self, request, queryset):
        group = Group.objects.filter(name="Admins").first()

        if group:
            for user in queryset:
                user.is_staff = True
                user.groups.add(group)
                user.save()

            messages.success(request, "Admin role assigned.")
        else:
            messages.error(request, "Admins Group does not exist.")

    @admin.action(description="Assign global admin role")
    def assign_global_admin(self, request, queryset):
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

    @admin.action(description="Remove an admin role")
    def unassign_admin(self, request, queryset):
        group = Group.objects.filter(name="Admins").first()

        if group:
            for user in queryset:
                user.is_staff = False
                user.groups.remove(group)
                user.save()

            messages.success(request, "Admin role removed.")
        else:
            messages.error(request, "Admins Group does not exist.")

    @admin.action(description="Remove global admin role")
    def unassign_global_admin(self, request, queryset):
        group = Group.objects.filter(name=PermissionGroups.GLOBAL_ADMINS).first()

        if group:
            for user in queryset:
                user.is_staff = False
                user.groups.remove(group)
                user.save()

            messages.success(request, "Global Admin role removed.")
        else:
            messages.error(request, "Global Admins Group does not exist.")

    @admin.action(description="Add to Read Only group")
    def assign_read_only(self, request, queryset):
        group = Group.objects.filter(name="Read Only").first()

        if group:
            for user in queryset:
                user.is_staff = True
                user.groups.add(group)
                user.save()

            messages.success(request, "Added to Read Only group.")
        else:
            messages.error(request, "Read Only Group does not exist.")

    @admin.action(description="Remove from Read Only group.")
    def unassign_read_only(self, request, queryset):
        group = Group.objects.filter(name="Read Only").first()

        if group:
            for user in queryset:
                user.is_staff = False
                user.groups.remove(group)
                user.save()

            messages.success(request, "Removed from Read Only group.")
        else:
            messages.error(request, "Read Only Group does not exist.")

    @admin.action(description="Add to Notifications group")
    def assign_notifications(self, request, queryset):
        group = Group.objects.filter(name="Notifications").first()

        if group:
            for user in queryset:
                user.groups.add(group)

            messages.success(request, "Added to Notifications group.")
        else:
            messages.error(request, "Notifications Group does not exist.")

    @admin.action(description="Remove from Notifications group")
    def unassign_notifications(self, request, queryset):
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
