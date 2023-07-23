"""Tests for hello function."""
import pytest

from henon2midi.midi import get_default_midi_output_name


@pytest.fixture
def mock_get_output_names(mocker):
    mocker.patch("henon2midi.midi.get_output_names", return_value=["Bus 1", "Bus 2"])


@pytest.fixture
def mock_get_output_names_empty(mocker):
    mocker.patch("henon2midi.midi.get_output_names", return_value=[])


def test_get_default_midi_output_name(mock_get_output_names):
    assert get_default_midi_output_name() == "Bus 1"


def test_get_default_midi_output_name_empty(mock_get_output_names_empty):
    with pytest.raises(Exception):
        get_default_midi_output_name()
