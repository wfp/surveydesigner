from django.contrib import admin
from django.db import models
from frontend_content.models import FrontendContent
from martor.widgets import AdminMartorWidget


@admin.register(FrontendContent)
class FrontendContentAdmin(admin.ModelAdmin):
    list_display = ("id", "key")
    list_filter = (
        "date_created",
        "date_updated",
    )
    search_fields = ("message",)
    formfield_overrides = {
        models.TextField: {"widget": AdminMartorWidget},
    }
