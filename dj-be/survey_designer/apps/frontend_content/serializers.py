from frontend_content.models import FrontendContent
from rest_framework import serializers


class FrontendContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FrontendContent
        fields = ["id", "message", "key", "severity", "is_active"]
