from organization.models import Organization
from questions.models import RepeatSection, RootQuestion
from questions.services import DataImport


def test_sunny_scenario(admin):
    data_import = DataImport(
        "./survey_designer/apps/questions/tests/files/questions.xlsx",
        admin,
        Organization.objects.filter(id=admin.organization.id),
    )
    data_import.process()
    assert data_import.is_valid()
    (
        created,
        created_choices,
        created_suffixes,
        created_recall_periods,
        created_groups,
        created_indicators,
    ) = data_import.create()
    assert created == 10
    assert RepeatSection.objects.count() == 1
    assert len(created_choices) == 2
    assert len(created_suffixes) == 2
    assert len(created_recall_periods) == 2
    assert RootQuestion.objects.count() == 7
    assert RootQuestion.objects.filter(type="calculate").count() == 1
    assert RootQuestion.objects.exclude(calculation="").count() == 2
    rq_with_constraint = RootQuestion.objects.filter(constraint_message__gt="").first()
    assert rq_with_constraint is not None
    assert rq_with_constraint.constraint_message == "test constraint message"
    assert RootQuestion.objects.exclude(parameters="").count() == 2
