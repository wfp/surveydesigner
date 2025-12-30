from django.contrib.auth import get_permission_codename
from organization.utils import get_organizations


class ChangeFormOrganizationsDisplayMixin:
    def change_view(self, request, object_id, form_url="", extra_context=None):
        obj = self.get_object(request, object_id)
        if obj is None:
            # Object does not exist; proceed with the default behavior
            return super().change_view(request, object_id, form_url, extra_context)

        organizations = get_organizations(obj)
        organization_names = list(organizations.values_list("name", flat=True))
        organization_names_str = (
            ", ".join(organization_names) if organization_names else "-----"
        )
        if extra_context is None:
            extra_context = {}
        extra_context["organization_names"] = organization_names_str
        return super().change_view(request, object_id, form_url, extra_context)


class ObjectPermissionMixin:
    def has_change_permission(self, request, obj=None):
        opts = self.opts
        codename = get_permission_codename("change", opts)
        return request.user.has_perm("{}.{}".format(opts.app_label, codename), obj)

    def has_delete_permission(self, request, obj=None):
        opts = self.opts
        codename = get_permission_codename("delete", opts)
        return request.user.has_perm("{}.{}".format(opts.app_label, codename), obj)

    def has_add_permission(self, request, obj=None):
        opts = self.opts
        codename = get_permission_codename("delete", opts)
        return request.user.has_perm("{}.{}".format(opts.app_label, codename), obj)


class RequestUserFormMixin:
    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj, change, **kwargs)
        form.user = request.user
        return form


class RestrictedVisibilityFieldMixin:
    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj, change, **kwargs)
        for restricted_visibility_field in self.restricted_visibility_fields:
            restricted_visibility_field = form.base_fields.get(
                restricted_visibility_field
            )
            if not restricted_visibility_field:
                continue
            restricted_visibility_field.queryset = (
                restricted_visibility_field.queryset.visible_for_user(request.user)
            )
        return form


class FormsetRequestMixin:
    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        formset.request = request
        return formset
