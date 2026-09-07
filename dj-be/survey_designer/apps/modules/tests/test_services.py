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

    @pytest.mark.parametrize(
        "field",
        ("relevant", "constraint", "calculation", "choice_filter"),
    )
    def test_process_relevant_dependencies_uses_non_selected_submodules(
        self,
        field,
        submodule_1,
        submodule_2,
        submodule_3,
        root_question_1,
        root_question_3,
    ):
        setattr(root_question_1, field, f"${{{root_question_3.name}}}")
        root_question_1.save(update_fields=[field])

        validator = SubmodulesOrderValidator(
            [submodule_1.id],
            [],
            [submodule_1.id, submodule_2.id, submodule_3.id],
        )

        validator.process()

        assert [issue.code for issue in validator.get_issues()] == [
            "SELECTED_SCOPE_DEPENDENCY_NOT_EMITTED"
        ]
        assert validator.get_issues()[0].owner == {
            "model": "RootQuestion",
            "id": root_question_1.id,
            "name": root_question_1.name,
        }
        assert validator.get_issues()[0].field == field
        assert submodule_1 in validator.dependencies_result
        assert (
            submodule_2
            in validator.dependencies_result[submodule_1]["related_submodules"]
        )
        assert (
            submodule_3
            in validator.dependencies_result[submodule_1]["related_submodules"]
        )
        assert [
            dependency.name
            for dependency in validator.dependencies_result[submodule_1]["dependencies"]
        ] == [root_question_3.name]

    def test_dependency_in_another_selected_submodule_is_valid(
        self,
        submodule_1,
        submodule_2,
        submodule_3,
        root_question_1,
        root_question_3,
    ):
        root_question_1.relevant = f"${{{root_question_3.name}}}"
        root_question_1.save(update_fields=["relevant"])
        validator = SubmodulesOrderValidator(
            [submodule_1.id, submodule_2.id],
            [],
            [submodule_1.id, submodule_2.id, submodule_3.id],
        )

        validator.process()

        assert validator.get_issues() == []

    def test_dependency_selected_through_indicator_is_valid(
        self,
        submodule_1,
        submodule_2,
        submodule_3,
        root_question_1,
        root_question_3,
        indicator_2,
    ):
        root_question_1.relevant = f"${{{root_question_3.name}}}"
        root_question_1.save(update_fields=["relevant"])
        validator = SubmodulesOrderValidator(
            [submodule_1.id],
            [indicator_2.id],
            [submodule_1.id, submodule_2.id, submodule_3.id],
        )

        validator.process()

        assert validator.get_issues() == []

    def test_process_reports_structural_and_repeat_dependencies(
        self,
        submodule_1,
        submodule_2,
        root_question_3,
        repeat_section_1,
    ):
        module = submodule_1.module
        module.relevant = f"${{{root_question_3.name}}}"
        module.save(update_fields=["relevant"])
        submodule_1.relevant = f"${{{root_question_3.name}}}"
        submodule_1.save(update_fields=["relevant"])
        repeat_section_1.relevant = f"${{{root_question_3.name}}}"
        repeat_section_1.repeat_count = f"${{{root_question_3.name}}}"
        repeat_section_1.save(update_fields=["relevant", "repeat_count"])
        validator = SubmodulesOrderValidator(
            [submodule_1.id],
            [],
            [submodule_1.id, submodule_2.id],
        )

        validator.process()

        assert [
            (issue.owner["model"], issue.field) for issue in validator.get_issues()
        ] == [
            ("Module", "relevant"),
            ("Submodule", "relevant"),
            ("RepeatSection", "relevant"),
            ("RepeatSection", "repeat_count"),
        ]

    def test_process_reports_unresolved_expression_reference(
        self,
        submodule_1,
        root_question_1,
    ):
        root_question_1.relevant = "${QuestionThatDoesNotExist}"
        root_question_1.save(update_fields=["relevant"])
        validator = SubmodulesOrderValidator([submodule_1.id], [], [submodule_1.id])

        validator.process()

        assert [issue.code for issue in validator.get_issues()] == [
            "SELECTED_SCOPE_DEPENDENCY_UNRESOLVED"
        ]
        assert "no exact question with that name exists" in validator.get_messages()[0]

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
        root_question_1.relevant = f"${{{root_question_3.name}}}"
        root_question_1.constraint = f"${{{root_question_4.name}}}"
        root_question_1.save(update_fields=["relevant", "constraint"])

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
