"""Canonical organization read and mutation permission helpers."""

from django.db.models import Count, Q
from organization.models import Organization
from organization.utils import get_organizations

_MUTATION_ORGANIZATION_RELATIONS = {
    "modules.indicator": (
        "questions__root_question__submodule__module__organizations",
        "questions__sub_question__root_question__submodule__module__organizations",
        "questions__repeat_section__submodule__module__organizations",
        "mapping__survey_types__organizations",
        "mapping__survey_attributes__organizations",
    ),
    "questions.basequestion": (
        "root_question__submodule__module__organizations",
        "sub_question__root_question__submodule__module__organizations",
        "repeat_section__submodule__module__organizations",
    ),
    "questions.repeatsection": ("submodule__module__organizations",),
}


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


def mutation_safe_related_queryset(queryset, user):
    """Limit editable related-object choices; never use this for reading."""
    if has_global_mutation_authority(user):
        return queryset
    if not can_create_organization_scoped_content(user):
        return queryset.none()

    model = queryset.model
    if model is Organization:
        return queryset.filter(pk=user.organization_id)

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

    relations = _MUTATION_ORGANIZATION_RELATIONS.get(model._meta.label_lower)
    if relations:
        own_organization = Q()
        foreign_organizations = Q()
        other_organizations = Organization.objects.exclude(pk=user.organization_id)
        for relation in relations:
            own_organization |= Q(**{f"{relation}__id": user.organization_id})
            foreign_organizations |= Q(**{f"{relation}__in": other_organizations})
        return (
            queryset.filter(own_organization).exclude(foreign_organizations).distinct()
        )

    allowed_ids = [obj.pk for obj in queryset if can_mutate_object(user, obj)]
    return queryset.filter(pk__in=allowed_ids)
