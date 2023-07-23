"""Tests for hello function."""
import pytest

from henon2midi.math import rescale_number_to_range


@pytest.mark.parametrize(
    ("value", "initial_range", "new_range", "expected"),
    [
        (-1.0, (-1.0, 1.0), (0, 127), 0.0),
        (0.0, (-1.0, 1.0), (0, 127), 63.5),
        (1.0, (-1.0, 1.0), (0, 127), 127.0),
        (-1.0, (-1.0, 1.0), (10, 20), 10.0),
        (0.0, (-1.0, 1.0), (10, 20), 15.0),
        (1.0, (-1.0, 1.0), (10, 20), 20.0),
    ],
)
def test_rescale_number_to_range(value, initial_range, new_range, expected):
    assert (
        rescale_number_to_range(value, initial_range, new_range, clip_value=False)
        == expected
    )


@pytest.mark.parametrize(
    ("value", "initial_range", "new_range", "expected"),
    [
        (-1000.0, (-1.0, 1.0), (0, 127), 0),
        (0.0, (-1.0, 1.0), (0, 127), 63.5),
        (100.0, (-1.0, 1.0), (0, 127), 127),
    ],
)
def test_rescale_number_to_range_with_clipping(
    value, initial_range, new_range, expected
):
    assert (
        rescale_number_to_range(value, initial_range, new_range, clip_value=True)
        == expected
    )


@pytest.mark.parametrize(
    ("value", "initial_range", "new_range"),
    [
        (-1000.0, (-1.0, 1.0), (0, 127)),
        (100.0, (-1.0, 1.0), (0, 127)),
    ],
)
def test_rescale_number_to_range_value_out_of_initial_range_raises_error(
    value, initial_range, new_range
):
    with pytest.raises(ValueError):
        rescale_number_to_range(value, initial_range, new_range, clip_value=False)
