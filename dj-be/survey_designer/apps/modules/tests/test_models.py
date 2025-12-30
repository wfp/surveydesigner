import pytest
from modules.models import (
    Module,
    Submodule,
    SubmoduleMapping,
    SubmoduleMappingSurveyMode,
    SubmoduleMappingSurveyType,
)


@pytest.mark.django_db
def test_visible_for_user_module(user, module_1, module_2, organization_1):
    # Query the visible modules for the not global admin user
    user.organization = organization_1
    visible_modules = Module.objects.visible_for_user(user)
    # Check that both module_1 and module_2 are visible
    assert module_1 in visible_modules
    assert module_2 in visible_modules
    assert visible_modules.count() == 2


@pytest.mark.django_db
def test_visible_for_user_submodule(user, submodule_1, submodule_2, organization_1):
    # Query the visible submodules for the not global admin user
    user.organization = organization_1
    visible_submodules = Submodule.objects.visible_for_user(user)
    # Check that both submodule_1 and submodule_2 are visible
    assert submodule_1 in visible_submodules
    assert submodule_2 in visible_submodules
    assert visible_submodules.count() == 2


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
