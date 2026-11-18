import math

import pytest

from henon2midi.domain.maps import Point, expanding_orbits
from henon2midi.domain.parameters import Parameters
from henon2midi.domain.plan import plan_iteration


def test_the_next_step_uses_a_parameter_changed_after_binding():
    bound = plan_iteration(None, "x + a", "y", "0; 0").bind((1.0,))
    assert bound.step(Point(0.0, 0.0)) == Point(1.0, 0.0)
    bound.parameters.set("a", 5.0)
    assert bound.parameters.get("a") == 5.0
    assert bound.step(Point(0.0, 0.0)) == Point(5.0, 0.0)


def test_a_running_orbit_uses_a_parameter_change_on_the_next_point():
    bound = plan_iteration(None, "x + a", "y", "0; 0").bind((1.0,))
    samples = expanding_orbits(
        bound.step,
        iterations_per_orbit=3,
        starting_radius=0.0,
        radial_step=1.0,
        max_radius=0.0,
        start_at=bound.start_at,
    )
    assert next(samples).point == Point(1.0, 0.0)
    bound.parameters.set("a", 5.0)
    assert next(samples).point == Point(6.0, 0.0)
    assert next(samples).point == Point(11.0, 0.0)


def test_the_next_orbit_starts_from_the_current_parameter_value():
    bound = plan_iteration(None, "x", "a", "a; 0").bind((0.25,))
    samples = expanding_orbits(
        bound.step,
        iterations_per_orbit=1,
        starting_radius=0.0,
        radial_step=1.0,
        max_radius=1.0,
        start_at=bound.start_at,
    )
    assert next(samples).point == Point(0.25, 0.25)
    bound.parameters.set("a", 0.8)
    assert next(samples).point == Point(0.8, 0.8)


def test_each_binding_keeps_its_own_values():
    plan = plan_iteration("classic", None, None, "diagonal")
    first = plan.bind((1.0,))
    second = plan.bind((2.0,))
    first.parameters.set("a", 9.0)
    assert first.parameters.values == (9.0,)
    assert second.parameters.values == (2.0,)


def test_one_parameter_can_move_while_the_others_stay():
    bound = plan_iteration("four-parameter", None, None, "diagonal").bind(
        (1.0, 2.0, 3.0, 4.0)
    )
    bound.parameters.set("c", 9.0)
    assert bound.parameters.values == (1.0, 2.0, 9.0, 4.0)
    assert repr(bound.parameters) == "Parameters(a=1.0, b=2.0, c=9.0, d=4.0)"
    bound.parameters.replace((4.0, 3.0, 2.0, 1.0))
    assert bound.parameters.values == (4.0, 3.0, 2.0, 1.0)


def test_a_bad_update_leaves_the_current_values_in_place():
    parameters = Parameters(("a", "b"), (1.0, 2.0))
    with pytest.raises(ValueError, match="not a parameter"):
        parameters.set("c", 3.0)
    with pytest.raises(ValueError, match="finite"):
        parameters.set("a", math.inf)
    with pytest.raises(ValueError, match="finite"):
        parameters.set("a", True)
    with pytest.raises(ValueError, match="finite"):
        parameters.set("a", "3")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="got 1"):
        parameters.replace((3.0,))
    assert parameters.values == (1.0, 2.0)


def test_parameters_reject_a_bad_initial_value():
    with pytest.raises(ValueError, match="unique"):
        Parameters(("a", "a"), (1.0, 2.0))
    with pytest.raises(ValueError, match="got 1"):
        Parameters(("a", "b"), (1.0,))
    with pytest.raises(ValueError, match="finite"):
        Parameters(("a",), (math.nan,))
