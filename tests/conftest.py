import pytest

from henon2midi.domain.plan import plan_iteration
from henon2midi.domain.mapping import Mapping
from henon2midi.run import OrbitSchedule, Performance, Timing


def classic_orbit(parameters: tuple[float, ...] = (1.0,), start: str = "diagonal"):
    return plan_iteration("classic", None, None, start).bind(parameters)


@pytest.fixture
def tiny_config() -> Performance:
    bound = classic_orbit()
    window = bound.source_range
    return Performance(
        bound,
        OrbitSchedule(
            iterations_per_orbit=2,
            starting_radius=0.0,
            radial_step=1.0,
        ),
        Timing(),
        Mapping(source_range_x=window, source_range_y=window),
    )
