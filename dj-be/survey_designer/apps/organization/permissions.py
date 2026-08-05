"""Canonical organization read and mutation permission helpers."""

from django.db.models import Count
from organization.utils import get_organizations


def has_global_mutation_authority(user):
    return bool(user and (user.is_superuser or user.is_global_admins_member))


def can_create_organization_scoped_content(user):
    """Whether a user may create organization-scoped content at all."""
    return has_global_mutation_authority(user) or (
        user is not None
        and user.organization_id is not None
        and user.is_admins_member
        and not user.read_only_member
    )


def get_object_organizations(obj):
    """Resolve the organizations associated with an organization-scoped object."""
    return get_organizations(obj)


def can_mutate_object(user, obj):
    """Organization Admins may mutate only exclusively assigned content."""
    if has_global_mutation_authority(user):
        return True
    if not can_create_organization_scoped_content(user):
        return False
    if getattr(obj, "pk", None) is None:
        return True
    try:
        organization_ids = set(
            get_object_organizations(obj).values_list("id", flat=True)
        )
    except NotImplementedError:
        return False
    return organization_ids == {user.organization_id}


def organization_assignment_queryset(queryset, user):
    """Limit direct organization assignment without restricting relationships."""
    if has_global_mutation_authority(user):
        return queryset
    if user is None or user.organization_id is None:
        return queryset.none()
    return queryset.filter(pk=user.organization_id)


def mutable_objects_queryset(queryset, user):
    """Filter objects that an action is allowed to mutate.

    Relationship choices intentionally do not use this helper: organization admins
    may link content they own to readable foreign or shared content.
    """
    if has_global_mutation_authority(user):
        return queryset
    if not can_create_organization_scoped_content(user):
        return queryset.none()

    model = queryset.model
    if any(field.name == "organizations" for field in model._meta.many_to_many):
        return queryset.annotate(
            _mutation_organization_count=Count("organizations", distinct=True)
        ).filter(
            organizations=user.organization_id,
            _mutation_organization_count=1,
        )
    if any(field.name == "module" for field in model._meta.fields):
        return queryset.annotate(
            _mutation_organization_count=Count("module__organizations", distinct=True)
        ).filter(
            module__organizations=user.organization_id,
            _mutation_organization_count=1,
        )

    allowed_ids = [obj.pk for obj in queryset if can_mutate_object(user, obj)]
    return queryset.filter(pk__in=allowed_ids)
