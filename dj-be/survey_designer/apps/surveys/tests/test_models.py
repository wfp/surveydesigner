import pytest
from accounts.const import PermissionGroups
from django.contrib.auth.models import Group
from organization.permissions import mutation_safe_related_queryset
from surveys.models import SurveyMode


@pytest.mark.django_db
def test_mutation_safe_survey_mode_queryset_excludes_shared_content(
    user, survey_mode_1, survey_mode_2, organization_1
):
    user.organization = organization_1
    user.groups.add(Group.objects.get_or_create(name=PermissionGroups.ADMINS)[0])
    writable_modes = mutation_safe_related_queryset(SurveyMode.objects.all(), user)
    assert list(writable_modes) == [survey_mode_1]
