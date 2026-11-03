from core.admin import AdminUserTrackingMixin, CollationSafeSearchAdminMixin
from django.contrib import admin, messages
from django.core.exceptions import ValidationError

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
from .services import can_publish_release, publish_release


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
    actions = ("publish_releases",)
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

    def has_publish_permission(self, request):
        return can_publish_release(request.user)

    @admin.action(permissions=("publish",), description="Publish selected releases")
    def publish_releases(self, request, queryset):
        published = 0
        unchanged = 0
        for release in queryset.order_by("pk"):
            try:
                notification, created = publish_release(
                    release_id=release.pk, actor=request.user
                )
            except ValidationError as exc:
                details = (
                    "; ".join(
                        f"{field}: {'; '.join(errors)}"
                        for field, errors in exc.message_dict.items()
                    )
                    if hasattr(exc, "message_dict")
                    else "; ".join(exc.messages)
                )
                self.message_user(
                    request,
                    f"Release {release.business_version}: {details}",
                    level=messages.ERROR,
                )
                continue
            if created:
                published += 1
                self.log_change(
                    request,
                    release,
                    f"Published release and created draft notification {notification.pk}.",
                )
            else:
                unchanged += 1
        if published:
            self.message_user(
                request,
                f"Published {published} release(s) and created their draft notifications. "
                "Review notification audiences and timing before delivery is enabled.",
                level=messages.SUCCESS,
            )
        if unchanged:
            self.message_user(
                request,
                f"{unchanged} release(s) were already published; nothing was changed.",
                level=messages.INFO,
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
