from release_notifications.models import ReleaseEvent
from rest_framework import serializers


class ReleaseNotificationSerializer(serializers.ModelSerializer):
    state = serializers.SerializerMethodField()

    class Meta:
        model = ReleaseEvent
        fields = ("id", "version", "description", "deployed_at", "state")

    def get_state(self, obj):
        state = self.context.get("user_states", {}).get(obj.pk)
        if state is None:
            state = self.context.get("user_state")
        return state.state if state else "unread"


class ClearReleaseNotificationsSerializer(serializers.Serializer):
    release_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), allow_empty=False, max_length=5
    )
