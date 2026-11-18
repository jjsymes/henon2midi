from collections.abc import Callable
from dataclasses import dataclass

from henon2midi.domain.formula import (
    CONSTANTS,
    FUNCTION_NAMES,
    Expression,
    evaluate,
    names_in,
    read_expression,
)
from henon2midi.domain.maps import (
    Point,
    StartContext,
    StartPoint,
    Step,
    diagonal_start,
    random_start,
    sweep_start,
)
from henon2midi.domain.parameters import Parameters
from henon2midi.domain.presets import CUSTOM_SOURCE_RANGE, PRESETS, Preset

_ORBIT_NAMES = frozenset({"r", "n", "u"})
_POINT_NAMES = frozenset({"x", "y"})
_INVALID_START = (
    "start must be diagonal, random, sweep, or two expressions separated by ';'"
)


@dataclass(frozen=True)
class BoundIteration:
    name: str
    step: Step
    parameters: Parameters
    equations: tuple[str, str]
    source_range: tuple[float, float]
    start_at: StartPoint
    start: str

    @property
    def parameter_names(self) -> tuple[str, ...]:
        return self.parameters.names


@dataclass(frozen=True)
class IterationPlan:
    name: str
    equations: tuple[str, str]
    parameter_names: tuple[str, ...]
    source_range: tuple[float, float]
    start_description: str
    _bind_step: Callable[[Parameters], Step]
    _bind_start: Callable[[Parameters], StartPoint]

    @property
    def parameter_count(self) -> int:
        return len(self.parameter_names)

    def bind(self, values: tuple[float, ...]) -> BoundIteration:
        _require_parameter_count(self.name, self.parameter_names, values)
        parameters = Parameters(self.parameter_names, values)
        return BoundIteration(
            name=self.name,
            step=self._bind_step(parameters),
            parameters=parameters,
            equations=self.equations,
            source_range=self.source_range,
            start_at=self._bind_start(parameters),
            start=self.start_description,
        )


@dataclass(frozen=True)
class _MapSource:
    name: str
    x_prime: str
    y_prime: str
    source_range: tuple[float, float]


def plan_iteration(
    map_name: str | None,
    x_prime: str | None,
    y_prime: str | None,
    start_source: str,
    source_range: tuple[float, float] | None = None,
) -> IterationPlan:
    source = _map_source(map_name, x_prime, y_prime, source_range)
    x_expression = read_expression(source.x_prime, "x'")
    y_expression = read_expression(source.y_prime, "y'")
    names = _equation_names(x_expression, y_expression)
    description, bind_start = _parse_start(start_source, names)
    return IterationPlan(
        name=source.name,
        equations=(source.x_prime.strip(), source.y_prime.strip()),
        parameter_names=names,
        source_range=source.source_range,
        start_description=description,
        _bind_step=_bind_step(x_expression, y_expression),
        _bind_start=bind_start,
    )


def _map_source(
    map_name: str | None,
    x_prime: str | None,
    y_prime: str | None,
    source_range: tuple[float, float] | None,
) -> _MapSource:
    if (x_prime is None) != (y_prime is None):
        raise ValueError("custom equations need both an x equation and a y equation")
    if x_prime is not None and y_prime is not None:
        if map_name is not None:
            raise ValueError("custom equations replace the selected map")
        return _MapSource(
            "custom",
            x_prime,
            y_prime,
            _window(source_range, CUSTOM_SOURCE_RANGE),
        )
    if map_name is None:
        raise ValueError("choose a map or provide both equations")
    preset = _preset(map_name)
    return _MapSource(
        preset.name,
        preset.x_prime,
        preset.y_prime,
        _window(source_range, preset.source_range),
    )


def _preset(map_name: str) -> Preset:
    try:
        return PRESETS[map_name]
    except KeyError as error:
        raise ValueError(f"Unknown map {map_name!r}") from error


def _window(
    override: tuple[float, float] | None, default: tuple[float, float]
) -> tuple[float, float]:
    if override is None:
        return default
    return override


def _equation_names(
    x_expression: Expression, y_expression: Expression
) -> tuple[str, ...]:
    names = _names_in_equation(x_expression, "x'") | _names_in_equation(
        y_expression, "y'"
    )
    return tuple(sorted(names))


