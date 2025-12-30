from organization.models import Organization
from organization.serializers import OrganizationSerializer
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated


class ListOrganizationsView(ListAPIView):
    model = Organization
    serializer_class = OrganizationSerializer
    queryset = Organization.objects.all()
    permission_classes = [
        IsAuthenticated,
    ]
