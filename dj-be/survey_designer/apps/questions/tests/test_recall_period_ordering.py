from types import SimpleNamespace

from django import forms
from questions.models import RecallPeriod
from questions.recall_period_ordering import (
    order_recall_period_field,
    order_recall_period_queryset,
    recall_period_sort_key,
)


def test_recall_period_sort_key_groups_units_and_numbers_with_fallback():
    names = [
        "_5Y",
        "_2M",
        "_7D",
        "_1M",
        "_6M",
        "_Tot",
        "_3M",
        "_1Y",
        "_10D",
        "_0D",
        "_00D",
        "_01d",
    ]
    periods = [SimpleNamespace(name=name, pk=index) for index, name in enumerate(names)]

    assert [period.name for period in sorted(periods, key=recall_period_sort_key)] == [
        "_7D",
        "_10D",
        "_1M",
        "_2M",
        "_3M",
        "_6M",
        "_1Y",
        "_5Y",
        "_00D",
        "_01d",
        "_0D",
        "_Tot",
    ]


def test_recall_period_model_choice_field_keeps_blank_and_validation(db):
    for name in ("_2M", "_7D", "_Tot", "_1M"):
        RecallPeriod.objects.create(name=name, description=name)

    field = forms.ModelChoiceField(queryset=RecallPeriod.objects.all(), required=False)
    order_recall_period_field(field)

    choices = list(field.choices)
    assert choices[0][0] == ""
    assert [label for _, label in choices[1:]] == ["_7D", "_1M", "_2M", "_Tot"]
    assert field.clean(str(RecallPeriod.objects.get(name="_1M").pk)).name == "_1M"


def test_recall_period_queryset_ordering_is_semantic_and_database_side(db):
    for name in (
        "_5Y",
        "_2M",
        "_10D",
        "_7D",
        "_Tot",
        "_1M",
        "_0D",
        "_01d",
        "malformed",
    ):
        RecallPeriod.objects.create(name=name, description=name)

    assert list(
        order_recall_period_queryset(RecallPeriod.objects.all()).values_list(
            "name", flat=True
        )
    ) == [
        "_7D",
        "_10D",
        "_1M",
        "_2M",
        "_5Y",
        "_01d",
        "_0D",
        "_Tot",
        "malformed",
    ]


def test_recall_period_queryset_validates_against_deterministic_collation(db):
    query = order_recall_period_queryset(RecallPeriod.objects.all()).query
    sql, params = query.sql_with_params()

    assert 'COLLATE "C"' in sql
    assert " ~ %s" in sql
    assert "^_[0-9]*[1-9][0-9]*[DMY]$" in params
