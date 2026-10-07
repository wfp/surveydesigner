"""Static validation for XLSForm expressions on codebook records.

Expressions are parsed with the XPath 1.0 grammar plus pyxform ``${name}``
references, so malformed logic is rejected before it can be emitted into an
XLSForm. The checks are deliberately limited to what can be decided without
evaluating the form: syntax and completeness, exact references, result type,
repeat context, and dependency cycles. This module does not touch the
database; callers supply the names and repeat structure that are in scope.
"""

from __future__ import annotations

import dataclasses
import re
from collections import defaultdict, deque
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Iterable, Mapping, Sequence

from pyxform.aliases import BINDING_CONVERSIONS
from pyxform.utils import default_is_dynamic

from .form_validation import ValidationIssue

QUESTION_EXPRESSION_FIELDS = (
    "relevant",
    "constraint",
    "required",
    "read_only",
    "default",
    "choice_filter",
    "calculation",
)
REPEAT_EXPRESSION_FIELDS = ("relevant", "repeat_count")
SURVEY_EXPRESSION_COLUMNS = (*QUESTION_EXPRESSION_FIELDS, "repeat_count")
# Fields JavaRosa evaluates as triggerables; references between them must not
# form a cycle.
DEPENDENCY_CYCLE_FIELDS = frozenset(
    ("calculation", "relevant", "required", "read_only")
)
# pyxform rewrites yes/no style values in these bind columns to true()/false().
_BINDING_FIELDS = frozenset(
    ("relevant", "constraint", "required", "read_only", "calculation")
)
NUMERIC_QUESTION_TYPES = frozenset(("integer", "decimal"))
# Question types whose value is never a single number, so cannot be a repeat
# count. Single selects, barcodes and notes may hold numeric values.
NON_NUMERIC_QUESTION_TYPES = frozenset(
    (
        "acknowledge",
        "audio",
        "background-audio",
        "date",
        "dateTime",
        "geopoint",
        "geoshape",
        "geotrace",
        "group",
        "image",
        "rank",
        "repeat",
        "select_multiple",
        "select_multiple_from_file",
        "time",
        "video",
    )
)
# Functions that legitimately consume every value of a repeated question.
_AGGREGATE_FUNCTIONS = frozenset(
    (
        "count",
        "count-non-empty",
        "distinct-values",
        "indexed-repeat",
        "join",
        "max",
        "min",
        "sum",
    )
)
_FUNCTION_RESULT_TYPES = {
    **dict.fromkeys(
        (
            "boolean",
            "boolean-from-string",
            "checklist",
            "contains",
            "ends-with",
            "false",
            "lang",
            "not",
            "regex",
            "selected",
            "starts-with",
            "true",
            "weighted-checklist",
        ),
        "boolean",
    ),
    **dict.fromkeys(("date", "today"), "date"),
    **dict.fromkeys(("date-time", "now"), "dateTime"),
    **dict.fromkeys(
        (
            "abs",
            "acos",
            "area",
            "asin",
            "atan",
            "atan2",
            "ceiling",
            "cos",
            "count",
            "count-non-empty",
            "count-selected",
            "decimal-date-time",
            "decimal-time",
            "distance",
            "exp",
            "exp10",
            "floor",
            "int",
            "last",
            "log",
            "log10",
            "max",
            "min",
            "number",
            "pi",
            "position",
            "pow",
            "random",
            "round",
            "sin",
            "sqrt",
            "string-length",
            "sum",
            "tan",
        ),
        "number",
    ),
    **dict.fromkeys(
        (
            "base64-decode",
            "concat",
            "format-date",
            "format-date-time",
            "jr:choice-name",
            "join",
            "normalize-space",
            "selected-at",
            "string",
            "substr",
            "substring",
            "substring-after",
            "substring-before",
            "translate",
        ),
        "string",
    ),
    # Text that can never be read as a number.
    **dict.fromkeys(("digest", "uuid"), "text"),
}

