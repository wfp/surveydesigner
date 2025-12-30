from accounts.models import User, UserAPIKey, UserAPISite
from rest_framework import serializers


class UserAPISiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAPISite
        fields = ["id", "api_type", "name", "url"]


class UserAPIKeySerializer(serializers.ModelSerializer):
    raw_key = serializers.CharField(source="get_key")
    is_name_required = serializers.SerializerMethodField()

    class Meta:
        model = UserAPIKey
        fields = (
            "id",
            "site",
            "site_url",
            "raw_key",
            "name",
            "is_name_required",
        )
        extra_kwargs = {
            "site": {"required": True, "allow_null": False},
            "name": {"required": True, "allow_blank": False},
        }

    def get_is_name_required(self, obj) -> bool:
        return True

    def create(self, validated_data):
        raw_key = validated_data.pop("get_key", "")
        instance = super().create(validated_data)
        instance.set_key(raw_key)
        instance.save()
        return instance

    def update(self, instance, validated_data):
        raw_key = validated_data.pop("get_key", "")
        instance = super().update(instance, validated_data)
        instance.set_key(raw_key)
        instance.save()
        return instance

    def validate(self, data):
        user = self.context["request"].user
        site = data.get("site")
        name = data.get("name")
        if (
            site
            and name
            and UserAPIKey.objects.filter(user=user, site=site, name=name).exists()
        ):
            raise serializers.ValidationError("Please provide a unique name.")
        return data


class UserAPIKeyReadSerializer(UserAPIKeySerializer):
    site = UserAPISiteSerializer()


class UserAPIKeySimpleSerializer(serializers.ModelSerializer):
    skip_projects = serializers.SerializerMethodField()

    class Meta:
        model = UserAPIKey
        fields = (
            "id",
            "name",
            "skip_projects",
        )

    def get_skip_projects(self, obj) -> bool:
        # KOBO does not have an external API for projects. Every KOBO project has a unique API key
        return obj.site_id and obj.site.is_kobo


class UserDetailSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    can_access_cms = serializers.SerializerMethodField()
    read_only_member = serializers.BooleanField(read_only=True)
    sites = UserAPIKeySimpleSerializer(many=True, source="api_keys.all", read_only=True)

    class Meta:
        model = User
        fields = [
            "display_name",
            "email",
            "can_access_cms",
            "sites",
            "read_only_member",
        ]

    def get_can_access_cms(self, obj) -> bool:
        return obj.is_staff or obj.is_superuser

    def get_display_name(self, obj) -> str:
        request = self.context.get("request")
        default_display_name = obj.display_name()
        if request:
            return request.session.get("display_name", default_display_name)
        return default_display_name
