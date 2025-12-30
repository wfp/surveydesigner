from django.db import models
from django.forms import Textarea


class FormFieldOverridesMixin:
    formfield_overrides = {
        models.TextField: {"widget": Textarea(attrs={"rows": 2, "cols": 70})},
    }


class AdminUserTrackingMixin:
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if hasattr(obj, "created_by") and not obj.created_by_id:
            obj.created_by = request.user

        if hasattr(obj, "updated_by"):
            obj.updated_by = request.user
        obj.save()

    def modified_by(self, obj):
        return obj.updated_by

    modified_by.short_description = "Modified By"

    def modified_on(self, obj):
        return obj.date_updated

    modified_on.short_description = "Modified On"
    modified_on.admin_order_field = "date_updated"