_NAME_START_CHARS = "A-Z_a-zÀ-ÖØ-öø-˿Ͱ-ͽͿ-῿" "‌-‍⁰-↏Ⰰ-⿯、-퟿豈-﷏ﷰ-�"
_NCNAME = rf"[{_NAME_START_CHARS}][{_NAME_START_CHARS}\-.0-9·̀-ͯ‿-⁀]*"
_NAME_TOKEN = re.compile(rf"{_NCNAME}(?::(?:{_NCNAME}|\*))?")
_NUMBER_TOKEN = re.compile(r"\d+(?:\.\d*)?|\.\d+")
_REFERENCE_NAME = re.compile(rf"(?P<last_saved>last-saved#)?(?P<name>{_NCNAME})")
_EMBEDDED_REFERENCE = re.compile(r"\$\{([^}]*)\}")
# Longest symbols first so that e.g. "<=" is not read as "<" followed by "=".
_SYMBOLS = (
    "!=",
    "<=",
    ">=",
    "//",
    "..",
    "::",
    "=",
    "<",
    ">",
    "/",
    ".",
    "(",
    ")",
    "[",
    "]",
    ",",
    "@",
    "|",
    "+",
    "-",
    "*",
)
_OPERATOR_SYMBOLS = frozenset(("=", "!=", "<", "<=", ">", ">=", "|", "+", "-"))
_OPERATOR_NAMES = frozenset(("and", "or", "mod", "div"))
_NODE_TYPES = frozenset(("comment", "text", "processing-instruction", "node"))
# XPath 1.0 section 3.7: after these tokens (or at the start), "*" is a name
# test and an NCName is a name rather than an operator.
_OPERAND_EXPECTED_AFTER = frozenset(("@", "::", "(", "[", ",", "op", "path"))


@dataclass(frozen=True)
class ExpressionReference:
    name: str
    last_saved: bool = False
    # Wrapped in an aggregate such as count().
    aggregated: bool = False
    # Inside a text value: pyxform substitutes a constant path, nothing is read.
    in_text: bool = False


@dataclass(frozen=True)
class ExpressionAnalysis:
    references: tuple[ExpressionReference, ...] = ()
    result_type: str = "any"
    error_code: str | None = None
    error_message: str | None = None
    # The literal value when the whole expression is one string or number.
    constant: Any = None
    # Reads the owner's own value through ".".
    reads_context: bool = False

    @property
    def valid(self) -> bool:
        return self.error_code is None


@dataclass(frozen=True)
class ExpressionContext:
    """Where an expression lives and which names it may reference.

    ``available_names`` is the codebook scope for reference resolution; when it
    is ``None`` references are not resolved (for example when the final
    artifact's emitted names are checked separately).
    """

    owner: Mapping[str, Any]
    field: str
    question_type: str = ""
    layer: str = "model"
    available_names: frozenset[str] | None = None
    # Repeats that evaluate this expression.
    repeats: frozenset[str] = frozenset()
    # For a repeat's own fields: the names emitted inside that repeat.
    own_members: frozenset[str] = frozenset()
    name_repeats: Mapping[str, frozenset[str]] = dataclasses.field(default_factory=dict)
    name_types: Mapping[str, str] = dataclasses.field(default_factory=dict)
    sheet: str | None = None
    row: int | None = None
    column: str | None = None

    def issue(self, code: str, message: str) -> ValidationIssue:
        owner_name = self.owner.get("name")
        model = self.owner.get("model", "Question")
        label = f"{model} '{owner_name}'" if owner_name else model
        return ValidationIssue(
            code=code,
            layer=self.layer,
            severity="error",
            message=f"{label} field '{self.field}' {message}",
            owner=dict(self.owner),
            field=self.field,
            sheet=self.sheet,
            row=self.row,
            column=self.column,
        )


@dataclass(frozen=True)
class DependencyEdge:
    """``source`` depends on ``target`` through ``owner``'s ``field``."""

    source: str
    target: str
    owner: Mapping[str, Any]
    field: str
    row: int | None = None


class _ExpressionError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class _Token:
    kind: str
    value: str
    start: int

    @property
    def display(self) -> str:
        if self.kind == "reference":
            return f"${{{self.value}}}"
        return self.value


def _reference_token(
    expression: str, start: int, limit: int | None = None
) -> tuple[_Token, int]:
    end = expression.find("}", start + 2, limit)
    if end == -1:
        raise _ExpressionError(
            "EXPRESSION_REFERENCE_UNTERMINATED",
            f"has a reference starting at position {start + 1} that is not closed with '}}'.",
        )
    nested = expression.find("${", start + 2)
    if nested != -1 and nested < end:
        raise _ExpressionError(
            "EXPRESSION_REFERENCE_NESTED",
            f"has a reference starting at position {start + 1} that contains another reference; references cannot be nested.",
        )
    inner = expression[start + 2 : end]
    if not _REFERENCE_NAME.fullmatch(inner):
        raise _ExpressionError(
            "EXPRESSION_REFERENCE_INVALID",
            f"contains invalid reference '{expression[start:end + 1]}'; a reference must be ${{name}} where the name starts with a letter or underscore.",
        )
    return _Token("reference", inner, start), end + 1