def _names_in_equation(expression: Expression, label: str) -> frozenset[str]:
    names = _names_excluding_functions_and_constants(expression, label)
    _reject_reserved(names & _ORBIT_NAMES, label, "is only available in the start")
    return names - _POINT_NAMES


def _names_excluding_functions_and_constants(
    expression: Expression, label: str
) -> frozenset[str]:
    names = names_in(expression)
    _reject_reserved(names & FUNCTION_NAMES, label, "is a function and needs arguments")
    return names - set(CONSTANTS)


def _parse_start(
    source: str, parameter_names: tuple[str, ...]
) -> tuple[str, Callable[[Parameters], StartPoint]]:
    text = source.strip()
    if text == "":
        raise ValueError(_INVALID_START)
    preset = _STARTS.get(text.lower())
    if preset is not None and ";" not in text:
        description, function = preset
        return description, _ignore_parameters(function)
    return _expression_start(text, parameter_names)


def _ignore_parameters(function: StartPoint) -> Callable[[Parameters], StartPoint]:
    def bind(_parameters: Parameters) -> StartPoint:
        return function

    return bind


def _expression_start(
    text: str, parameter_names: tuple[str, ...]
) -> tuple[str, Callable[[Parameters], StartPoint]]:
    x_source, y_source = _split_start(text)
    x_expression = read_expression(x_source, "start x")
    y_expression = read_expression(y_source, "start y")
    _reject_unknown_start_names(x_expression, "start x", parameter_names)
    _reject_unknown_start_names(y_expression, "start y", parameter_names)
    return text, _bind_start(x_expression, y_expression)


def _split_start(text: str) -> tuple[str, str]:
    parts = [part.strip() for part in text.split(";")]
    if len(parts) != 2 or parts[0] == "" or parts[1] == "":
        raise ValueError(_INVALID_START)
    return parts[0], parts[1]


def _reject_unknown_start_names(
    expression: Expression, label: str, parameter_names: tuple[str, ...]
) -> None:
    names = _names_excluding_functions_and_constants(expression, label)
    _reject_reserved(
        names & _POINT_NAMES, label, "is only available in the map equations"
    )
    unknown = names - _ORBIT_NAMES - set(parameter_names)
    if not unknown:
        return
    name = sorted(unknown)[0]
    allowed = ", ".join(parameter_names) if parameter_names else "none"
    raise ValueError(
        f"{label}: {name} is not a parameter of this map; parameters are {allowed}"
    )


def _reject_reserved(names: frozenset[str], label: str, reason: str) -> None:
    if not names:
        return
    name = sorted(names)[0]
    raise ValueError(f"{label}: {name} {reason}")


def _bind_step(
    x_expression: Expression, y_expression: Expression
) -> Callable[[Parameters], Step]:
    def bind(parameters: Parameters) -> Step:
        def step(point: Point) -> Point:
            return _point(
                x_expression,
                y_expression,
                parameters.bindings(),
                x=point.x,
                y=point.y,
            )

        return step

    return bind


def _bind_start(
    x_expression: Expression, y_expression: Expression
) -> Callable[[Parameters], StartPoint]:
    def bind(parameters: Parameters) -> StartPoint:
        def start(context: StartContext) -> Point:
            return _point(
                x_expression,
                y_expression,
                parameters.bindings(),
                r=context.radius,
                n=float(context.n),
                u=context.u,
            )

        return start

    return bind


def _point(
    x_expression: Expression,
    y_expression: Expression,
    values: dict[str, float],
    **fixed: float,
) -> Point:
    bindings = dict(values)
    bindings.update(CONSTANTS)
    bindings.update(fixed)
    return Point(evaluate(x_expression, bindings), evaluate(y_expression, bindings))


def _require_parameter_count(
    name: str, parameter_names: tuple[str, ...], parameters: tuple[float, ...]
) -> None:
    actual = len(parameters)
    expected = len(parameter_names)
    if actual == expected:
        return
    noun = "parameter" if expected == 1 else "parameters"
    listed = f" ({', '.join(parameter_names)})" if parameter_names else ""
    raise ValueError(f"Map {name} expects {expected} {noun}{listed}, got {actual}")


_STARTS = {
    "diagonal": ("diagonal", diagonal_start),
    "random": ("random", random_start),
    "sweep": ("sweep", sweep_start),
}
