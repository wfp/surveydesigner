import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
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

    def test_process_relevant_dependencies_uses_non_selected_submodules(
        self,
        submodule_1,
        submodule_2,
        submodule_3,
        root_question_1,
        root_question_3,
        indicator_1,
    ):
        root_question_1.relevant_dependencies.add(root_question_3.base_question)

        validator = SubmodulesOrderValidator(
            [submodule_1.id, submodule_2.id],
            [indicator_1.id],
            [submodule_1.id, submodule_2.id, submodule_3.id],
        )

        validator.process()

        assert submodule_1 in validator.dependencies_result
        assert (
            submodule_3
            in validator.dependencies_result[submodule_1]["related_submodules"]
        )
        assert [
            dependency.name
            for dependency in validator.dependencies_result[submodule_1]["dependencies"]
        ] == [root_question_3.name]

    def test_process_uses_bounded_queries(
        self,
        submodule_1,
        submodule_2,
        submodule_3,
        root_question_1,
        root_question_3,
        root_question_4,
        indicator_1,
    ):
        root_question_1.relevant_dependencies.add(root_question_3.base_question)
        root_question_1.constraint_dependencies.add(root_question_4.base_question)

        validator = SubmodulesOrderValidator(
            [submodule_1.id, submodule_2.id],
            [indicator_1.id],
            [submodule_1.id, submodule_2.id, submodule_3.id],
        )

        with CaptureQueriesContext(connection) as queries:
            validator.process()
            validator.get_messages()

        # Current optimized path is single-digit queries in local profiling.
        assert len(queries) <= 10
