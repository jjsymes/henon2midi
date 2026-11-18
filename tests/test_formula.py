import math
import random

import pytest

from henon2midi.domain.events import NoteOn
from henon2midi.domain.maps import Point, StartContext, expanding_orbits
from henon2midi.domain.plan import plan_iteration
from henon2midi.domain.mapping import Mapping, midi_events


def value_of(expression: str) -> float:
    plan = plan_iteration(None, expression, "0", "diagonal")
    return plan.bind(()).step(Point(0.0, 0.0)).x


def test_arithmetic_follows_ordinary_precedence():
    assert value_of("  2 + 3 * 4  ") == 14
    assert value_of("+2") == 2
    assert value_of("1e2") == 100
    assert value_of("8/2*2") == 8
    assert value_of("8-3-2") == 3
    assert value_of("(2+3)*4") == 20
    assert value_of("5%2") == 1
    assert value_of("-2**2") == -4
    assert value_of("2**-2") == 0.25
    assert value_of("2**3**2") == 512
    assert value_of("2*3**2") == 18


def test_numbers_constants_and_calls():
    assert value_of("1e-3") == pytest.approx(0.001)
    assert value_of("1*e - 3") == pytest.approx(math.e - 3)
    assert value_of(".5") == 0.5
    assert value_of("1.") == 1
    assert value_of("pi") == pytest.approx(math.pi)
    assert value_of("sin(0)") == 0
    assert value_of("cos(0)") == 1
    assert value_of("sqrt(4)") == 2
    assert value_of("min(3, 1)") == 1
    assert value_of("max(3, 1)") == 3
    assert value_of("floor(1.8)") == 1
    assert value_of("ceil(1.2)") == 2
    assert value_of("abs(-3)") == 3
    assert value_of("log(1)") == 0
    assert value_of("log10(100)") == 2
    assert value_of("atan2(0, -1)") == pytest.approx(math.pi)
    assert value_of("exp(0)") == 1
    assert value_of("tan(0)") == 0
    assert value_of("asin(0)") == 0
    assert value_of("acos(1)") == 0
    assert value_of("atan(0)") == 0


@pytest.mark.parametrize(
    ("expression", "message"),
    [
        ("", "must not be empty"),
        ("   ", "must not be empty"),
        ("2$", "unexpected character"),
        ("1e", "bad number"),
        ("(2+3", r"missing '\)'"),
        ("sin(x", r"missing '\)'"),
        ("sin()", "expects 1 argument"),
        ("sin(1, 2)", "expects 1 argument"),
        ("min(1)", "expects 2 arguments"),
        ("foo(1)", "unknown function"),
        ("sin", "function and needs arguments"),
        ("2 2", "unexpected"),
        ("*2", "unexpected"),
        ("x, y", "unexpected"),
    ],
)
def test_malformed_equations_say_which_one_and_why(expression, message):
    with pytest.raises(ValueError, match=message):
        plan_iteration(None, expression, "0", "diagonal")


def test_parameter_names_are_alphabetical():
    plan = plan_iteration(None, "b", "a", "a; b")
    assert plan.name == "custom"
    assert plan.parameter_names == ("a", "b")
    assert plan.equations == ("b", "a")
    bound = plan.bind((1.0, 2.0))
    assert bound.step(Point(9.0, 9.0)) == Point(2.0, 1.0)
    assert bound.start_at(StartContext(9.0, 4, 0.2)) == Point(1.0, 2.0)


def test_a_start_cannot_invent_parameters():
    with pytest.raises(ValueError, match="not a parameter"):
        plan_iteration(None, "b", "a", "s; s")
    with pytest.raises(ValueError, match="not a parameter"):
        plan_iteration("classic", None, None, "S; 0")
    with pytest.raises(ValueError, match="not a parameter"):
        plan_iteration("four-parameter", None, None, "aa; 0")


def test_typed_classic_and_four_parameter_formulas_match_the_builtins():
    classic = plan_iteration(
        None,
        "x*cos(a) - (y - x**2)*sin(a)",
        "x*sin(a) + (y - x**2)*cos(a)",
        "diagonal",
    )
    four = plan_iteration(
        None,
        "sin(a*y) - cos(b*x)",
        "sin(c*x) - cos(d*y)",
        "diagonal",
    )
    point = Point(0.2, -0.4)
    custom_points = _points(
        _orbits(
            classic,
            (1.333,),
            iterations_per_orbit=3,
            starting_radius=0.0,
            radial_step=0.2,
        )
    )
    preset = plan_iteration("classic", None, None, "diagonal")
    builtin_points = _points(
        _orbits(
            preset,
            (1.333,),
            iterations_per_orbit=3,
            starting_radius=0.0,
            radial_step=0.2,
        )
    )
    assert len(custom_points) == len(builtin_points)
    for custom_point, builtin_point in zip(custom_points, builtin_points):
        assert custom_point.x == pytest.approx(builtin_point.x)
        assert custom_point.y == pytest.approx(builtin_point.y)
    got = four.bind((0.3, -0.2, 1.1, 0.7)).step(point)
    a, b, c, d = (0.3, -0.2, 1.1, 0.7)
    x, y = point.x, point.y
    expected = Point(
        math.sin(a * y) - math.cos(b * x), math.sin(c * x) - math.cos(d * y)
    )
    assert got.x == pytest.approx(expected.x)
    assert got.y == pytest.approx(expected.y)


def test_orbit_names_stay_out_of_the_map_and_point_names_stay_out_of_the_start():
    with pytest.raises(ValueError, match="only available in the start"):
        plan_iteration(None, "r", "y", "diagonal")
    with pytest.raises(ValueError, match="only available in the map"):
        plan_iteration(None, "y", "-x", "x; y")


