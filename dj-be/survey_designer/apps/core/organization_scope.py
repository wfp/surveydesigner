from django.db.models import Q
from organization.models import Organization
from rest_framework.exceptions import ParseError, ValidationError


def get_selected_organization_ids(request):
    """Validate the selected read scope carried by the organization header."""
    if getattr(request, "organization_ids_parse_error", False):
        raise ParseError("Survey-Designer-Organizations must contain integer IDs.")

    organization_ids = getattr(request, "organization_ids", [])
    if not organization_ids:
        return []

    requested_organization_ids = set(organization_ids)
    existing_organization_ids = set(
        Organization.objects.filter(id__in=requested_organization_ids).values_list(
            "id", flat=True
        )
    )

    if requested_organization_ids != existing_organization_ids:
        raise ValidationError("One or more selected organizations could not be found.")

    return organization_ids


def filter_for_selected_organizations(
    queryset, organization_ids, relations=("organizations",)
):
    """Require association with every selected organization.

    Multiple relation paths are alternatives for each organization. Repeated filters
    provide intersection semantics while allowing additional associations.
    """
    if not organization_ids:
        return queryset.none()
    if isinstance(relations, str):
        relations = (relations,)

    for organization_id in set(organization_ids):
        organization_filter = Q()
        for relation in relations:
            organization_filter |= Q(**{f"{relation}__id": organization_id})
        queryset = queryset.filter(organization_filter)
    return queryset.distinct()


def validate_scoped_ids(
    queryset,
    submitted_ids,
    organization_ids,
    *,
    relations=("organizations",),
    field_name,
):
    """Validate IDs against selected scope without distinguishing missing/foreign."""
    submitted_ids = set(submitted_ids or [])
    if not submitted_ids:
        return
    scoped_ids = set(
        filter_for_selected_organizations(
            queryset.filter(pk__in=submitted_ids),
            organization_ids,
            relations=relations,
        ).values_list("pk", flat=True)
    )
    if scoped_ids != submitted_ids:
        raise ValidationError(
            {
                field_name: "One or more selected items are outside the selected organization scope."
            }
        )
