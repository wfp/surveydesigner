from core.admin import AdminUserTrackingMixin, CollationSafeSearchAdminMixin
from django.contrib import admin

from .forms import (
    NotificationAdminForm,
    NotificationTranslationAdminForm,
    ReleaseAdminForm,
    ReleaseTranslationAdminForm,
)
from .models import (
    Notification,
    NotificationAudience,
    NotificationRead,
    NotificationTranslation,
    Release,
    ReleaseTranslation,
)


class ReleaseTranslationInline(admin.TabularInline):
    model = ReleaseTranslation
    form = ReleaseTranslationAdminForm
    fields = ("language", "title", "label")
    extra = 0


class NotificationTranslationInline(admin.TabularInline):
    model = NotificationTranslation
    form = NotificationTranslationAdminForm
    fields = ("language", "title", "abstract", "label")
    extra = 0


class NotificationAudienceInline(admin.TabularInline):
    model = NotificationAudience
    fields = ("group",)
    autocomplete_fields = ("group",)
    extra = 0
    verbose_name = "Audience group"
    verbose_name_plural = "Audience groups"


class NotificationContentAdmin(
    CollationSafeSearchAdminMixin, AdminUserTrackingMixin, admin.ModelAdmin
):
    readonly_fields = (
        "status",
        "created_by",
        "updated_by",
        "date_created",
        "date_updated",
    )
    actions = None

    def has_delete_permission(self, request, obj=None):
        return False

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in formset.deleted_objects:
            instance.delete()
        for instance in instances:
            if hasattr(instance, "created_by_id"):
                if not instance.created_by_id:
                    instance.created_by = request.user
                instance.updated_by = request.user
            instance.save()
        formset.save_m2m()


@admin.register(Release)
class ReleaseAdmin(NotificationContentAdmin):
    form = ReleaseAdminForm
    inlines = (ReleaseTranslationInline,)
    list_display = (
        "business_version",
        "configuration_version",
        "title",
        "status",
        "published_at",
        "is_active",
    )
    list_filter = ("status", "is_active", "published_at")
    search_fields = ("business_version", "configuration_version", "github_tag", "title")
    list_select_related = ("created_by", "updated_by")
    readonly_fields = NotificationContentAdmin.readonly_fields + (
        "github_tag",
        "github_release_id",
        "github_url",
        "released_at",
        "published_at",
    )
    fieldsets = (
        (
            "Release",
            {
                "fields": (
                    "business_version",
                    "configuration_version",
                    "status",
                    "published_at",
                    "is_active",
                )
            },
        ),
        ("English content", {"fields": ("title", "body")}),
        (
            "GitHub source",
            {
                "fields": (
                    "github_tag",
                    "github_release_id",
                    "github_url",
                    "released_at",
                )
            },
        ),
        (
            "Audit",
            {
                "fields": ("created_by", "updated_by", "date_created", "date_updated"),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(Notification)
class NotificationAdmin(NotificationContentAdmin):
    form = NotificationAdminForm
    inlines = (NotificationTranslationInline, NotificationAudienceInline)
    autocomplete_fields = ("release",)
    list_display = (
        "title",
        "release",
        "status",
        "publish_at",
        "expires_at",
        "is_active",
    )
    list_filter = ("status", "is_active", "publish_at", "expires_at")
    search_fields = ("title", "abstract", "release__business_version")
    list_select_related = ("release", "created_by", "updated_by")
    fieldsets = (
        ("Notification", {"fields": ("release", "status", "is_active")}),
        ("English content", {"fields": ("title", "abstract", "body")}),
        ("Timing", {"fields": ("publish_at", "expires_at")}),
        (
            "Audit",
            {
                "fields": ("created_by", "updated_by", "date_created", "date_updated"),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(NotificationRead)
class NotificationReadAdmin(CollationSafeSearchAdminMixin, admin.ModelAdmin):
    list_display = ("notification", "user", "state", "read_at", "date_created")
    list_filter = ("dismissed", "read_at", "date_created")
    search_fields = (
        "user__email",
        "notification__title",
        "notification__release__business_version",
    )
    list_select_related = ("user", "notification")
    readonly_fields = (
        "notification",
        "user",
        "state",
        "read_at",
        "dismissed",
        "date_created",
    )
    ordering = ("-date_created", "-id")
    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
