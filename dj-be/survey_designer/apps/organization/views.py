from organization.models import Organization
from organization.serializers import OrganizationSerializer
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated


class ListOrganizationsView(ListAPIView):
    model = Organization
    serializer_class = OrganizationSerializer
    permission_classes = [
        IsAuthenticated,
    ]

    def get_queryset(self):
        return Organization.objects.readable_by(self.request.user)