def _reference(
    value: str, *, aggregated: bool, in_text: bool = False
) -> ExpressionReference:
    match = _REFERENCE_NAME.fullmatch(value)
    return ExpressionReference(
        match.group("name"),
        last_saved=bool(match.group("last_saved")),
        aggregated=aggregated,
        in_text=in_text,
    )


def _tokenize(expression: str) -> list[_Token]:
    tokens: list[_Token] = []
    index = 0
    while index < len(expression):
        char = expression[index]
        if char.isspace():
            index += 1
            continue

        operand_expected = not tokens or tokens[-1].kind in _OPERAND_EXPECTED_AFTER
        if expression.startswith("${", index):
            token, index = _reference_token(expression, index)
        elif char in "'\"":
            end = expression.find(char, index + 1)
            if end == -1:
                raise _ExpressionError(
                    "EXPRESSION_INCOMPLETE",
                    f"has a text value starting at position {index + 1} that is not closed with {char}.",
                )
            # pyxform substitutes references inside text values too, e.g. the
            # second argument of jr:choice-name(${q}, '${q}').
            embedded = expression.find("${", index + 1, end)
            while embedded != -1:
                _, embedded_end = _reference_token(expression, embedded, end)
                embedded = expression.find("${", embedded_end, end)
            token = _Token("literal", expression[index : end + 1], index)
            index = end + 1
        elif match := _NUMBER_TOKEN.match(expression, index):
            token = _Token("number", match.group(), index)
            index = match.end()
        elif match := _NAME_TOKEN.match(expression, index):
            name = match.group()
            index = match.end()
            if not operand_expected:
                if name not in _OPERATOR_NAMES:
                    raise _ExpressionError(
                        "EXPRESSION_SYNTAX_INVALID",
                        f"has unexpected '{name}' at position {match.start() + 1}; expected an operator.",
                    )
                kind = "op"
            else:
                following = index
                while following < len(expression) and expression[following].isspace():
                    following += 1
                if expression.startswith("::", following):
                    kind = "axis"
                elif expression.startswith("(", following):
                    kind = "node_type" if name in _NODE_TYPES else "function"
                else:
                    kind = "name"
            token = _Token(kind, name, match.start())
        else:
            symbol = next(
                (symbol for symbol in _SYMBOLS if expression.startswith(symbol, index)),
                None,
            )
            if symbol is None:
                raise _ExpressionError(
                    "EXPRESSION_SYNTAX_INVALID",
                    f"has unexpected character '{char}' at position {index + 1}.",
                )
            if symbol == "*":
                kind = "name" if operand_expected else "op"
            elif symbol in ("/", "//"):
                kind = "path"
            elif symbol in _OPERATOR_SYMBOLS:
                kind = "op"
            else:
                kind = symbol
            token = _Token(kind, symbol, index)
            index += len(symbol)
        tokens.append(token)
    tokens.append(_Token("end", "", len(expression)))
    return tokens


