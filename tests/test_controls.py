import pytest

from henon2midi.domain.controls import (
    _glossary,
    _names,
    describe_midi_target,
    parse_midi_target,
)
from henon2midi.domain.targets import ControlTarget, NoteField


def test_note_fields_stay_out_of_the_controller_map():
    assert parse_midi_target("note") == NoteField.NOTE
    assert parse_midi_target(" Velocity ") == NoteField.VELOCITY


@pytest.mark.parametrize("number", (0, 10, 20, 47, 127))
def test_a_bare_number_and_the_cc_prefix_are_the_same_controller(number):
    assert parse_midi_target(str(number)) == ControlTarget(number)
    assert parse_midi_target(f"cc{number}") == ControlTarget(number)
    assert parse_midi_target(f"CC-{number}") == ControlTarget(number)
    assert parse_midi_target(f"cc {number}") == ControlTarget(number)


@pytest.mark.parametrize(
    ("word", "number"),
    [
        ("pan", 10),
        (" panorama ", 10),
        ("panorama", 10),
        ("volume", 7),
        ("channel-volume", 7),
        ("modulation", 1),
        ("mod_wheel", 1),
        ("knob-3", 20),
        ("Knob 3", 20),
        ("knob-1", 17),
        ("knob-4", 21),
        ("ribbon", 16),
        ("sustain", 64),
        ("damper", 64),
        ("hold", 64),
        ("brightness", 74),
        ("cutoff", 74),
        ("filter cutoff", 74),
        ("resonance", 71),
        ("timbre", 71),
        ("reverb", 91),
        ("effect-1", 12),
        ("effect-control-1", 12),
        ("portamento", 65),
        ("portamento-time", 5),
        ("portamento-control", 84),
    ],
)
def test_words_map_to_the_controller_they_name(word, number):
    assert parse_midi_target(word) == ControlTarget(number)


def test_cc20_and_its_usual_name_are_one_controller():
    assert parse_midi_target("cc20") == parse_midi_target("knob-3")
    assert parse_midi_target("20") == ControlTarget(20)
    assert describe_midi_target(parse_midi_target("cc20")) == "knob-3"
    assert describe_midi_target(parse_midi_target("cutoff")) == "brightness"
    assert describe_midi_target(parse_midi_target("47")) == "cc47"


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("", "must not be empty"),
        ("not-a-control", "Unknown MIDI target"),
        ("-1", "outside 0 to 127"),
        ("cc128", "outside 0 to 127"),
        ("cc200", "outside 0 to 127"),
    ],
)
def test_parse_midi_target_rejects_what_is_not_a_target(text, message):
    with pytest.raises(ValueError, match=message):
        parse_midi_target(text)


def test_a_chart_name_does_not_replace_the_specification_name():
    assert describe_midi_target(parse_midi_target("ribbon")) == "general-purpose-1"
    assert describe_midi_target(parse_midi_target("knob-1")) == "general-purpose-2"
    assert describe_midi_target(parse_midi_target("cc20")) == "knob-3"


def test_a_controller_number_has_to_fit_in_seven_bits():
    with pytest.raises(ValueError, match="outside 0 to 127"):
        ControlTarget(128)


def test_the_glossary_rejects_a_word_that_cannot_mean_one_controller():
    with pytest.raises(ValueError, match="outside 0 to 127"):
        _glossary((_names(128, "too-high"),), ())
    with pytest.raises(ValueError, match="note field"):
        _glossary((_names(1, "note"),), ())
    with pytest.raises(ValueError, match="already maps"):
        _glossary((_names(1, "mod-wheel"), _names(2, "mod_wheel")), ())
