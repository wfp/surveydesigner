import pytest
from questions.services.expression_validation import (
    DependencyEdge,
    ExpressionContext,
    cycle_dependency_names,
    dependency_cycle_issue,
    expression_dependency_names,
    find_dependency_cycles,
    lint_expression,
)

OWNER = {"model": "RootQuestion", "id": 1, "name": "owner"}
REPEAT_NAMES = {
    "member": frozenset({"household"}),
    "household": frozenset({"household"}),
}


def _context(field="relevant", **kwargs):
    return ExpressionContext(owner=OWNER, field=field, **kwargs)


def _codes(expression, **kwargs):
    return [issue.code for issue in lint_expression(expression, _context(**kwargs))]


@pytest.mark.parametrize(
    "expression, code",
    (
        ("${valid_question} =", "EXPRESSION_INCOMPLETE"),
        ("${q} and", "EXPRESSION_INCOMPLETE"),
        ("${q} = 1 or", "EXPRESSION_INCOMPLETE"),
        ("1 +", "EXPRESSION_INCOMPLETE"),
        ("(${q}", "EXPRESSION_INCOMPLETE"),
        ("concat(${q},", "EXPRESSION_INCOMPLETE"),
        ("'abc", "EXPRESSION_INCOMPLETE"),
        ("${q})", "EXPRESSION_SYNTAX_INVALID"),
        ("${q} ${r}", "EXPRESSION_SYNTAX_INVALID"),
        ("${q} in options", "EXPRESSION_SYNTAX_INVALID"),
        ("= 1", "EXPRESSION_SYNTAX_INVALID"),
        ("${q} = $r", "EXPRESSION_SYNTAX_INVALID"),
        ("${q", "EXPRESSION_REFERENCE_UNTERMINATED"),
        ("round(${q) div 2.0)", "EXPRESSION_REFERENCE_UNTERMINATED"),
        ("'${q' = 1", "EXPRESSION_REFERENCE_UNTERMINATED"),
        ("${a${b}}", "EXPRESSION_REFERENCE_NESTED"),
        ("${1bad}", "EXPRESSION_REFERENCE_INVALID"),
        ("${ q }", "EXPRESSION_REFERENCE_INVALID"),
        ("${}", "EXPRESSION_REFERENCE_INVALID"),
        ("${a:b}", "EXPRESSION_REFERENCE_INVALID"),
    ),
)
def test_malformed_expression_is_rejected(expression, code):
    issues = lint_expression(expression, _context())

    assert [issue.code for issue in issues] == [code]
    assert issues[0].owner == OWNER
    assert issues[0].field == "relevant"
    assert issues[0].layer == "model"


def test_incomplete_comparison_message_names_the_dangling_operator():
    (issue,) = lint_expression("${valid_question} =", _context())

    assert issue.message == (
        "RootQuestion 'owner' field 'relevant' is incomplete after '='; "
        "expected a value, reference, or function."
    )


@pytest.mark.parametrize(
    "expression",
    (
        ". >= 0 and . <= 7",
        "${q} != ''",
        "selected(${q}, 'a')",
        "not(selected(${q}, 'a'))",
        "if(${q} > 1, 'y', 'n')",
        "jr:choice-name(${q}, '${q}')",
        "count(${q}) > 0",
        "instance('cities')/root/item[name = ${q}]/label",
        "${last-saved#q} = 1",
        "regex(., '^[0-9]{3}$')",
        "today() - ${q} > 365",
        "${q} div 2 mod 3",
        "-1 * ${q}",
        "string-length(.) <= 5",
        "choice_filter_name = ${q}",
        "position(..) = 1",
        "/data/q = 1",
        "${q}[1] = 1",
        "coalesce(${q}, 0)",
    ),
)
def test_valid_expression_is_accepted(expression):
    assert _codes(expression) == []


