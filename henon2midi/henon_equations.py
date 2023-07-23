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


class RadiallyExpandingHenonMappingsGenerator:
    def __init__(
        self,
        a_parameter: float,
        iterations_per_orbit: int = 100,
        starting_radius: float = 0.1,
        radial_step: float = 0.05,
    ):
        self.a_parameter = a_parameter
        self.iterations_per_orbit = iterations_per_orbit
        self.starting_radius = starting_radius
        self.radial_step = radial_step
        self.henon_mapping_generator = henon_mapping_generator(
            a_parameter, starting_radius, starting_radius
        )
        self.data_point_generator = self._radially_expanding_henon_mappings_generator()
        self.current_orbital_iteration = 0
        self.current_iteration = 0
        self.iteration_of_current_orbit = 0
        self.times_reset = 0
        self.current_radius = starting_radius
        self.current_data_point = (starting_radius, starting_radius)

    def generate_next_data_point(self) -> tuple[float, float]:
        """
        Returns the next data point in the sequence.
        If the sequence has reached the end, it will restart the sequence and return the first data point.
        """
        try:
            data_point = next(self.data_point_generator)
        except StopIteration:
            self.restart_data_point_generator()
            data_point = next(self.data_point_generator)
        return data_point

    def restart_data_point_generator(self):
        """
        Creates a new data point generator. This is useful if you want to restart the sequence.
        """
        self.times_reset += 1
        self.data_point_generator = self._radially_expanding_henon_mappings_generator()

    def _radially_expanding_henon_mappings_generator(
        self,
    ) -> Generator[tuple[float, float], None, None]:
        self._reset_to_starting_radius()
        self.current_iteration = 0
        self.current_orbital_iteration = 0
        self.iteration_of_current_orbit = 0

        while self.current_radius <= 1:
            self.iteration_of_current_orbit = 0
            self.current_orbital_iteration += 1
            self.henon_mapping_generator = henon_mapping_generator(
                self.a_parameter, self.current_radius, self.current_radius
            )

            while self.iteration_of_current_orbit < self.iterations_per_orbit:
                try:
                    data_point = next(self.henon_mapping_generator)
                except StopIteration:
                    break
                self.current_data_point = data_point
                self.current_iteration += 1
                self.current_data_point = data_point
                self.iteration_of_current_orbit += 1
                yield data_point

            self.current_radius += self.radial_step

    def _reset_to_starting_radius(self):
        self.current_radius = self.starting_radius
        self.current_data_point = (self.starting_radius, self.starting_radius)

    def get_current_iteration(self) -> int:
        return self.current_iteration

    def get_current_data_point(self) -> tuple[float, float]:
        return self.current_data_point

    def get_current_radius(self) -> float:
        return self.current_radius

    def get_current_orbital_iteration(self) -> int:
        return self.current_orbital_iteration

    def get_iteration_of_current_orbit(self) -> int:
        return self.iteration_of_current_orbit

    def is_new_orbit(self) -> bool:
        return self.iteration_of_current_orbit == 1

    def get_times_reset(self) -> int:
        return self.times_reset

    def __iter__(self):
        return self

    def __next__(self):
        return next(self.data_point_generator)
