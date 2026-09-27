import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from modules.services import SubmoduleCompositionValidator
from questions.models import RepeatSection


@pytest.mark.django_db
class TestSubmoduleCompositionValidator:
    def test_get_submodules(self, submodule_1, submodule_2, indicator_1):
        submodule_ids = [submodule_1.id]
        indicator_ids = [indicator_1.id]
        all_submodule_ids = [submodule_1.id, submodule_2.id]
        validator = SubmoduleCompositionValidator(
            submodule_ids, indicator_ids, all_submodule_ids
        )
        submodules = validator.get_submodules()

        assert [submodule.id for submodule in submodules] == submodule_ids

    def test_validate(self, submodule_1, submodule_2, indicator_1):
        submodule_ids = [submodule_1.id]
        indicator_ids = [indicator_1.id]
        all_submodule_ids = [submodule_1.id, submodule_2.id]
        validator = SubmoduleCompositionValidator(
            submodule_ids, indicator_ids, all_submodule_ids
        )
        validator.validate()
        # should raise an error on failure

    @pytest.mark.parametrize(
        "field",
        ("relevant", "constraint", "calculation", "choice_filter"),
    )
    def test_validate_dependencies_uses_non_selected_submodules(
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

        validator = SubmoduleCompositionValidator(
            [submodule_1.id],
            [],
            [submodule_1.id, submodule_2.id, submodule_3.id],
        )

        validator.validate()

        assert [issue.code for issue in validator.get_issues()] == [
            "SELECTED_SCOPE_DEPENDENCY_NOT_EMITTED"
        ]
        issue = validator.get_issues()[0]
        assert issue.owner == {
            "model": "RootQuestion",
            "id": root_question_1.id,
            "name": root_question_1.name,
        }
        assert issue.submodule == {
            "model": "Submodule",
            "id": submodule_1.id,
            "name": submodule_1.name,
            "label": submodule_1.label,
        }
        assert issue.dependency == {
            "name": root_question_3.name,
            "status": "not_emitted",
            "target": {
                "model": "RootQuestion",
                "id": root_question_3.id,
                "name": root_question_3.name,
            },
            "available_submodules": [
                {
                    "model": "Submodule",
                    "id": submodule_2.id,
                    "name": submodule_2.name,
                    "label": submodule_2.label,
                },
                {
                    "model": "Submodule",
                    "id": submodule_3.id,
                    "name": submodule_3.name,
                    "label": submodule_3.label,
                },
            ],
        }
        assert issue.field == field
        assert submodule_1 in validator.dependency_results
        assert (
            submodule_2
            in validator.dependency_results[submodule_1]["related_submodules"]
        )
        assert (
            submodule_3
            in validator.dependency_results[submodule_1]["related_submodules"]
        )
        assert [
            dependency.name
            for dependency in validator.dependency_results[submodule_1]["dependencies"]
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
        validator = SubmoduleCompositionValidator(
            [submodule_1.id, submodule_2.id],
            [],
            [submodule_1.id, submodule_2.id, submodule_3.id],
        )

        validator.validate()

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
        validator = SubmoduleCompositionValidator(
            [submodule_1.id],
            [indicator_2.id],
            [submodule_1.id, submodule_2.id, submodule_3.id],
        )

        validator.validate()

        assert validator.get_issues() == []

    def test_validate_reports_structural_and_repeat_dependencies(
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
        validator = SubmoduleCompositionValidator(
            [submodule_1.id],
            [],
            [submodule_1.id, submodule_2.id],
        )

        validator.validate()

        assert [
            (issue.owner["model"], issue.field) for issue in validator.get_issues()
        ] == [
            ("Module", "relevant"),
            ("Submodule", "relevant"),
            ("RepeatSection", "relevant"),
            ("RepeatSection", "repeat_count"),
        ]

    def test_validate_reports_unresolved_expression_reference(
        self,
        submodule_1,
        root_question_1,
    ):
        root_question_1.relevant = "${QuestionThatDoesNotExist}"
        root_question_1.save(update_fields=["relevant"])
        validator = SubmoduleCompositionValidator(
            [submodule_1.id], [], [submodule_1.id]
        )

        validator.validate()

        assert [issue.code for issue in validator.get_issues()] == [
            "SELECTED_SCOPE_DEPENDENCY_UNRESOLVED"
        ]
        issue = validator.get_issues()[0]
        assert "no question with that exact name exists" in issue.message
        assert issue.dependency == {
            "name": "QuestionThatDoesNotExist",
            "status": "unresolved",
        }

    def test_validate_reports_dependency_outside_available_scope(
        self,
        submodule_1,
        root_question_1,
        root_question_3,
    ):
        root_question_1.relevant = f"${{{root_question_3.name}}}"
        root_question_1.save(update_fields=["relevant"])
        validator = SubmoduleCompositionValidator(
            [submodule_1.id], [], [submodule_1.id]
        )

        issues = validator.validate()

        assert [issue.code for issue in issues] == [
            "SELECTED_SCOPE_DEPENDENCY_UNAVAILABLE"
        ]
        assert "unavailable in the current survey scope" in issues[0].message
        assert issues[0].dependency == {
            "name": root_question_3.name,
            "status": "unavailable",
        }

    def test_validate_reports_dependency_case_mismatch(
        self,
        submodule_1,
        submodule_2,
        root_question_1,
        root_question_3,
    ):
        root_question_1.relevant = f"${{{root_question_3.name.lower()}}}"
        root_question_1.save(update_fields=["relevant"])
        validator = SubmoduleCompositionValidator(
            [submodule_1.id],
            [],
            [submodule_1.id, submodule_2.id],
        )

        issues = validator.validate()

        assert [issue.code for issue in issues] == [
            "SELECTED_SCOPE_DEPENDENCY_CASE_MISMATCH"
        ]
        assert f"available exact name: '{root_question_3.name}'" in issues[0].message
        assert issues[0].dependency == {
            "name": root_question_3.name.lower(),
            "status": "case_mismatch",
            "available_names": [root_question_3.name],
        }

    def test_validate_reports_ambiguous_dependency(
        self,
        submodule_1,
        submodule_2,
        root_question_1,
        root_question_3,
    ):
        repeat = RepeatSection.objects.create(
            name=root_question_3.name,
            label="Ambiguous repeat",
            repeat_count="1",
        )
        repeat.submodule.add(submodule_2)
        root_question_1.relevant = f"${{{root_question_3.name}}}"
        root_question_1.save(update_fields=["relevant"])
        validator = SubmoduleCompositionValidator(
            [submodule_1.id],
            [],
            [submodule_1.id, submodule_2.id],
        )

        issues = validator.validate()

        assert [issue.code for issue in issues] == [
            "SELECTED_SCOPE_DEPENDENCY_AMBIGUOUS"
        ]
        assert f"RootQuestion #{root_question_3.id}" in issues[0].message
        assert f"RepeatSection #{repeat.id}" in issues[0].message
        assert issues[0].dependency == {
            "name": root_question_3.name,
            "status": "ambiguous",
            "candidates": [
                {
                    "model": "RepeatSection",
                    "id": repeat.id,
                    "name": repeat.name,
                },
                {
                    "model": "RootQuestion",
                    "id": root_question_3.id,
                    "name": root_question_3.name,
                },
            ],
        }

    def test_validate_reports_inactive_dependency(
        self,
        submodule_1,
        submodule_2,
        root_question_1,
        root_question_3,
    ):
        root_question_3.is_active = False
        root_question_3.save(update_fields=["is_active"])
        root_question_1.calculation = f"${{{root_question_3.name}}}"
        root_question_1.save(update_fields=["calculation"])
        validator = SubmoduleCompositionValidator(
            [submodule_1.id, submodule_2.id],
            [],
            [submodule_1.id, submodule_2.id],
        )

        issues = validator.validate()

        assert [issue.code for issue in issues] == ["SELECTED_SCOPE_DEPENDENCY_INVALID"]
        assert issues[0].field == "calculation"
        assert "is inactive" in issues[0].message
        assert issues[0].dependency == {
            "name": root_question_3.name,
            "status": "invalid",
            "reason": "inactive",
            "target": {
                "model": "RootQuestion",
                "id": root_question_3.id,
                "name": root_question_3.name,
            },
        }

    def test_validate_checks_selected_indicator_subquestion_expressions(
        self,
        submodule_1,
        submodule_2,
        root_question_3,
        sub_question_1,
        indicator_1,
    ):
        sub_question_1.constraint = f"${{{root_question_3.name}}} > 0"
        sub_question_1.save(update_fields=["constraint"])
        validator = SubmoduleCompositionValidator(
            [submodule_1.id],
            [indicator_1.id],
            [submodule_1.id, submodule_2.id],
        )

        issues = validator.validate()

        assert [issue.code for issue in issues] == [
            "SELECTED_SCOPE_DEPENDENCY_NOT_EMITTED"
        ]
        assert issues[0].owner == {
            "model": "SubQuestion",
            "id": sub_question_1.id,
            "name": sub_question_1.name,
        }
        assert issues[0].submodule == {
            "model": "Submodule",
            "id": submodule_1.id,
            "name": submodule_1.name,
            "label": submodule_1.label,
        }
        assert issues[0].field == "constraint"

    def test_validate_reports_incompatible_selected_submodules(
        self,
        submodule_2,
        submodule_3,
        root_question_3,
    ):
        validator = SubmoduleCompositionValidator(
            [submodule_2.id, submodule_3.id],
            [],
            [submodule_2.id, submodule_3.id],
        )

        issues = validator.validate()

        assert root_question_3.submodule.count() == 2
        assert [issue.code for issue in issues] == ["SELECTED_SCOPE_SUBMODULE_CONFLICT"]
        assert issues[0].owner == {
            "model": "Submodule",
            "id": submodule_3.id,
            "name": submodule_3.name,
        }
        assert issues[0].submodule == {
            "model": "Submodule",
            "id": submodule_3.id,
            "name": submodule_3.name,
            "label": submodule_3.label,
        }
        assert issues[0].dependency == {
            "status": "conflict",
            "submodules": [
                {
                    "model": "Submodule",
                    "id": submodule_2.id,
                    "name": submodule_2.name,
                    "label": submodule_2.label,
                }
            ],
        }

    def test_validate_uses_bounded_queries(
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

        validator = SubmoduleCompositionValidator(
            [submodule_1.id, submodule_2.id],
            [indicator_1.id],
            [submodule_1.id, submodule_2.id, submodule_3.id],
        )

        with CaptureQueriesContext(connection) as queries:
            validator.validate()
            validator.get_messages()

        # Current optimized path is single-digit queries in local profiling.
        assert len(queries) <= 10