class _Parser:
    """Recursive-descent parser for XPath 1.0 with pyxform references.

    Each production returns the inferred result type: ``boolean``, ``number``,
    ``string``, ``date``, ``dateTime``, ``node`` (a path or filtered nodeset),
    ``reference`` (a lone ``${name}``), or ``any``.
    """

    def __init__(self, tokens: Sequence[_Token]) -> None:
        self.tokens = tokens
        self.index = 0
        self.functions: list[str] = []
        self.references: list[ExpressionReference] = []
        self.predicate_depth = 0
        self.reads_context = False

    @property
    def token(self) -> _Token:
        return self.tokens[self.index]

    def advance(self) -> _Token:
        token = self.tokens[self.index]
        self.index += 1
        return token

    def at_operator(self, *values: str) -> bool:
        return self.token.kind == "op" and self.token.value in values

    def error(self, expected: str) -> _ExpressionError:
        token = self.token
        if token.kind == "end":
            previous = self.tokens[self.index - 1].display if self.index else ""
            where = f" after '{previous}'" if previous else ""
            return _ExpressionError(
                "EXPRESSION_INCOMPLETE",
                f"is incomplete{where}; expected {expected}.",
            )
        return _ExpressionError(
            "EXPRESSION_SYNTAX_INVALID",
            f"has unexpected '{token.display}' at position {token.start + 1}; expected {expected}.",
        )

    def expect(self, kind: str) -> _Token:
        if self.token.kind != kind:
            raise self.error(f"'{kind}'")
        return self.advance()

    def parse(self) -> str:
        result = self.expr()
        if self.token.kind != "end":
            raise self.error("an operator")
        return result

    def expr(self) -> str:
        return self.or_expr()

    def _binary(self, operand, operators: tuple[str, ...], result_type: str) -> str:
        result = operand()
        while self.at_operator(*operators):
            self.advance()
            operand()
            result = result_type
        return result

    def or_expr(self) -> str:
        return self._binary(self.and_expr, ("or",), "boolean")

    def and_expr(self) -> str:
        return self._binary(self.equality_expr, ("and",), "boolean")

    def equality_expr(self) -> str:
        return self._binary(self.relational_expr, ("=", "!="), "boolean")

    def relational_expr(self) -> str:
        return self._binary(self.additive_expr, ("<", ">", "<=", ">="), "boolean")

    def additive_expr(self) -> str:
        return self._binary(self.multiplicative_expr, ("+", "-"), "number")

    def multiplicative_expr(self) -> str:
        return self._binary(self.unary_expr, ("*", "div", "mod"), "number")

    def unary_expr(self) -> str:
        if self.at_operator("-"):
            self.advance()
            self.unary_expr()
            return "number"
        return self._binary(self.path_expr, ("|",), "node")

    def starts_step(self) -> bool:
        return self.token.kind in ("name", "axis", "node_type", "@", ".", "..")

    def path_expr(self) -> str:
        if self.token.kind == "path":
            separator = self.advance()
            if separator.value == "//" or self.starts_step():
                self.relative_location_path()
            return "node"
        if self.starts_step():
            if self.token.kind == "." and not self.predicate_depth:
                self.reads_context = True
            self.relative_location_path()
            return "node"
        result = self.filter_expr()
        if self.token.kind == "path":
            self.advance()
            self.relative_location_path()
            return "node"
        return result

    def relative_location_path(self) -> None:
        self.step()
        while self.token.kind == "path":
            self.advance()
            self.step()

    def step(self) -> None:
        if self.token.kind in (".", ".."):
            self.advance()
            return
        if self.token.kind == "axis":
            self.advance()
            self.expect("::")
        elif self.token.kind == "@":
            self.advance()
        if self.token.kind == "name":
            self.advance()
        elif self.token.kind == "node_type":
            node_type = self.advance()
            self.expect("(")
            if node_type.value == "processing-instruction" and self.token.kind == (
                "literal"
            ):
                self.advance()
            self.expect(")")
        else:
            raise self.error("a node name")
        while self.token.kind == "[":
            self.predicate()

    def predicate(self) -> None:
        self.expect("[")
        self.predicate_depth += 1
        self.expr()
        self.predicate_depth -= 1
        self.expect("]")

    def filter_expr(self) -> str:
        result = self.primary_expr()
        # A predicate on ${name} applies to each repeated node, so it does not
        # narrow repeated values the way an aggregate does.
        while self.token.kind == "[":
            self.predicate()
            result = "node"
        return result

    def primary_expr(self) -> str:
        token = self.token
        if token.kind == "reference":
            self.advance()
            aggregated = any(
                function in _AGGREGATE_FUNCTIONS for function in self.functions
            )
            self.references.append(_reference(token.value, aggregated=aggregated))
            return "reference"
        if token.kind == "literal":
            self.advance()
            self.references.extend(
                _reference(value, aggregated=True, in_text=True)
                for value in _EMBEDDED_REFERENCE.findall(token.value)
            )
            return "string"
        if token.kind == "number":
            self.advance()
            return "number"
        if token.kind == "(":
            self.advance()
            result = self.expr()
            self.expect(")")
            return result
        if token.kind == "function":
            return self.function_call()
        raise self.error("a value, reference, or function")

    def function_call(self) -> str:
        function = self.advance()
        self.expect("(")
        self.functions.append(function.value)
        if self.token.kind != ")":
            self.expr()
            while self.token.kind == ",":
                self.advance()
                self.expr()
        self.functions.pop()
        self.expect(")")
        return _FUNCTION_RESULT_TYPES.get(function.value, "any")


