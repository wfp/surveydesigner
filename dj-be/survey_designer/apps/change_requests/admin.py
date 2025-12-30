from admin_auto_filters.filters import AutocompleteFilter
from change_requests.forms import ChangeRequestAdminForm
from change_requests.models import ChangeRequest
from django.contrib import admin
from django.contrib.postgres.aggregates import ArrayAgg
from django.shortcuts import reverse
from django.utils.html import format_html
from organization.mixins import (
    ChangeFormOrganizationsDisplayMixin,
    ObjectPermissionMixin,
)


class CreatedByFilter(AutocompleteFilter):
    title = "Created By"
    field_name = "created_by"
    parameter_name = "created_by__pk"


@admin.register(ChangeRequest)
class ChangeRequestAdmin(
    ObjectPermissionMixin, ChangeFormOrganizationsDisplayMixin, admin.ModelAdmin
):
    request: None
    form = ChangeRequestAdminForm
    exclude = (
        "created_by",
        "updated_by",
    )
    list_display = (
        "id",
        "created_by",
        "organizations_display",
        "status",
        "updated_by",
        "date_created",
        "date_updated",
    )
    readonly_fields = (
        "created_by",
        "description",
        "file",
    )
    list_select_related = ("created_by",)

    def has_add_permission(self, request):
        return False

    def get_list_display(self, request):
        list_display = list(super().get_list_display(request))
        if request.user.can_manage_change_requests:
            list_display.append("approve_button")
        return list_display

    def get_list_filter(self, request):
        filters = [
            "status",
            "organizations",
        ]

        # if request.user.can_manage_change_requests:
        #     filters.append(CreatedByFilter)
        return filters

    def get_queryset(self, request):
        self.request = request
        qs = super().get_queryset(request)
        qs = qs.annotate(
            change_request_organizations=ArrayAgg("organizations__name", distinct=True)
        )

        if request.user.can_manage_change_requests:
            return qs
        return qs.filter(created_by=request.user)

    def get_readonly_fields(self, request, obj=None):
        read_only_fields = list(self.readonly_fields)
        if obj and (obj.is_approved or obj.is_rejected):
            read_only_fields.insert(0, "status")
        return read_only_fields

    @admin.display(description="Approve")
    def approve_button(self, obj):
        if not obj.id or not obj.can_be_approved:
            return "-"
        button_text = "Approve" if obj.user_can_approve(self.request.user) else "Review"
        url = reverse("approve_change_request", args=[obj.id])
        return format_html(
            "<a class='button' type='button' href='{url}'>{button_text}</button>",
            url=url,
            button_text=button_text,
        )

    @admin.display(description="Organizations")
    def organizations_display(self, obj):
        if not obj.change_request_organizations or not any(
            obj.change_request_organizations
        ):
            return ""
        return ", ".join(obj.change_request_organizations)
