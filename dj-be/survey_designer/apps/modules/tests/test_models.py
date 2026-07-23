import pytest
from accounts.const import PermissionGroups
from django.contrib.auth.models import Group
from modules.models import (
    Module,
    Submodule,
    SubmoduleMapping,
    SubmoduleMappingSurveyMode,
    SubmoduleMappingSurveyType,
)
from organization.permissions import mutation_safe_related_queryset


@pytest.mark.django_db
def test_mutation_safe_module_queryset_excludes_shared_content(
    user, module_1, module_2, organization_1
):
    user.organization = organization_1
    user.groups.add(Group.objects.get_or_create(name=PermissionGroups.ADMINS)[0])
    writable_modules = mutation_safe_related_queryset(Module.objects.all(), user)
    assert list(writable_modules) == [module_1]


@pytest.mark.django_db
def test_mutation_safe_submodule_queryset_excludes_shared_content(
    user, submodule_1, submodule_2, organization_1
):
    user.organization = organization_1
    user.groups.add(Group.objects.get_or_create(name=PermissionGroups.ADMINS)[0])
    writable_submodules = mutation_safe_related_queryset(Submodule.objects.all(), user)
    assert list(writable_submodules) == [submodule_1]


@pytest.mark.django_db
def test_default_mapping_duplication_copies_modes(
    module_1, survey_type_1, survey_mode_1
):
    # Prepare a default mapping with a survey type and its mode
    default_mapping = SubmoduleMapping.objects.create()
    old_type_mapping = SubmoduleMappingSurveyType.objects.create(
        submodule_mapping=default_mapping,
        survey_type=survey_type_1,
        is_mandatory=True,
    )
    SubmoduleMappingSurveyMode.objects.create(
        survey_type=old_type_mapping,
        survey_mode=survey_mode_1,
        is_mandatory=True,
    )
    module_1.default_submodule_mapping = default_mapping
    module_1.save()

    # Creating a submodule without an explicit mapping should duplicate the default one
    new_submodule = Submodule.objects.create(
        name="DefaultMappingSubmodule",
        label="Default Mapping Submodule",
        module=module_1,
        appearance="test",
    )

    new_mapping = new_submodule.mapping
    assert new_mapping
    assert new_mapping != default_mapping

    # The survey type should be duplicated to the new mapping
    new_type_mapping = SubmoduleMappingSurveyType.objects.get(
        submodule_mapping=new_mapping,
        survey_type=survey_type_1,
    )
    # And its associated mode should be copied over to the duplicated survey type
    assert (
        SubmoduleMappingSurveyMode.objects.filter(
            survey_type=new_type_mapping,
            survey_mode=survey_mode_1,
            is_mandatory=True,
        ).count()
        == 1
    )
