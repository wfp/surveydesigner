import json
from contextvars import ContextVar
from types import MethodType

from django.contrib import messages
from django.contrib.admin import helpers
from django.contrib.auth import get_permission_codename
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.utils.safestring import mark_safe
from organization.utils import get_organizations

_OBJECT_PERMISSION_ADMIN_REQUEST = ContextVar(
    "object_permission_admin_request", default=None
)


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
    object_permission_readonly_actions = ("export_action",)
    object_permission_sortable_move_actions = (
        "move_to_exact_page",
        "move_to_back_page",
        "move_to_forward_page",
        "move_to_first_page",
        "move_to_last_page",
    )

    def _permission_name(self, action):
        opts = self.opts
        codename = get_permission_codename(action, opts)
        return f"{opts.app_label}.{codename}"

    def has_change_permission(self, request, obj=None):
        return request.user.has_perm(self._permission_name("change"), obj)

    def has_delete_permission(self, request, obj=None):
        return request.user.has_perm(self._permission_name("delete"), obj)

    def has_add_permission(self, request, obj=None):
        return request.user.has_perm(self._permission_name("add"), obj)

    def _has_object_permission(self, request, action, obj):
        return request.user.has_perm(self._permission_name(action), obj)

    def _has_unrestricted_object_permissions(self, request):
        return request.user.is_superuser or request.user.is_global_admins_member

    def _get_objects_without_permission(self, request, action, queryset):
        return [
            obj
            for obj in queryset
            if not self._has_object_permission(request, action, obj)
        ]

    def _object_permission_denied_response(self, request, disallowed_objects):
        object_names = ", ".join(str(obj) for obj in disallowed_objects[:5])
        if len(disallowed_objects) > 5:
            object_names = f"{object_names}, ..."
        self.message_user(
            request,
            f"Action not allowed for objects outside your organization: {object_names}",
            level=messages.ERROR,
        )
        return HttpResponseRedirect(request.get_full_path())

    def _get_requested_action(self, request):
        try:
            action_index = int(request.POST.get("index", 0))
        except ValueError:
            action_index = 0

        data = request.POST.copy()
        data.pop(helpers.ACTION_CHECKBOX_NAME, None)
        data.pop("index", None)

        try:
            data.update({"action": data.getlist("action")[action_index]})
        except IndexError:
            pass

        action_form = self.action_form(data, auto_id=None)
        action_form.fields["action"].choices = self.get_action_choices(request)
        if not action_form.is_valid():
            return None, False
        return (
            action_form.cleaned_data["action"],
            action_form.cleaned_data["select_across"],
        )

    def _get_action_object_permission(self, action_func):
        allowed_permissions = tuple(getattr(action_func, "allowed_permissions", ()))
        if allowed_permissions == ("delete",):
            return "delete"
        return "change"

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not self._has_unrestricted_object_permissions(request):
            for action_name in self.object_permission_sortable_move_actions:
                actions.pop(action_name, None)
        return actions

    def response_action(self, request, queryset):
        action_name, select_across = self._get_requested_action(request)
        actions = self.get_actions(request)

        if (
            action_name
            and action_name in actions
            and action_name not in self.object_permission_readonly_actions
        ):
            selected = request.POST.getlist(helpers.ACTION_CHECKBOX_NAME)
            if selected or select_across:
                if not select_across:
                    queryset = queryset.filter(pk__in=selected)

                action_func = actions[action_name][0]
                permission_action = self._get_action_object_permission(action_func)
                disallowed_objects = self._get_objects_without_permission(
                    request, permission_action, queryset
                )
                if disallowed_objects:
                    return self._object_permission_denied_response(
                        request, disallowed_objects
                    )

        return super().response_action(request, queryset)

    def update_order(self, request):
        if request.method == "POST":
            try:
                updated_items = json.loads(request.body).get("updatedItems") or []
            except (AttributeError, TypeError, ValueError):
                updated_items = []

            updated_object_ids = []
            for item in updated_items:
                if not item:
                    continue
                try:
                    updated_object_ids.append(item[0])
                except (KeyError, IndexError, TypeError):
                    continue
            queryset = self.model.objects.filter(pk__in=updated_object_ids)
            disallowed_objects = self._get_objects_without_permission(
                request, "change", queryset
            )
            if disallowed_objects:
                return HttpResponseForbidden(
                    "Missing object permissions to perform this request"
                )

        return super().update_order(request)

    def _add_reorder_method(self):
        super()._add_reorder_method()
        original_reorder = self._reorder_

        def func(this, item):
            request = _OBJECT_PERMISSION_ADMIN_REQUEST.get()
            if request is not None and not this.has_change_permission(request, item):
                return mark_safe('<div class="drag">&nbsp;</div>')
            return original_reorder(item)

        for attr in ("short_description", "admin_order_field", "allow_tags"):
            if hasattr(original_reorder, attr):
                setattr(func, attr, getattr(original_reorder, attr))
        self._reorder_ = MethodType(func, self)

    def get_list_display(self, request):
        _OBJECT_PERMISSION_ADMIN_REQUEST.set(request)
        return list(super().get_list_display(request))


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