@pytest.mark.parametrize(
    "field, value, question_type",
    (
        ("required", "yes", ""),
        ("read_only", "No", ""),
        ("relevant", "TRUE", ""),
        ("default", "some text", "text"),
        ("default", "2024-01-31", "date"),
    ),
)
def test_static_values_are_not_parsed_as_expressions(field, value, question_type):
    assert _codes(value, field=field, question_type=question_type) == []


@pytest.mark.parametrize(
    "value, code",
    (
        ("${missing", "EXPRESSION_REFERENCE_UNTERMINATED"),
        ("${1bad}", "EXPRESSION_REFERENCE_INVALID"),
    ),
)
def test_default_with_malformed_reference_is_rejected(value, code):
    assert _codes(value, field="default", question_type="text") == [code]


def test_dynamic_default_is_parsed_as_an_expression():
    assert _codes("${q} +", field="default", question_type="integer") == [
        "EXPRESSION_INCOMPLETE"
    ]


def test_references_resolve_exactly_and_case_sensitively():
    names = frozenset({"Household_Size"})

    assert _codes("${Household_Size} > 0", available_names=names) == []
    (issue,) = lint_expression("${household_size} > 0", _context(available_names=names))
    assert issue.code == "EXPRESSION_REFERENCE_CASE_MISMATCH"
    assert "available exact name: 'Household_Size'" in issue.message
    assert _codes("${missing} > 0", available_names=names) == [
        "EXPRESSION_REFERENCE_UNRESOLVED"
    ]
    assert _codes("${last-saved#missing} = 1", available_names=names) == [
        "EXPRESSION_REFERENCE_UNRESOLVED"
    ]


def test_references_inside_text_values_are_resolved():
    names = frozenset({"Household_Size"})

    assert _codes(
        "jr:choice-name(${Household_Size}, '${household_size}')",
        available_names=names,
    ) == ["EXPRESSION_REFERENCE_CASE_MISMATCH"]


def test_reference_into_repeat_from_outside_requires_an_aggregate():
    (issue,) = lint_expression("${member} > 1", _context(name_repeats=REPEAT_NAMES))

    assert issue.code == "EXPRESSION_REPEAT_CONTEXT_INVALID"
    assert "inside repeat 'household' from outside that repeat" in issue.message


@pytest.mark.parametrize(
    "expression",
    (
        "count(${member}) > 1",
        "sum(${member}) > 1",
        "indexed-repeat(${member}, ${household}, 1) > 1",
        "count(${household}) > 0",
    ),
)
def test_aggregated_repeat_reference_is_accepted(expression):
    assert _codes(expression, name_repeats=REPEAT_NAMES) == []


@pytest.mark.parametrize("expression", ("${member}[1] > 1", "${member}[true()] + 1"))
def test_predicate_does_not_narrow_repeated_values(expression):
    assert _codes(expression, name_repeats=REPEAT_NAMES) == [
        "EXPRESSION_REPEAT_CONTEXT_INVALID"
    ]


def test_reference_within_the_same_repeat_is_accepted():
    assert (
        _codes(
            "${member} > 1",
            repeats=frozenset({"household"}),
            name_repeats=REPEAT_NAMES,
        )
        == []
    )


def test_quoted_reference_to_own_member_is_not_a_repeat_dependency():
    assert (
        _codes(
            "'${member}' != ''",
            own_members=frozenset({"member"}),
            name_repeats=REPEAT_NAMES,
        )
        == []
    )


@pytest.mark.parametrize("expression", ("${member}", "count(${member})"))
def test_repeat_fields_cannot_depend_on_their_own_members(expression):
    assert _codes(
        expression,
        field="repeat_count",
        own_members=frozenset({"member"}),
        name_repeats=REPEAT_NAMES,
    ) == ["EXPRESSION_REPEAT_CONTEXT_INVALID"]


@pytest.mark.parametrize(
    "expression",
    ("${size} > 0", "'many'", "-1", "2.5", "today()", "true()", "uuid()"),
)
def test_repeat_count_must_be_a_whole_number(expression):
    assert _codes(expression, field="repeat_count") == [
        "EXPRESSION_RESULT_TYPE_INVALID"
    ]


