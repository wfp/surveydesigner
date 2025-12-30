import pytest
from modules.services import SubmodulesOrderValidator


@pytest.mark.django_db
class TestSubmodulesOrderValidator:
    def test_get_submodules(self, submodule_1, submodule_2, indicator_1):
        submodule_ids = [submodule_1.id]
        indicator_ids = [indicator_1.id]
        all_submodule_ids = [submodule_1.id, submodule_2.id]
        validator = SubmodulesOrderValidator(
            submodule_ids, indicator_ids, all_submodule_ids
        )
        submodules = validator.get_submodules()

        assert [submodule.id for submodule in submodules] == submodule_ids

    def test_process(self, submodule_1, submodule_2, indicator_1):
        submodule_ids = [submodule_1.id]
        indicator_ids = [indicator_1.id]
        all_submodule_ids = [submodule_1.id, submodule_2.id]
        validator = SubmodulesOrderValidator(
            submodule_ids, indicator_ids, all_submodule_ids
        )
        validator.process()
        # should raise an error on failure
