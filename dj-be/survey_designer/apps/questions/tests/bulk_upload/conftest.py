import pytest
from accounts.factories import AdminFactory
from modules.factories import ModuleFactory, SubmoduleFactory
from organization.tests.factories import OrganizationFactory
from questions.factories import RootQuestionFactory


@pytest.fixture()
def setup_upload_base(global_admin):
    org_wfp = OrganizationFactory(name="WFP_")
    org_unicef = OrganizationFactory(name="UNICEF_")
    org_red_cross = OrganizationFactory(name="RED_CROSS_")

    admin_wfp = AdminFactory(email="admin@wfp.test", organization=org_wfp)
    admin_unicef = AdminFactory(email="admin@unicef.test", organization=org_unicef)

    module_wfp = ModuleFactory(name="wfp_module", label="wfp_module")
    module_unicef = ModuleFactory(name="unicef_module", label="unicef_module")
    module_red_cross = ModuleFactory(name="red_cross_module", label="red_cross_module")
    module_shared = ModuleFactory(name="shared_module", label="shared_module")

    module_wfp.organizations.set([org_wfp])
    module_unicef.organizations.set([org_unicef])
    module_red_cross.organizations.set([org_red_cross])
    module_shared.organizations.set([org_wfp, org_unicef])

    red_cross_submodule_1 = SubmoduleFactory(
        name="red_cross_submodule_1",
        label="red_cross_submodule_1",
        module=module_red_cross,
    )
    wfp_submodule_1 = SubmoduleFactory(
        name="wfp_submodule_1", label="wfp_submodule_1", module=module_wfp
    )
    _ = SubmoduleFactory(
        name="wfp_submodule_2", label="wfp_submodule_2", module=module_wfp
    )
    unicef_submodule_1 = SubmoduleFactory(
        name="unicef_submodule_1", label="unicef_submodule_1", module=module_unicef
    )
    _ = SubmoduleFactory(
        name="unicef_submodule_2", label="unicef_submodule_2", module=module_unicef
    )
    _ = SubmoduleFactory(
        name="shared_submodule", label="shared_submodule", module=module_shared
    )

    _ = RootQuestionFactory(
        **{
            "name": "wfp_unicef_shared_question",
            "submodules": [
                {"submodule_id": wfp_submodule_1.id},
                {"submodule_id": unicef_submodule_1.id},
            ],
            "description": "Some shared question across 2 submodules",
            "type": "integer",
            "label": "Question shared across 2 submodules, one wfp, one unicef",
            "sub_questions": [],
        }
    )

    _ = RootQuestionFactory(
        **{
            "name": "red_cross_unicef_shared_question",
            "submodules": [
                {"submodule_id": red_cross_submodule_1.id},
                {"submodule_id": unicef_submodule_1.id},
            ],
            "description": "Some shared question across 2 submodules",
            "type": "integer",
            "label": "Question shared across 2 submodules, one red_cross, one unicef",
            "sub_questions": [],
        }
    )

    return admin_wfp, admin_unicef, global_admin
