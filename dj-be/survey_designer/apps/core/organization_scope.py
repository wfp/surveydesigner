from organization.models import Organization
from rest_framework.exceptions import ParseError, PermissionDenied


def get_authorized_organization_ids(request):
    if getattr(request, "organization_ids_parse_error", False):
        raise ParseError("Survey-Designer-Organizations must contain integer IDs.")

    organization_ids = getattr(request, "organization_ids", [])
    if not organization_ids:
        return []

    allowed_organization_ids = set(
        Organization.objects.visible_for_user(request.user).values_list("id", flat=True)
    )
    requested_organization_ids = set(organization_ids)

    if not requested_organization_ids.issubset(allowed_organization_ids):
        raise PermissionDenied(
            "You do not have access to one or more requested organizations."
        )

    return organization_ids
