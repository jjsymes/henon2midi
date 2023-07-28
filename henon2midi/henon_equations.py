from math import cos, sin
from typing import Callable, Generator
import random


def equation_a(xy: tuple[float, float], parameters: tuple[float]) -> float:
    x = xy[0]
    y = xy[1]
    a = parameters[0]
    return (x * cos(a)) - ((y - x**2) * sin(a))


def equation_b(xy: tuple[float, float], parameters: tuple[float]) -> float:
    x = xy[0]
    y = xy[1]
    a = parameters[0]
    return (x * sin(a)) + ((y - x**2) * cos(a))


def four_parameter_equation_a(
    xy: tuple[float, float], parameters: tuple[float, float, float, float]
) -> float:
    x = xy[0]
    y = xy[1]
    a = parameters[0]
    b = parameters[1]
    return (sin(a * y)) - (cos(b * x))


def four_parameter_equation_b(
    xy: tuple[float, float], parameters: tuple[float, float, float, float]
) -> float:
    x = xy[0]
    y = xy[1]
    c = parameters[2]
    d = parameters[3]
    return (sin(c * x)) - (cos(d * y))


def henon_mapping_generator(
    parameters: tuple[float, ...],
    initial_x: float,
    initial_y: float,
    equation_a: Callable = equation_a,
    equation_b: Callable = equation_b,
) -> Generator[tuple[float, float], None, None]:
    x = initial_x
    y = initial_y
    while True:
        try:
            x_next, y_next = equation_a((x, y), parameters), equation_b(
                (x, y), parameters
            )
            x, y = x_next, y_next
        except OverflowError:
            break
        else:
            yield x, y


class RadiallyExpandingHenonMappingsGenerator:
    def __init__(
        self,
        parameters: tuple[float, ...],
        iterations_per_orbit: int = 100,
        starting_radius: float = 0.1,
        radial_step: float = 0.05,
        equation_a: Callable = equation_a,
        equation_b: Callable = equation_b,
        # equation_a: Callable = four_parameter_equation_a,
        # equation_b: Callable = four_parameter_equation_b,
    ):
        self.parameters = parameters
        self.equation_a = equation_a
        self.equation_b = equation_b
        self.iterations_per_orbit = iterations_per_orbit
        self.starting_radius = starting_radius
        self.radial_step = radial_step
        self.henon_mapping_generator = henon_mapping_generator(
            self.parameters,
            starting_radius,
            starting_radius,
            self.equation_a,
            self.equation_b,
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
        angle = random.uniform(0, 2 * 3.141592653589793)

        while self.current_radius <= 1:
            self.iteration_of_current_orbit = 0
            self.current_orbital_iteration += 1
            # random_point_at_same_radius = self._get_random_point_at_same_radius(self.current_radius)
            random_point_at_same_radius = (self.current_radius, self.current_radius)
            # random_point_at_same_radius = self._get_pont_at_angle(angle, radius=self.current_radius)
            # angle += 1
            # if angle > 2 * 3.141592653589793:
            #     angle = 0

            self.henon_mapping_generator = henon_mapping_generator(
                self.parameters,
                random_point_at_same_radius[0],
                random_point_at_same_radius[1],
                self.equation_a,
                self.equation_b,
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
    
    def _get_random_point_at_same_radius(self, radius: float) -> tuple[float, float]:
        # where (0,0) is the center of the circle
        # and (x,y) is the random point on the circle
        import random
        import math
        if radius == 0:
            return (0, 0)
        theta = random.uniform(0, 2 * math.pi)
        x = radius * cos(theta)
        y = radius * sin(theta)
        return (x, y)

    def _get_pont_at_angle(self, angle: float, radius: float) -> tuple[float, float]:
        # where (0,0) is the center of the circle
        # and (x,y) is the random point on the circle
        if radius == 0:
            return (0, 0)
        x = radius * cos(angle)
        y = radius * sin(angle)
        return (x, y)

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