def _constant(tokens: Sequence[_Token]) -> Any:
    """Return the literal when the expression is a single (signed) value."""

    values = [token for token in tokens if token.kind not in ("(", ")", "end")]
    negative = len(values) == 2 and values[0].kind == "op" and values[0].value == "-"
    if negative:
        values = values[1:]
    if len(values) != 1:
        return None
    token = values[0]
    if token.kind == "number":
        number = float(token.value)
        return -number if negative else number
    if token.kind == "literal" and not negative and "${" not in token.value:
        return token.value[1:-1]
    return None


def _token_references(tokens: Sequence[_Token]) -> tuple[ExpressionReference, ...]:
    references = []
    for token in tokens:
        if token.kind == "reference":
            references.append(_reference(token.value, aggregated=True))
        elif token.kind == "literal":
            references.extend(
                _reference(value, aggregated=True, in_text=True)
                for value in _EMBEDDED_REFERENCE.findall(token.value)
            )
    return tuple(references)


@lru_cache(maxsize=1024)
def analyse_expression(expression: str) -> ExpressionAnalysis:
    """Parse one expression; the result is cached because forms repeat logic."""

    try:
        tokens = _tokenize(expression)
        parser = _Parser(tokens)
        result_type = parser.parse()
    except _ExpressionError as error:
        return ExpressionAnalysis(error_code=error.code, error_message=error.message)
    except RecursionError:
        # Too deeply nested to parse recursively. Keep the references so scope
        # and dependency metadata stay accurate; the final gate still compiles
        # the emitted XPath.
        return ExpressionAnalysis(references=_token_references(tokens))
    return ExpressionAnalysis(
        references=tuple(parser.references),
        result_type=result_type,
        constant=_constant(tokens),
        reads_context=parser.reads_context,
    )


def is_static_value(field_name: str, value: str, question_type: str = "") -> bool:
    """True when pyxform emits the value as a literal rather than an expression."""

    if field_name in _BINDING_FIELDS and value in BINDING_CONVERSIONS:
        return True
    if field_name == "default":
        # pyxform rejects malformed references even in static defaults.
        return "${" not in value and not default_is_dynamic(
            value, question_type or None
        )
    return False


def _valid_analysis(
    expression: Any, field_name: str, question_type: str
) -> ExpressionAnalysis | None:
    text = str(expression or "").strip()
    if not text or is_static_value(field_name, text, question_type):
        return None
    analysis = analyse_expression(text)
    return analysis if analysis.valid else None


def expression_dependency_names(
    expression: Any, field_name: str, question_type: str = ""
) -> frozenset[str]:
    """Exact question names an expression depends on.

    Malformed expressions and static values have no dependencies, so invalid
    logic never leaves misleading dependency metadata. ``last-saved`` values
    come from a previous submission and are not dependencies.
    """

    analysis = _valid_analysis(expression, field_name, question_type)
    if analysis is None:
        return frozenset()
    return frozenset(
        reference.name for reference in analysis.references if not reference.last_saved
    )


def cycle_dependency_names(
    expression: Any, field_name: str, owner_name: str, question_type: str = ""
) -> frozenset[str]:
    """Names whose values an expression reads when it is evaluated.

    References inside text values become constant paths and are not read,
    while "." reads the owner itself.
    """

    analysis = _valid_analysis(expression, field_name, question_type)
    if analysis is None:
        return frozenset()
    names = {
        reference.name
        for reference in analysis.references
        if not reference.last_saved and not reference.in_text
    }
    if analysis.reads_context:
        names.add(owner_name)
    return frozenset(names)


