from django.contrib import admin
from documents.models import Document


@admin.register(Document)
class ModuleAdmin(
    admin.ModelAdmin,
):
    exclude = (
        "created_by",
        "updated_by",
    )
    list_display = (
        "id",
        "document",
    )