def test_start_presets_cover_the_old_experiments():
    diagonal = plan_iteration("classic", None, None, "  Diagonal ")
    random_start = plan_iteration("classic", None, None, "random")
    sweep = plan_iteration("classic", None, None, "sweep")
    assert diagonal.start_description == "diagonal"
    assert random_start.start_description == "random"
    assert sweep.start_description == "sweep"

    assert diagonal.bind((1.0,)).start_at(StartContext(0.4, 3, 0.9)) == Point(0.4, 0.4)
    swept = sweep.bind((1.0,)).start_at(StartContext(2.0, 1, 0.9))
    assert swept.x == pytest.approx(2 * math.cos(1))
    assert swept.y == pytest.approx(2 * math.sin(1))
    shared = random_start.bind((1.0,)).start_at(StartContext(2.0, 0, 0.25))
    assert shared.x == pytest.approx(0.0)
    assert shared.y == pytest.approx(2.0)
    assert random_start.bind((1.0,)).start_at(StartContext(0.0, 0, 0.3)) == Point(
        0.0, 0.0
    )


def test_a_start_expression_can_share_one_random_sample_and_the_map_parameter():
    plan = plan_iteration("classic", None, None, "r*cos(u*2*pi); r*sin(u*2*pi)")
    origin = plan.bind((0.0,)).start_at(StartContext(2.0, 7, 0.25))
    assert origin.x == pytest.approx(0.0)
    assert origin.y == pytest.approx(2.0)

    angled = plan_iteration("classic", None, None, "r*cos(a); r*sin(a)")
    assert angled.parameter_names == ("a",)
    origin = angled.bind((0.0,)).start_at(StartContext(0.5, 3, 0.2))
    assert origin.x == pytest.approx(0.5)
    assert origin.y == pytest.approx(0.0)


def test_the_same_seed_repeats_random_starts_and_another_seed_does_not():
    first = _random_points(0)
    assert first == _random_points(0)
    assert first != _random_points(1)
    drawn = random.Random(0)
    classic = plan_iteration("classic", None, None, "diagonal").bind((1.0,))
    expected_angles = [drawn.random() * 2 * math.pi for _ in range(2)]
    for point, angle, radius in zip(first, expected_angles, (0.5, 1.0)):
        origin = Point(radius * math.cos(angle), radius * math.sin(angle))
        expected = classic.step(origin)
        assert point.x == pytest.approx(expected.x)
        assert point.y == pytest.approx(expected.y)


def test_a_plan_needs_a_map_or_two_equations():
    with pytest.raises(ValueError, match="choose a map or provide both equations"):
        plan_iteration(None, None, None, "diagonal")


def test_custom_equations_reject_a_builtin_and_a_missing_half():
    with pytest.raises(ValueError, match="replace the selected map"):
        plan_iteration("classic", "y", "-x", "diagonal")
    with pytest.raises(ValueError, match="both an x equation and a y equation"):
        plan_iteration("classic", "y", None, "diagonal")
    with pytest.raises(ValueError, match="Unknown map"):
        plan_iteration("logistic", None, None, "diagonal")


@pytest.mark.parametrize(
    "source",
    ["", "   ", "sideways", "r;", ";r", "r;r;r"],
)
def test_start_text_must_be_a_preset_or_two_expressions(source):
    with pytest.raises(ValueError, match="start must"):
        plan_iteration("classic", None, None, source)


def test_a_broken_start_expression_names_its_side():
    with pytest.raises(ValueError, match="start y"):
        plan_iteration("classic", None, None, "r; r*")


def test_an_empty_equation_names_its_side():
    with pytest.raises(ValueError, match="y'"):
        plan_iteration(None, "x", "  ", "diagonal")


def test_dividing_by_zero_ends_that_orbit_only():
    plan = plan_iteration(None, "1/(x-1)", "y", "2; 0")
    samples = list(
        _orbits(
            plan,
            (),
            iterations_per_orbit=5,
            starting_radius=0.0,
            radial_step=1.0,
            max_radius=0.0,
        )
    )
    assert [sample.point for sample in samples] == [Point(1.0, 0.0)]


def test_four_parameter_window_plays_a_point_below_minus_one():
    plan = plan_iteration("four-parameter", None, None, "diagonal")
    assert plan.source_range == (-2.0, 2.0)
    samples = list(
        _orbits(
            plan,
            (1.0, 1.0, 1.0, 1.0),
            iterations_per_orbit=5,
            starting_radius=0.2,
            radial_step=1.0,
            max_radius=0.2,
        )
    )
    below = next(sample for sample in samples if sample.point.x < -1)
    window = plan.source_range
    events = midi_events(
        below.point,
        Mapping(source_range_x=window, source_range_y=window),
        10,
    )
    assert any(isinstance(event, NoteOn) for event in events)
    unit_events = midi_events(below.point, Mapping(), 10)
    assert not any(isinstance(event, NoteOn) for event in unit_events)


def _orbits(plan, parameters, **kwargs):
    bound = plan.bind(parameters)
    return expanding_orbits(bound.step, start_at=bound.start_at, **kwargs)


def _random_points(seed: int) -> list[Point]:
    plan = plan_iteration("classic", None, None, "random")
    samples = _orbits(
        plan,
        (1.0,),
        iterations_per_orbit=1,
        starting_radius=0.5,
        radial_step=0.5,
        seed=seed,
    )
    return [sample.point for sample in samples]


def _points(samples):
    return [sample.point for sample in samples]