def _reference_issues(
    analysis: ExpressionAnalysis, context: ExpressionContext
) -> list[ValidationIssue]:
    if context.available_names is None:
        return []

    names_by_casefold: dict[str, list[str]] = defaultdict(list)
    for name in context.available_names:
        names_by_casefold[name.casefold()].append(name)

    issues: list[ValidationIssue] = []
    seen: set[str] = set()
    for reference in analysis.references:
        if reference.name in seen or reference.name in context.available_names:
            continue
        seen.add(reference.name)
        candidates = sorted(names_by_casefold.get(reference.name.casefold(), ()))
        if candidates:
            rendered = ", ".join(f"'{name}'" for name in candidates)
            issues.append(
                context.issue(
                    "EXPRESSION_REFERENCE_CASE_MISMATCH",
                    f"references '{reference.name}', but references are case-sensitive; available exact name: {rendered}.",
                )
            )
        else:
            issues.append(
                context.issue(
                    "EXPRESSION_REFERENCE_UNRESOLVED",
                    f"references '{reference.name}', but no question with that exact name exists.",
                )
            )
    return issues


def _repeat_context_issues(
    analysis: ExpressionAnalysis, context: ExpressionContext
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    seen: set[str] = set()
    for reference in analysis.references:
        # Quoted references are constant paths; they read no repeated value.
        if reference.last_saved or reference.in_text or reference.name in seen:
            continue
        if reference.name in context.own_members:
            seen.add(reference.name)
            issues.append(
                context.issue(
                    "EXPRESSION_REPEAT_CONTEXT_INVALID",
                    f"references '{reference.name}', which is inside this repeat; a repeat's {context.field} cannot depend on its own members.",
                )
            )
            continue
        target_repeats = context.name_repeats.get(reference.name, frozenset())
        if (
            not target_repeats
            or reference.aggregated
            or target_repeats & context.repeats
        ):
            continue
        seen.add(reference.name)
        repeat = sorted(target_repeats)[0]
        issues.append(
            context.issue(
                "EXPRESSION_REPEAT_CONTEXT_INVALID",
                f"references '{reference.name}' inside repeat '{repeat}' from outside that repeat; use an aggregate such as count(), sum(), or indexed-repeat() to select its values.",
            )
        )
    return issues


def _is_number(value: Any) -> bool:
    if isinstance(value, float):
        return True
    try:
        float(str(value).strip())
    except ValueError:
        return False
    return True


def _result_type_issues(
    analysis: ExpressionAnalysis, context: ExpressionContext
) -> list[ValidationIssue]:
    if context.field == "repeat_count":
        if analysis.result_type == "reference":
            name = analysis.references[0].name
            target_type = context.name_types.get(name, "")
            if target_type in NON_NUMERIC_QUESTION_TYPES:
                return [
                    context.issue(
                        "EXPRESSION_RESULT_TYPE_INVALID",
                        f"references '{name}' of type '{target_type}', which cannot provide a numeric repeat count.",
                    )
                ]
            return []
        constant = analysis.constant
        if isinstance(constant, float) and (constant < 0 or not constant.is_integer()):
            return [
                context.issue(
                    "EXPRESSION_RESULT_TYPE_INVALID",
                    "must be a non-negative whole number.",
                )
            ]
        if analysis.result_type in ("boolean", "date", "dateTime", "text") or (
            isinstance(constant, str) and not _is_number(constant)
        ):
            result = (
                "text"
                if isinstance(constant, str) or analysis.result_type == "text"
                else f"a {analysis.result_type}"
            )
            return [
                context.issue(
                    "EXPRESSION_RESULT_TYPE_INVALID",
                    f"must evaluate to a number, but it evaluates to {result}.",
                )
            ]
        return []

    if (
        context.field != "calculation"
        or context.question_type not in NUMERIC_QUESTION_TYPES
    ):
        return []
    if isinstance(analysis.constant, str) and not _is_number(analysis.constant):
        return [
            context.issue(
                "EXPRESSION_RESULT_TYPE_INVALID",
                f"assigns text '{analysis.constant}' to a {context.question_type} question.",
            )
        ]
    if analysis.result_type == "text":
        return [
            context.issue(
                "EXPRESSION_RESULT_TYPE_INVALID",
                f"assigns non-numeric text to a {context.question_type} question.",
            )
        ]
    return []


def lint_expression(
    expression: Any, context: ExpressionContext
) -> list[ValidationIssue]:
    """Validate one expression-bearing field value in its context."""

    text = str(expression or "").strip()
    if not text or is_static_value(context.field, text, context.question_type):
        return []

    analysis = analyse_expression(text)
    if not analysis.valid:
        return [context.issue(analysis.error_code, analysis.error_message)]
    return [
        *_reference_issues(analysis, context),
        *_repeat_context_issues(analysis, context),
        *_result_type_issues(analysis, context),
    ]


def _strongly_connected_components(
    nodes: Sequence[str], adjacency: Mapping[str, Sequence[str]]
) -> list[list[str]]:
    """Iterative Tarjan, so deep dependency chains cannot hit recursion limits."""

    index_of: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    components: list[list[str]] = []

    for root in nodes:
        if root in index_of:
            continue
        index_of[root] = lowlink[root] = len(index_of)
        stack.append(root)
        on_stack.add(root)
        work = [(root, iter(adjacency.get(root, ())))]
        while work:
            node, targets = work[-1]
            descended = False
            for target in targets:
                if target not in index_of:
                    index_of[target] = lowlink[target] = len(index_of)
                    stack.append(target)
                    on_stack.add(target)
                    work.append((target, iter(adjacency.get(target, ()))))
                    descended = True
                    break
                if target in on_stack:
                    lowlink[node] = min(lowlink[node], index_of[target])
            if descended:
                continue
            work.pop()
            if work:
                parent = work[-1][0]
                lowlink[parent] = min(lowlink[parent], lowlink[node])
            if lowlink[node] == index_of[node]:
                component = []
                while True:
                    member = stack.pop()
                    on_stack.discard(member)
                    component.append(member)
                    if member == node:
                        break
                components.append(component)
    return components


def _cycle_path(
    start: str, members: set[str], adjacency: Mapping[str, Sequence[str]]
) -> list[str]:
    previous: dict[str, str] = {}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for target in adjacency.get(node, ()):
            if target not in members:
                continue
            if target == start:
                path = [node]
                while path[-1] != start:
                    path.append(previous[path[-1]])
                return [*reversed(path), start]
            if target not in previous:
                previous[target] = node
                queue.append(target)
    return []


def find_dependency_cycles(
    edges: Iterable[DependencyEdge],
) -> list[tuple[DependencyEdge, ...]]:
    """Return one cycle per strongly connected component, in edge order."""

    order: dict[str, int] = {}
    adjacency: dict[str, list[str]] = defaultdict(list)
    edges_by_pair: dict[tuple[str, str], DependencyEdge] = {}
    for edge in edges:
        order.setdefault(edge.source, len(order))
        order.setdefault(edge.target, len(order))
        if (edge.source, edge.target) not in edges_by_pair:
            edges_by_pair[(edge.source, edge.target)] = edge
            adjacency[edge.source].append(edge.target)

    cycles = []
    for component in _strongly_connected_components(list(order), adjacency):
        start = min(component, key=order.__getitem__)
        if len(component) == 1 and (start, start) not in edges_by_pair:
            continue
        path = _cycle_path(start, set(component), adjacency)
        if not path:
            continue
        cycles.append(tuple(edges_by_pair[pair] for pair in zip(path, path[1:])))
    cycles.sort(key=lambda cycle: order[cycle[0].source])
    return cycles


def dependency_cycle_issue(
    cycle: Sequence[DependencyEdge], *, layer: str, sheet: str | None = None
) -> ValidationIssue:
    first = cycle[0]
    path = " -> ".join([*(edge.source for edge in cycle), first.source])
    owner_name = first.owner.get("name")
    model = first.owner.get("model", "Question")
    label = f"{model} '{owner_name}'" if owner_name else model
    return ValidationIssue(
        code="EXPRESSION_DEPENDENCY_CYCLE",
        layer=layer,
        severity="error",
        message=f"{label} field '{first.field}' creates a dependency cycle: {path}.",
        owner=dict(first.owner),
        field=first.field,
        sheet=sheet,
        column=first.field if sheet else None,
        row=first.row,
    )


__all__ = [
    "DEPENDENCY_CYCLE_FIELDS",
    "DependencyEdge",
    "ExpressionAnalysis",
    "ExpressionContext",
    "ExpressionReference",
    "NON_NUMERIC_QUESTION_TYPES",
    "QUESTION_EXPRESSION_FIELDS",
    "REPEAT_EXPRESSION_FIELDS",
    "SURVEY_EXPRESSION_COLUMNS",
    "analyse_expression",
    "cycle_dependency_names",
    "dependency_cycle_issue",
    "expression_dependency_names",
    "find_dependency_cycles",
    "is_static_value",
    "lint_expression",
]
