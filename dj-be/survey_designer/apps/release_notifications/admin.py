from django.contrib import admin
from release_notifications.models import ReleaseEvent, UserReleaseState


@admin.register(ReleaseEvent)
class ReleaseEventAdmin(admin.ModelAdmin):
    list_display = ("version", "source_id", "deployed_at", "is_active")
    list_filter = ("is_active", "deployed_at")
    search_fields = ("version", "source_id")
    ordering = ("-deployed_at", "-id")


@admin.register(UserReleaseState)
class UserReleaseStateAdmin(admin.ModelAdmin):
    list_display = ("user", "release_event", "read_at", "cleared_at")
    list_filter = ("read_at", "cleared_at")
    search_fields = ("user__email", "release_event__version")
    raw_id_fields = ("user", "release_event")
