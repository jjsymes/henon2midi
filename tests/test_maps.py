import math

import pytest

from henon2midi.domain.maps import Point, StartContext, diagonal_start, expanding_orbits
from henon2midi.domain.plan import plan_iteration
from henon2midi.domain.presets import PRESETS


def compiled_classic(angle: float = 1.0):
    return plan_iteration("classic", None, None, "diagonal").bind((angle,))


def classic_orbits(angle: float = 1.0, **kwargs):
    bound = compiled_classic(angle)
    return expanding_orbits(bound.step, **kwargs)


def test_registered_maps_are_addressable_by_name():
    assert set(PRESETS) == {"classic", "four-parameter"}
    assert PRESETS["classic"].source_range == (-1.0, 1.0)
    assert PRESETS["four-parameter"].source_range == (-2.0, 2.0)
    assert diagonal_start(StartContext(0.3, 0, 0.0)) == Point(0.3, 0.3)
    classic = plan_iteration("classic", None, None, "diagonal")
    four = plan_iteration("four-parameter", None, None, "diagonal")
    assert classic.parameter_names == ("a",)
    assert four.parameter_names == ("a", "b", "c", "d")
    assert classic.source_range == (-1.0, 1.0)
    assert four.source_range == (-2.0, 2.0)


@pytest.mark.parametrize(
    ("point", "angle"),
    [
        (Point(0.0, 0.0), 1.0),
        (Point(0.2, -0.4), 1.333),
        (Point(-0.7, 0.2), 0.4),
    ],
)
def test_classic_step_matches_the_area_preserving_henon_formula(point, angle):
    x, y = point.x, point.y
    expected = Point(
        (x * math.cos(angle)) - ((y - x**2) * math.sin(angle)),
        (x * math.sin(angle)) + ((y - x**2) * math.cos(angle)),
    )
    assert compiled_classic(angle).step(point) == expected


@pytest.mark.parametrize(
    ("point", "parameters"),
    [
        (Point(0.2, 0.2), (1.0, 2.0, 3.0, 4.0)),
        (Point(-0.5, 0.8), (0.3, -0.2, 1.1, 0.7)),
    ],
)
def test_four_parameter_step_matches_its_formula(point, parameters):
    x, y = point.x, point.y
    a, b, c, d = parameters
    expected = Point(
        math.sin(a * y) - math.cos(b * x),
        math.sin(c * x) - math.cos(d * y),
    )
    bound = plan_iteration("four-parameter", None, None, "diagonal").bind(parameters)
    assert bound.step(point) == expected


def test_origin_stays_at_the_origin_for_the_classic_map():
    assert (
        classic_points(0.0, iterations=4, step=1.0, max_radius=0.0)
        == [Point(0.0, 0.0)] * 4
    )


def classic_points(radius, iterations, step, max_radius=None):
    samples = classic_orbits(
        iterations_per_orbit=iterations,
        starting_radius=radius,
        radial_step=step,
        max_radius=1.0 if max_radius is None else max_radius,
    )
    return [sample.point for sample in samples]


def test_orbit_numbering_radius_and_boundaries():
    samples = list(
        classic_orbits(
            iterations_per_orbit=3,
            starting_radius=0.0,
            radial_step=0.2,
        )
    )

    assert len(samples) == 18
    assert [sample.iteration for sample in samples] == list(range(1, 19))
    assert [sample.orbit for sample in samples] == [
        orbit for orbit in range(1, 7) for _ in range(3)
    ]
    expected_radii = [
        radius for radius in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0) for _ in range(3)
    ]
    assert [sample.radius for sample in samples] == pytest.approx(expected_radii)
    assert [sample.is_orbit_start for sample in samples] == [
        flag for _ in range(6) for flag in (True, False, False)
    ]


def test_recorded_orbit_prefix():
    samples = list(
        classic_orbits(
            1.333,
            iterations_per_orbit=3,
            starting_radius=0.0,
            radial_step=0.2,
        )
    )
    prefix = samples[:9]
    expected = [
        (0.0, 0.0, 1, 1, 0.0, True),
        (0.0, 0.0, 2, 1, 0.0, False),
        (0.0, 0.0, 3, 1, 0.0, False),
        (-0.10838520166926688, 0.23206173329334662, 4, 2, 0.2, True),
        (-0.23964599511649803, -0.05343758598802673, 5, 2, 0.2, False),
        (0.05129652717282546, -0.2590184084288565, 6, 2, 0.2, False),
        (-0.13902164855103127, 0.445278543424398, 7, 3, 0.4, True),
        (-0.4467131615860041, -0.03477170387869473, 8, 3, 0.4, False),
        (0.12250189282953948, -0.48934020600680106, 9, 3, 0.4, False),
    ]
    for sample, (x, y, iteration, orbit, radius, is_start) in zip(
        prefix, expected, strict=True
    ):
        assert sample.point.x == pytest.approx(x)
        assert sample.point.y == pytest.approx(y)
        assert (
            sample.iteration,
            sample.orbit,
            sample.radius,
            sample.is_orbit_start,
        ) == (
            iteration,
            orbit,
            radius,
            is_start,
        )


