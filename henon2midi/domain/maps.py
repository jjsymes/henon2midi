import math
import random
from collections.abc import Callable, Iterator
from dataclasses import dataclass

MAX_ORBIT_RADIUS = 1.0
_ORBIT_ENDING_ERRORS = (OverflowError, ZeroDivisionError, ValueError)


@dataclass(frozen=True)
class Point:
    x: float
    y: float


@dataclass(frozen=True)
class Sample:
    point: Point
    iteration: int
    orbit: int
    radius: float
    is_orbit_start: bool


@dataclass(frozen=True)
class StartContext:
    radius: float
    n: int
    u: float


Step = Callable[[Point], Point]
StartPoint = Callable[[StartContext], Point]


def diagonal_start(context: StartContext) -> Point:
    return Point(context.radius, context.radius)


def random_start(context: StartContext) -> Point:
    return _on_circle(context.radius, context.u * 2 * math.pi)


def sweep_start(context: StartContext) -> Point:
    return _on_circle(context.radius, float(context.n))


def require_orbit_arguments(
    iterations_per_orbit: int,
    starting_radius: float,
    radial_step: float,
    max_radius: float,
) -> None:
    if iterations_per_orbit < 1:
        raise ValueError("iterations per orbit must be at least 1")
    if not math.isfinite(starting_radius):
        raise ValueError("starting radius must be finite")
    if not math.isfinite(radial_step) or radial_step <= 0:
        raise ValueError("radial step must be positive")
    if not math.isfinite(max_radius):
        raise ValueError("max radius must be finite")


def expanding_orbits(
    step: Step,
    iterations_per_orbit: int = 100,
    starting_radius: float = 0.0,
    radial_step: float = 0.01,
    max_radius: float = MAX_ORBIT_RADIUS,
    start_at: StartPoint = diagonal_start,
    seed: int = 0,
) -> Iterator[Sample]:
    require_orbit_arguments(
        iterations_per_orbit, starting_radius, radial_step, max_radius
    )

    draws = random.Random(seed)
    radius = starting_radius
    iteration = 0
    orbit_number = 0
    while radius <= max_radius:
        orbit_number += 1
        context = StartContext(radius, orbit_number - 1, draws.random())
        for sample in _orbit_samples(
            step,
            context,
            iterations_per_orbit,
            start_at,
            iteration,
            orbit_number,
        ):
            iteration = sample.iteration
            yield sample
        radius += radial_step


def _on_circle(radius: float, angle: float) -> Point:
    return Point(radius * math.cos(angle), radius * math.sin(angle))


def _orbit_samples(
    step: Step,
    context: StartContext,
    iterations_per_orbit: int,
    start_at: StartPoint,
    iteration_offset: int,
    orbit_number: int,
) -> Iterator[Sample]:
    try:
        origin = start_at(context)
    except _ORBIT_ENDING_ERRORS:
        return
    points = _iterate_from(step, origin)
    for index_in_orbit in range(iterations_per_orbit):
        try:
            point = next(points)
        except StopIteration:
            return
        yield Sample(
            point=point,
            iteration=iteration_offset + index_in_orbit + 1,
            orbit=orbit_number,
            radius=context.radius,
            is_orbit_start=index_in_orbit == 0,
        )


def _iterate_from(step: Step, start: Point) -> Iterator[Point]:
    point = start
    while True:
        try:
            point = step(point)
        except _ORBIT_ENDING_ERRORS:
            return
        yield point
