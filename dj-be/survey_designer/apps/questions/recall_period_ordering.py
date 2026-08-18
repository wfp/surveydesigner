import re

from django.db.models import Case, CharField, F, Func, Value, When
from django.db.models.functions import Cast, Collate, Concat, Length, LPad, Substr
from django.db.models.lookups import Regex
from django.forms.models import ModelChoiceIterator

# Recall periods are user-managed names. Only positive integer values with one
# of the supported units participate in semantic ordering.
_RECALL_PERIOD_PATTERN = r"^_[0-9]*[1-9][0-9]*[DMY]$"
_RECALL_PERIOD_NAME_PATTERN = re.compile(_RECALL_PERIOD_PATTERN)
_RECALL_PERIOD_UNIT_ORDER = {"D": 0, "M": 1, "Y": 2}
_RECALL_PERIOD_UNIT_PATTERNS = {
    unit: rf"^_[0-9]*[1-9][0-9]*{unit}$" for unit in _RECALL_PERIOD_UNIT_ORDER
}


def recall_period_sort_key(recall_period):
    """Return the shared in-memory ordering key for a recall period."""
    name = recall_period.name
    match = _RECALL_PERIOD_NAME_PATTERN.fullmatch(name)
    if match:
        number_text = match.group(0)[1:-1].lstrip("0")
        if number_text:
            unit = name[-1]
            return (
                0,
                _RECALL_PERIOD_UNIT_ORDER[unit],
                int(number_text),
                name,
                recall_period.pk,
            )

    return (1, 0, 0, name, recall_period.pk)


class RecallPeriodModelChoiceIterator(ModelChoiceIterator):
    """Keep model-choice validation while semantically ordering its options."""

    def __iter__(self):
        if self.field.empty_label is not None:
            yield ("", self.field.empty_label)

        queryset = self.queryset
        if not queryset._prefetch_related_lookups:
            queryset = queryset.iterator()

        for obj in sorted(queryset, key=recall_period_sort_key):
            yield self.choice(obj)


def order_recall_period_field(field):
    """Configure a model-choice field to use semantic recall-period order."""
    field.iterator = RecallPeriodModelChoiceIterator
    field.widget.choices = field.choices
    return field


class _TrimLeadingZeros(Func):
    function = "LTRIM"
    output_field = CharField()

    def __init__(self, expression):
        super().__init__(expression, Value("0"))


def recall_period_ordering_expression(name_field="name"):
    """Build a database-side expression suitable for admin column ordering.

    Numeric values are represented by their significant-digit length followed
    by their digits, which avoids integer-width limits while retaining numeric
    ordering. The expression starts special/malformed names after valid ones.
    """
    # RecallPeriod.name uses the project's nondeterministic ICU collation.
    # PostgreSQL rejects regex operations on such a collation, so explicitly
    # use the deterministic C collation for validation and string operations.
    name = Collate(F(name_field), "C")
    valid_name = Regex(name, _RECALL_PERIOD_PATTERN)
    valid_unit_patterns = {
        unit: Regex(name, pattern)
        for unit, pattern in _RECALL_PERIOD_UNIT_PATTERNS.items()
    }
    number_text = Substr(name, 2, Length(name) - 2)
    significant_number = _TrimLeadingZeros(number_text)
    number_length = LPad(
        Cast(Length(significant_number), CharField()),
        3,
        Value("0"),
    )
    unit_order = Case(
        When(
            valid_unit_patterns["D"],
            then=Value("0"),
        ),
        When(
            valid_unit_patterns["M"],
            then=Value("1"),
        ),
        default=Value("2"),
        output_field=CharField(),
    )
    valid_order = Case(
        When(
            valid_name,
            then=Concat(
                Value("0:"),
                unit_order,
                Value(":"),
                number_length,
                Value(":"),
                significant_number,
                Value(":"),
                name,
            ),
        ),
        default=Concat(Value("1:"), name),
        output_field=CharField(),
    )
    return valid_order


def order_recall_period_queryset(queryset, name_field="name"):
    """Apply semantic ordering without materializing a paginated queryset."""
    return queryset.order_by(recall_period_ordering_expression(name_field), "pk")
