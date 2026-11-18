import math
import operator
from collections.abc import Callable
from dataclasses import dataclass

ExpressionFunction = Callable[..., float]


FUNCTIONS: dict[str, tuple[int, ExpressionFunction]] = {
    "sin": (1, math.sin),
    "cos": (1, math.cos),
    "tan": (1, math.tan),
    "asin": (1, math.asin),
    "acos": (1, math.acos),
    "atan": (1, math.atan),
    "atan2": (2, math.atan2),
    "exp": (1, math.exp),
    "log": (1, math.log),
    "log10": (1, math.log10),
    "sqrt": (1, math.sqrt),
    "abs": (1, abs),
    "floor": (1, math.floor),
    "ceil": (1, math.ceil),
    "min": (2, min),
    "max": (2, max),
}
FUNCTION_NAMES = frozenset(FUNCTIONS)
CONSTANTS = {"pi": math.pi, "e": math.e}


@dataclass(frozen=True)
class Number:
    value: float


@dataclass(frozen=True)
class Variable:
    name: str


@dataclass(frozen=True)
class Unary:
    operator: str
    operand: "Expression"


@dataclass(frozen=True)
class Binary:
    operator: str
    left: "Expression"
    right: "Expression"


@dataclass(frozen=True)
class Call:
    name: str
    arguments: tuple["Expression", ...]


Expression = Number | Variable | Unary | Binary | Call


@dataclass(frozen=True)
class _Token:
    kind: str
    text: str


def read_expression(source: str, label: str) -> Expression:
    if source.strip() == "":
        raise ValueError(f"{label}: expression must not be empty")
    try:
        return _Parser(_tokenize(source)).parse()
    except ValueError as error:
        raise ValueError(f"{label}: {error}") from error


def evaluate(expression: Expression, bindings: dict[str, float]) -> float:
    if isinstance(expression, Number):
        return expression.value
    if isinstance(expression, Variable):
        return bindings[expression.name]
    if isinstance(expression, Unary):
        value = evaluate(expression.operand, bindings)
        if expression.operator == "+":
            return value
        return -value
    if isinstance(expression, Binary):
        left = evaluate(expression.left, bindings)
        right = evaluate(expression.right, bindings)
        return _OPERATIONS[expression.operator](left, right)
    function = FUNCTIONS[expression.name][1]
    arguments = tuple(evaluate(argument, bindings) for argument in expression.arguments)
    return float(function(*arguments))


def names_in(expression: Expression) -> frozenset[str]:
    if isinstance(expression, Variable):
        return frozenset({expression.name})
    if isinstance(expression, Unary):
        return names_in(expression.operand)
    if isinstance(expression, Binary):
        return names_in(expression.left) | names_in(expression.right)
    if isinstance(expression, Call):
        found: set[str] = set()
        for argument in expression.arguments:
            found.update(names_in(argument))
        return frozenset(found)
    return frozenset()


_OPERATIONS = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": operator.truediv,
    "%": operator.mod,
    "**": operator.pow,
}


def _tokenize(source: str) -> list[_Token]:
    tokens: list[_Token] = []
    index = 0
    while index < len(source):
        index = _skip_space(source, index)
        if index >= len(source):
            break
        token, index = _read_token(source, index)
        tokens.append(token)
    return tokens


def _skip_space(source: str, index: int) -> int:
    while index < len(source) and source[index].isspace():
        index += 1
    return index


def _read_token(source: str, index: int) -> tuple[_Token, int]:
    character = source[index]
    if character.isdigit() or _is_decimal_point(source, index):
        return _read_number(source, index)
    if character.isalpha() or character == "_":
        return _read_name(source, index)
    if character == "*" and _next_is(source, index, "*"):
        return _Token("operator", "**"), index + 2
    if character in "+-*/%":
        return _Token("operator", character), index + 1
    if character in "()":
        return _Token("paren", character), index + 1
    if character == ",":
        return _Token("comma", character), index + 1
    raise ValueError(f"unexpected character {character!r}")


def _is_decimal_point(source: str, index: int) -> bool:
    return source[index] == "." and _next_is_digit(source, index)


def _next_is(source: str, index: int, character: str) -> bool:
    return index + 1 < len(source) and source[index + 1] == character


def _next_is_digit(source: str, index: int) -> bool:
    return index + 1 < len(source) and source[index + 1].isdigit()


