import bleach
from rest_framework import serializers

from .localization import localized_content
from .models import Notification, Release

# Notification bodies are authored HTML. Never return arbitrary active HTML,
# embedded media, CSS, or attributes to the consumer renderer.
BODY_TAGS = (
    "p",
    "br",
    "strong",
    "em",
    "b",
    "i",
    "u",
    "s",
    "ul",
    "ol",
    "li",
    "h2",
    "h3",
    "h4",
    "blockquote",
    "pre",
    "code",
    "hr",
    "a",
)


class LocalizedContentMixin:
    def to_representation(self, instance):
        data = super().to_representation(instance)
        content = localized_content(
            instance, self.context["request"].query_params.get("lang")
        )
        for field in ("language", "title", "abstract", "body"):
            if field not in self.fields:
                continue
            value = content[field]
            if field == "body":
                value = bleach.clean(
                    value,
                    tags=BODY_TAGS,
                    attributes={"a": ["href", "title"]},
                    protocols=("http", "https", "mailto"),
                    strip=True,
                )
            data[field] = value
        return data


class NotificationListSerializer(LocalizedContentMixin, serializers.ModelSerializer):
    language = serializers.CharField(read_only=True)
    release_id = serializers.IntegerField(read_only=True, allow_null=True)
    is_read = serializers.BooleanField(read_only=True)

    class Meta:
        model = Notification
        fields = (
            "id",
            "release_id",
            "language",
            "title",
            "abstract",
            "publish_at",
            "expires_at",
            "is_read",
        )
        read_only_fields = fields


class NotificationDetailSerializer(NotificationListSerializer):
    class Meta(NotificationListSerializer.Meta):
        fields = NotificationListSerializer.Meta.fields + ("body",)
        read_only_fields = fields


class ReleaseSerializer(LocalizedContentMixin, serializers.ModelSerializer):
    language = serializers.CharField(read_only=True)

    class Meta:
        model = Release
        fields = (
            "id",
            "business_version",
            "language",
            "title",
            "body",
            "released_at",
            "published_at",
        )
        read_only_fields = fields


class AcknowledgementRequestSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=("read", "dismiss"))

    def validate(self, attrs):
        extra = set(self.initial_data) - set(self.fields)
        if extra:
            raise serializers.ValidationError(
                {field: "Unexpected field." for field in sorted(extra)}
            )
        return attrs


class AcknowledgementSerializer(serializers.Serializer):
    id = serializers.IntegerField(source="notification_id", read_only=True)
    state = serializers.CharField(read_only=True)
    read_at = serializers.DateTimeField(read_only=True)
    dismissed = serializers.BooleanField(read_only=True)
