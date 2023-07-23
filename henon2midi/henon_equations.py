from math import cos, sin
from typing import Callable, Generator


def equation_a(x: float, y: float, a: float) -> float:
    return (x * cos(a)) - ((y - x**2) * sin(a))


def equation_b(x: float, y: float, a: float) -> float:
    return (x * sin(a)) + ((y - x**2) * cos(a))


# TODO: try these equations
# def four_parameter_equation_a(x: float, y: float, a: float, b: float, c: float, d: float) -> float:
#     return (sin(a*y)) - (cos(b*x))

# def four_parameter_equation_b(x: float, y: float, a: float, b: float, c: float, d: float) -> float:
#     return (sin(c*x)) - (cos(d*y))


def henon_mapping_generator(
    a_parameter: float,
    initial_x: float,
    initial_y: float,
    equation_a: Callable = equation_a,
    equation_b: Callable = equation_b,
) -> Generator[tuple[float, float], None, None]:
    x = initial_x
    y = initial_y
    while True:
        try:
            x_next, y_next = equation_a(x, y, a_parameter), equation_b(
                x, y, a_parameter
            )
            x, y = x_next, y_next
        except OverflowError:
            break
        else:
            yield x, y


def radially_expanding_henon_mappings_generator(
    a_parameter: float,
    iterations_per_orbit: int = 32,
    starting_radius: float = 0.0,
    radial_step: float = 0.1,
) -> Generator[tuple[float, float], None, None]:
    radius = starting_radius
    while radius <= 1:
        radius += radial_step
        for _ in range(iterations_per_orbit):
            yield from henon_mapping_generator(a_parameter, radius, radius)
