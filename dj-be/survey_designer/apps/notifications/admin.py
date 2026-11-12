from core.admin import AdminUserTrackingMixin, CollationSafeSearchAdminMixin
from django.contrib import admin, messages
from django.core.exceptions import ValidationError

from .const import NotificationStatus
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
from .services import (
    can_publish_release,
    deactivate_notification,
    publish_notification,
    publish_release,
    validation_error_message,
)


def notification_content_is_locked(notification):
    return bool(
        notification
        and (
            notification.status == NotificationStatus.EXPIRED
            or (
                notification.is_active
                and notification.status
                in (NotificationStatus.SCHEDULED, NotificationStatus.PUBLISHED)
            )
        )
    )


class NotificationEditableInline(admin.TabularInline):
    def has_add_permission(self, request, obj=None):
        return not notification_content_is_locked(obj) and super().has_add_permission(
            request, obj
        )

    def has_change_permission(self, request, obj=None):
        return not notification_content_is_locked(
            obj
        ) and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return not notification_content_is_locked(
            obj
        ) and super().has_delete_permission(request, obj)


class ReleaseTranslationInline(admin.TabularInline):
    model = ReleaseTranslation
    form = ReleaseTranslationAdminForm
    fields = ("language", "title", "label")
    extra = 0


class NotificationTranslationInline(NotificationEditableInline):
    model = NotificationTranslation
    form = NotificationTranslationAdminForm
    fields = ("language", "title", "abstract", "label")
    extra = 0


class NotificationAudienceInline(NotificationEditableInline):
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
                self.message_user(
                    request,
                    f"Release {release.business_version}: {validation_error_message(exc)}",
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
    actions = ("publish_notifications", "deactivate_notifications")
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
        (
            "Notification",
            {
                "fields": ("release", "status", "is_active"),
                "description": (
                    "Leave Audience groups empty to reach all signed-in users. "
                    "Select groups to restrict this notification to their members."
                ),
            },
        ),
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

    def get_readonly_fields(self, request, obj=None):
        fields = super().get_readonly_fields(request, obj)
        if obj and obj.status != NotificationStatus.DRAFT:
            fields += ("is_active",)
        if notification_content_is_locked(obj):
            fields += (
                "release",
                "title",
                "abstract",
                "body",
                "publish_at",
                "expires_at",
            )
        return fields

    @admin.action(
        permissions=("change",),
        description="Publish or schedule selected notifications",
    )
    def publish_notifications(self, request, queryset):
        counts = {"published": 0, "scheduled": 0, "unchanged": 0}
        for notification in queryset.order_by("pk"):
            try:
                updated, changed = publish_notification(
                    notification_id=notification.pk, actor=request.user
                )
            except ValidationError as exc:
                self.message_user(
                    request,
                    f"Notification {notification.pk}: {validation_error_message(exc)}",
                    level=messages.ERROR,
                )
                continue
            if changed:
                counts[updated.status] += 1
                self.log_change(request, updated, f"Notification {updated.status}.")
            else:
                counts["unchanged"] += 1
        if any(counts.values()):
            self.message_user(
                request,
                f"Notifications: {counts['published']} published, {counts['scheduled']} scheduled, "
                f"{counts['unchanged']} unchanged. Scheduled transitions require the RQ worker.",
                level=messages.SUCCESS,
            )

    @admin.action(
        permissions=("change",), description="Deactivate selected notifications"
    )
    def deactivate_notifications(self, request, queryset):
        count = 0
        for notification in queryset.order_by("pk"):
            updated, changed = deactivate_notification(
                notification_id=notification.pk, actor=request.user
            )
            if changed:
                count += 1
                self.log_change(request, updated, "Notification deactivated.")
        self.message_user(
            request, f"Deactivated {count} notification(s).", level=messages.SUCCESS
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
