from unittest.mock import MagicMock

import pytest
from organization.utils import get_organizations


def test_get_organizations_question_not_shared(root_question_1, organization_1):
    organizations = get_organizations(root_question_1)
    assert organizations.count() == 1
    assert organizations.first() == organization_1


def test_get_organizations_module_not_shared(module_1, organization_1):
    organizations = get_organizations(module_1)
    assert organizations.count() == 1
    assert organizations.first() == organization_1


def test_get_organizations_submodule_not_shared(submodule_1, organization_1):
    organizations = get_organizations(submodule_1)
    assert organizations.count() == 1
    assert organizations.first() == organization_1


def test_get_organizations_question_shared(
    root_question_3, organization_1, organization_2
):
    organizations = get_organizations(root_question_3)
    assert organizations.count() == 2
    assert organizations.first() == organization_1
    assert organizations.last() == organization_2


def test_get_organizations_module_shared(module_2, organization_1, organization_2):
    organizations = get_organizations(module_2)
    assert organizations.count() == 2
    assert organizations.first() == organization_1
    assert organizations.last() == organization_2


def test_get_organizations_ubmodule_shared(submodule_2, organization_1, organization_2):
    organizations = get_organizations(submodule_2)
    assert organizations.count() == 2
    assert organizations.first() == organization_1
    assert organizations.last() == organization_2


def test_get_organizations_missing_implementation():
    with pytest.raises(
        NotImplementedError, match="Missing get_organizations implementation"
    ):

        class TestClass:
            pass

        get_organizations(TestClass())


def test_global_admin_has_shared_organization_permission(global_admin, module_2):
    request = MagicMock()
    request.user = global_admin

    assert global_admin.has_perm("modules.change_module", module_2)


def test_admin_has_not_shared_organization_permission(admin, module_2):
    request = MagicMock()
    request.user = admin

    assert admin.has_perm("modules.change_module", module_2)
