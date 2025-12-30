from frontend_content.models import FrontendContent
from frontend_content.serializers import FrontendContentSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet


class FrontendContentViewSet(ModelViewSet):
    http_method_names = ["get"]
    queryset = FrontendContent.objects.all()
    serializer_class = FrontendContentSerializer
    permission_classes = [IsAuthenticated]