def _read_number(source: str, index: int) -> tuple[_Token, int]:
    start = index
    index = _read_digits_and_point(source, index)
    index = _read_exponent(source, index, start)
    return _Token("number", source[start:index]), index


def _read_digits_and_point(source: str, index: int) -> int:
    if source[index] == ".":
        index += 1
        return _read_digits(source, index)
    index = _read_digits(source, index)
    if index < len(source) and source[index] == ".":
        index += 1
        index = _read_digits(source, index)
    return index


def _read_digits(source: str, index: int) -> int:
    while index < len(source) and source[index].isdigit():
        index += 1
    return index


def _read_exponent(source: str, index: int, start: int) -> int:
    if index >= len(source) or source[index] not in "eE":
        return index
    cursor = index + 1
    if cursor < len(source) and source[cursor] in "+-":
        cursor += 1
    digits = _read_digits(source, cursor)
    if digits == cursor:
        raise ValueError(f"bad number {source[start:cursor]!r}")
    return digits


def _read_name(source: str, index: int) -> tuple[_Token, int]:
    start = index
    index += 1
    while index < len(source) and (source[index].isalnum() or source[index] == "_"):
        index += 1
    return _Token("name", source[start:index]), index


class _Parser:
    def __init__(self, tokens: list[_Token]) -> None:
        self._tokens = tokens
        self._index = 0

    def parse(self) -> Expression:
        expression = self._parse_additive()
        if self._index != len(self._tokens):
            raise ValueError(f"unexpected {self._tokens[self._index].text!r}")
        return expression

    def _parse_additive(self) -> Expression:
        return self._parse_left_to_right(self._parse_multiplicative, "+", "-")

    def _parse_multiplicative(self) -> Expression:
        return self._parse_left_to_right(self._parse_unary, "*", "/", "%")

    def _parse_left_to_right(
        self,
        parse_tighter: Callable[[], Expression],
        *operators: str,
    ) -> Expression:
        expression = parse_tighter()
        while True:
            operator = self._operator(*operators)
            if operator is None:
                return expression
            right = parse_tighter()
            expression = Binary(operator, expression, right)

    def _parse_unary(self) -> Expression:
        operator = self._operator("+", "-")
        if operator is None:
            return self._parse_power()
        return Unary(operator, self._parse_unary())

    def _parse_power(self) -> Expression:
        base = self._parse_primary()
        if self._operator("**") is None:
            return base
        return Binary("**", base, self._parse_unary())

    def _parse_primary(self) -> Expression:
        if self._take("number"):
            return Number(float(self._previous().text))
        if self._take("name"):
            name = self._previous().text
            if self._take("paren", "("):
                return self._parse_call(name)
            return Variable(name)
        if self._take("paren", "("):
            expression = self._parse_additive()
            if not self._take("paren", ")"):
                raise ValueError("missing ')'")
            return expression
        if self._index >= len(self._tokens):
            raise ValueError("unexpected end of equation")
        raise ValueError(f"unexpected {self._tokens[self._index].text!r}")

    def _parse_call(self, name: str) -> Call:
        if name not in FUNCTIONS:
            raise ValueError(f"unknown function {name}")
        arguments: list[Expression] = []
        if not self._looking_at("paren", ")"):
            arguments.append(self._parse_additive())
            while self._take("comma"):
                arguments.append(self._parse_additive())
        if not self._take("paren", ")"):
            raise ValueError("missing ')'")
        expected = FUNCTIONS[name][0]
        if len(arguments) != expected:
            noun = "argument" if expected == 1 else "arguments"
            raise ValueError(f"{name} expects {expected} {noun}, got {len(arguments)}")
        return Call(name, tuple(arguments))

    def _operator(self, *operators: str) -> str | None:
        if not self._looking_at("operator"):
            return None
        text = self._tokens[self._index].text
        if text not in operators:
            return None
        self._index += 1
        return text

    def _take(self, kind: str, text: str | None = None) -> bool:
        if not self._looking_at(kind, text):
            return False
        self._index += 1
        return True

    def _looking_at(self, kind: str, text: str | None = None) -> bool:
        if self._index >= len(self._tokens):
            return False
        token = self._tokens[self._index]
        if token.kind != kind:
            return False
        return text is None or token.text == text

    def _previous(self) -> _Token:
        return self._tokens[self._index - 1]
