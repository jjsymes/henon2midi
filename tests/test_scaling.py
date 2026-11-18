import math

import pytest

from henon2midi.domain.scaling import point_to_cell, rescale, within_range


@pytest.mark.parametrize(
    ("value", "initial_range", "new_range", "expected"),
    [
        (-1.0, (-1.0, 1.0), (0, 127), 0.0),
        (0.0, (-1.0, 1.0), (0, 127), 63.5),
        (1.0, (-1.0, 1.0), (0, 127), 127.0),
        (-1.0, (-1.0, 1.0), (10, 20), 10.0),
        (0.0, (-1.0, 1.0), (10, 20), 15.0),
        (1.0, (-1.0, 1.0), (10, 20), 20.0),
        (5.0, (0.0, 10.0), (0.0, 10.0), 5.0),
        (-1.0, (-1.0, 1.0), (10.0, 0.0), 10.0),
        (1.0, (-1.0, 1.0), (10.0, 0.0), 0.0),
        (0.0, (-1.0, 1.0), (10.0, 0.0), 5.0),
        (3.0, (0.0, 10.0), (4.0, 4.0), 4.0),
    ],
)
def test_rescale_maps_endpoints_and_midpoints(
    value, initial_range, new_range, expected
):
    assert rescale(value, initial_range, new_range, clip_value=False) == expected


@pytest.mark.parametrize(
    ("value", "initial_range", "new_range", "expected"),
    [
        (-1000.0, (-1.0, 1.0), (0, 127), 0),
        (0.0, (-1.0, 1.0), (0, 127), 63.5),
        (100.0, (-1.0, 1.0), (0, 127), 127),
        (math.inf, (-1.0, 1.0), (0, 10), 10),
        (-math.inf, (-1.0, 1.0), (0, 10), 0),
    ],
)
def test_rescale_with_clipping(value, initial_range, new_range, expected):
    assert rescale(value, initial_range, new_range, clip_value=True) == expected


@pytest.mark.parametrize(
    ("value", "initial_range", "new_range"),
    [
        (-1000.0, (-1.0, 1.0), (0, 127)),
        (100.0, (-1.0, 1.0), (0, 127)),
        (math.inf, (-1.0, 1.0), (0, 127)),
    ],
)
def test_rescale_value_out_of_initial_range_raises_error(
    value, initial_range, new_range
):
    with pytest.raises(ValueError, match="not within initial_range"):
        rescale(value, initial_range, new_range, clip_value=False)


def test_rescale_rejects_a_zero_width_source_range():
    with pytest.raises(ValueError, match="non-zero width"):
        rescale(1.0, (5.0, 5.0), (0, 1))


@pytest.mark.parametrize(
    ("value", "initial_range", "new_range"),
    [
        (math.nan, (-1.0, 1.0), (0, 1)),
        (0.0, (math.nan, 1.0), (0, 1)),
        (0.0, (-1.0, 1.0), (math.inf, 1.0)),
    ],
)
def test_rescale_rejects_non_finite_inputs(value, initial_range, new_range):
    with pytest.raises(ValueError):
        rescale(value, initial_range, new_range)


def test_within_range_is_inclusive_and_rejects_non_numbers():
    assert within_range(-1.0, (-1.0, 1.0))
    assert within_range(1.0, (-1.0, 1.0))
    assert not within_range(1.1, (-1.0, 1.0))
    assert not within_range(math.nan, (-1.0, 1.0))
    assert not within_range(math.inf, (-1.0, 1.0))


def test_point_to_cell_maps_the_unit_square_onto_the_canvas():
    assert point_to_cell(-1.0, -1.0, width=11, height=5) == (0, 0)
    assert point_to_cell(0.0, 0.0, width=11, height=5) == (5, 2)
    assert point_to_cell(1.0, 1.0, width=11, height=5) == (10, 4)


def test_point_to_cell_skips_points_outside_the_source_range():
    assert point_to_cell(1.1, 0.0, width=11, height=5, clamp=False) is None
    assert point_to_cell(0.0, -1.1, width=11, height=5, clamp=False) is None
    assert point_to_cell(math.nan, 0.0, width=11, height=5, clamp=True) is None


def test_point_to_cell_clamps_to_the_edge_when_asked():
    assert point_to_cell(4.0, -4.0, width=11, height=5, clamp=True) == (10, 0)


def test_point_to_cell_rejects_an_empty_canvas():
    with pytest.raises(ValueError, match="at least 1"):
        point_to_cell(0.0, 0.0, width=0, height=4)
