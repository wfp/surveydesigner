from django.contrib import admin
from organization.mixins import ObjectPermissionMixin

from .models import SavedSurvey


@admin.register(SavedSurvey)
class SavedSurveyAdmin(ObjectPermissionMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "owner",
        "name",
        "survey_type",
        "survey_category",
        "survey_mode",
        "uuid",
    )