def test_each_call_returns_a_fresh_finite_sequence():
    def orbits():
        return list(
            classic_orbits(
                iterations_per_orbit=2,
                starting_radius=0.5,
                radial_step=0.5,
            )
        )

    assert orbits() == orbits()
    assert len(orbits()) == 4


def test_radius_above_the_maximum_yields_nothing():
    samples = list(
        classic_orbits(
            starting_radius=1.1,
            radial_step=0.1,
        )
    )
    assert samples == []


def test_starting_on_the_maximum_radius_yields_one_orbit():
    samples = list(
        classic_orbits(
            iterations_per_orbit=2,
            starting_radius=1.0,
            radial_step=0.5,
        )
    )
    assert [sample.orbit for sample in samples] == [1, 1]
    assert {sample.radius for sample in samples} == {1.0}


def test_custom_start_point_is_used_for_every_orbit():
    def along_x_axis(context: StartContext) -> Point:
        return Point(context.radius, 0.0)

    samples = list(
        classic_orbits(
            0.3,
            iterations_per_orbit=1,
            starting_radius=0.4,
            radial_step=0.6,
            max_radius=1.0,
            start_at=along_x_axis,
        )
    )
    expected = [
        compiled_classic(0.3).step(Point(0.4, 0.0)),
        compiled_classic(0.3).step(Point(1.0, 0.0)),
    ]
    assert [sample.point for sample in samples] == expected


def test_overflow_ends_the_orbit_and_the_next_radius_still_runs():
    def overflow_when_x_passes_one(point: Point) -> Point:
        if point.x > 1:
            raise OverflowError
        return Point(point.x + 0.6, 0.0)

    samples = list(
        expanding_orbits(
            overflow_when_x_passes_one,
            iterations_per_orbit=10,
            starting_radius=0.0,
            radial_step=1.0,
            max_radius=1.0,
            start_at=lambda context: Point(context.radius, 0.0),
        )
    )

    assert [sample.point for sample in samples] == [
        Point(0.6, 0.0),
        Point(1.2, 0.0),
        Point(1.6, 0.0),
    ]
    assert [sample.is_orbit_start for sample in samples] == [True, False, True]
    assert [sample.orbit for sample in samples] == [1, 1, 2]
    assert [sample.iteration for sample in samples] == [1, 2, 3]


@pytest.mark.parametrize(
    ("iterations", "radius", "step", "maximum", "message"),
    [
        (0, 0.0, 0.1, 1.0, "at least 1"),
        (2, math.nan, 0.1, 1.0, "starting radius"),
        (2, 0.0, 0.0, 1.0, "radial step"),
        (2, 0.0, -0.2, 1.0, "radial step"),
        (2, 0.0, math.inf, 1.0, "radial step"),
        (2, 0.0, 0.1, math.nan, "max radius"),
    ],
)
def test_expanding_orbits_rejects_arguments_that_cannot_finish(
    iterations, radius, step, maximum, message
):
    with pytest.raises(ValueError, match=message):
        next(
            classic_orbits(
                iterations_per_orbit=iterations,
                starting_radius=radius,
                radial_step=step,
                max_radius=maximum,
            )
        )


def test_wrong_parameter_count_names_the_map():
    four = plan_iteration("four-parameter", None, None, "diagonal")
    classic = plan_iteration("classic", None, None, "diagonal")
    with pytest.raises(
        ValueError, match=r"four-parameter expects 4 parameters \(a, b, c, d\), got 1"
    ):
        four.bind((1.0,))
    with pytest.raises(ValueError, match=r"classic expects 1 parameter \(a\), got 4"):
        classic.bind((1.0, 1.0, 1.0, 1.0))


def test_a_domain_error_skips_the_rest_of_the_orbit():
    def fail_after_the_origin(point: Point) -> Point:
        if point.x != 0:
            raise ValueError("math domain error")
        return Point(1.0, 0.0)

    samples = list(
        expanding_orbits(
            fail_after_the_origin,
            iterations_per_orbit=4,
            starting_radius=0.0,
            radial_step=1.0,
            max_radius=0.0,
            start_at=lambda context: Point(context.radius, 0.0),
        )
    )
    assert [sample.point for sample in samples] == [Point(1.0, 0.0)]


def test_a_start_error_skips_that_orbit_and_the_next_radius_still_runs():
    def start(context: StartContext) -> Point:
        if context.radius == 0:
            raise ZeroDivisionError
        return Point(context.radius, 0.0)

    samples = list(
        classic_orbits(
            iterations_per_orbit=1,
            starting_radius=0.0,
            radial_step=1.0,
            max_radius=1.0,
            start_at=start,
        )
    )
    assert [sample.orbit for sample in samples] == [2]
    assert samples[0].iteration == 1
    assert samples[0].point == compiled_classic(1.0).step(Point(1.0, 0.0))