@pytest.mark.parametrize(
    "expression",
    ("5", "${size}", "${size} + 1", "count(${size})", "int(${size} div 2)", "'3'"),
)
def test_numeric_repeat_count_is_accepted(expression):
    assert (
        _codes(expression, field="repeat_count", name_types={"size": "integer"}) == []
    )


def test_repeat_count_reference_must_be_a_numeric_question():
    (issue,) = lint_expression(
        "${size}",
        _context(field="repeat_count", name_types={"size": "select_multiple"}),
    )

    assert issue.code == "EXPRESSION_RESULT_TYPE_INVALID"
    assert "of type 'select_multiple'" in issue.message


@pytest.mark.parametrize("question_type", ("select_one", "barcode", "note"))
def test_repeat_count_accepts_questions_that_may_hold_a_number(question_type):
    assert (
        _codes("${size}", field="repeat_count", name_types={"size": question_type})
        == []
    )


def test_numeric_calculation_cannot_assign_text():
    assert _codes("'abc'", field="calculation", question_type="integer") == [
        "EXPRESSION_RESULT_TYPE_INVALID"
    ]
    assert _codes("uuid()", field="calculation", question_type="decimal") == [
        "EXPRESSION_RESULT_TYPE_INVALID"
    ]
    assert _codes("uuid()", field="calculation", question_type="text") == []
    assert (
        _codes("concat('1', '2')", field="calculation", question_type="integer") == []
    )
    assert _codes("'5'", field="calculation", question_type="integer") == []
    assert _codes("'abc'", field="calculation", question_type="text") == []


def test_dependency_names_are_exact_and_ignore_invalid_logic():
    assert expression_dependency_names(
        "${a} > ${B} and ${last-saved#c} = 1", "relevant"
    ) == {"a", "B"}
    assert expression_dependency_names(
        "jr:choice-name(${a}, '${a}')", "calculation"
    ) == {"a"}
    assert expression_dependency_names("${a} =", "relevant") == frozenset()
    assert expression_dependency_names("${a${b}}", "relevant") == frozenset()
    assert expression_dependency_names("yes", "required") == frozenset()


def _edge(source, target):
    return DependencyEdge(
        source, target, {"model": "question", "name": source}, "calculation"
    )


def test_find_dependency_cycles_reports_each_cycle_once():
    cycles = find_dependency_cycles(
        [
            _edge("a", "b"),
            _edge("b", "c"),
            _edge("c", "a"),
            _edge("c", "d"),
            _edge("d", "e"),
            _edge("x", "x"),
        ]
    )

    assert [[edge.source for edge in cycle] for cycle in cycles] == [
        ["a", "b", "c"],
        ["x"],
    ]


def test_find_dependency_cycles_ignores_acyclic_dependencies():
    assert find_dependency_cycles([_edge("a", "b"), _edge("b", "c")]) == []


def test_dependency_cycle_issue_describes_the_cycle():
    (cycle,) = find_dependency_cycles([_edge("a", "b"), _edge("b", "a")])

    issue = dependency_cycle_issue(cycle, layer="composition")

    assert issue.code == "EXPRESSION_DEPENDENCY_CYCLE"
    assert issue.owner == {"model": "question", "name": "a"}
    assert issue.field == "calculation"
    assert issue.message == (
        "question 'a' field 'calculation' creates a dependency cycle: a -> b -> a."
    )


def test_cycle_dependencies_only_include_values_that_are_read():
    expression = "jr:choice-name(${a}, '${b}') and . != ''"

    assert expression_dependency_names(expression, "relevant") == {"a", "b"}
    assert cycle_dependency_names(expression, "relevant", "owner") == {"a", "owner"}
    assert (
        cycle_dependency_names(
            "count(instance('c')/root/item[name = .])", "calculation", "owner"
        )
        == frozenset()
    )


def test_deeply_nested_expression_keeps_its_references():
    expression = "(" * 300 + "${a} > 1" + ")" * 300

    assert _codes(expression, field="required") == []
    assert expression_dependency_names(expression, "required") == {"a"}
