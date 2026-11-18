import pytest

from henon2midi.domain.events import (
    CENTER_PAN,
    PAN_CONTROL,
    SUSTAIN_CONTROL,
    SUSTAIN_OFF_VALUE,
    SUSTAIN_ON_VALUE,
    ControlChange,
    NoteOff,
    NoteOn,
    silence_events,
)
from henon2midi.domain.maps import Point
from henon2midi.domain.mapping import Mapping, midi_events
from henon2midi.domain.targets import ControlTarget, NoteField

NOTE = NoteField.NOTE
VELOCITY = NoteField.VELOCITY
PAN = ControlTarget(PAN_CONTROL)


def _describe(event):
    if isinstance(event, NoteOn):
        return ("note_on", event.time, event.note, event.velocity, None, None)
    if isinstance(event, NoteOff):
        return ("note_off", event.time, event.note, event.velocity, None, None)
    return ("control_change", event.time, None, None, event.control, event.value)


@pytest.mark.parametrize(
    ("point", "duration", "sustain", "clamp", "x_targets", "y_targets", "expected"),
    [
        (
            Point(0.0, 0.0),
            240,
            False,
            False,
            (NOTE,),
            (VELOCITY, PAN),
            [
                ("control_change", 0, None, None, 10, 64),
                ("note_on", 0, 64, 64, None, None),
                ("note_off", 240, 64, 64, None, None),
                ("control_change", 0, None, None, 10, 64),
                ("control_change", 0, None, None, 64, 0),
            ],
        ),
        (
            Point(-1.0, -1.0),
            10,
            False,
            False,
            (NOTE,),
            (VELOCITY, PAN),
            [
                ("control_change", 0, None, None, 10, 0),
                ("note_on", 0, 0, 0, None, None),
                ("note_off", 10, 0, 0, None, None),
                ("control_change", 0, None, None, 10, 64),
                ("control_change", 0, None, None, 64, 0),
            ],
        ),
        (
            Point(1.0, 1.0),
            10,
            False,
            False,
            (NOTE,),
            (VELOCITY, PAN),
            [
                ("control_change", 0, None, None, 10, 127),
                ("note_on", 0, 127, 127, None, None),
                ("note_off", 10, 127, 127, None, None),
                ("control_change", 0, None, None, 10, 64),
                ("control_change", 0, None, None, 64, 0),
            ],
        ),
        (
            Point(2.0, -2.0),
            240,
            False,
            False,
            (NOTE,),
            (VELOCITY, PAN),
            [
                ("control_change", 0, None, None, 10, 0),
                ("note_off", 240, 127, 0, None, None),
                ("control_change", 0, None, None, 10, 64),
                ("control_change", 0, None, None, 64, 0),
            ],
        ),
        (
            Point(2.0, -2.0),
            240,
            False,
            True,
            (NOTE,),
            (VELOCITY, PAN),
            [
                ("control_change", 0, None, None, 10, 0),
                ("note_on", 0, 127, 0, None, None),
                ("note_off", 240, 127, 0, None, None),
                ("control_change", 0, None, None, 10, 64),
                ("control_change", 0, None, None, 64, 0),
            ],
        ),
        (
            Point(-0.2, 0.4),
            30,
            False,
            False,
            (PAN,),
            (VELOCITY,),
            [
                ("control_change", 0, None, None, 10, 51),
                ("note_on", 0, 64, 89, None, None),
                ("note_off", 30, 64, 89, None, None),
                ("control_change", 0, None, None, 10, 64),
                ("control_change", 0, None, None, 64, 0),
            ],
        ),
        (
            Point(0.25, -0.5),
            48,
            True,
            False,
            (NOTE,),
            (VELOCITY, PAN),
            [
                ("control_change", 0, None, None, 10, 32),
                ("control_change", 0, None, None, 64, 127),
                ("note_on", 0, 79, 32, None, None),
                ("note_off", 48, 79, 32, None, None),
                ("control_change", 0, None, None, 10, 64),
            ],
        ),
    ],
)
def test_midi_events_message_shape(
    point, duration, sustain, clamp, x_targets, y_targets, expected
):
    mapping = Mapping(x_targets=x_targets, y_targets=y_targets, clamp=clamp)
    events = midi_events(point, mapping, duration, sustain=sustain)
    assert [_describe(event) for event in events] == expected


def test_y_mapping_overwrites_the_same_target_on_x():
    events = midi_events(
        Point(0.0, 1.0),
        Mapping(x_targets=(NOTE,), y_targets=(NOTE,)),
        duration_ticks=10,
    )
    assert events == [
        NoteOn(127, 64),
        NoteOff(127, 64, 10),
        ControlChange(SUSTAIN_CONTROL, SUSTAIN_OFF_VALUE),
    ]


def test_unmapped_controls_keep_their_defaults_and_skip_pan():
    events = midi_events(Point(1.0, -1.0), Mapping(x_targets=(), y_targets=()), 7)
    assert events == [
        NoteOn(64, 64),
        NoteOff(64, 64, 7),
        ControlChange(SUSTAIN_CONTROL, SUSTAIN_OFF_VALUE),
    ]


def test_only_one_axis_outside_the_source_is_a_rest():
    events = midi_events(Point(0.0, 2.0), Mapping(), 20)
    assert isinstance(events[1], NoteOff)
    assert all(not isinstance(event, NoteOn) for event in events)


def test_custom_ranges_scale_each_axis_and_pan_still_resets_to_center():
    mapping = Mapping(
        x_targets=(NOTE, PAN),
        y_targets=(VELOCITY,),
        source_range_x=(0.0, 10.0),
        source_range_y=(-5.0, 5.0),
        midi_range_x=(10, 20),
        midi_range_y=(0, 100),
    )
    events = midi_events(Point(0.0, 0.0), mapping, 10)
    assert events[0] == ControlChange(PAN_CONTROL, 10)
    assert events[1] == NoteOn(10, 50)
    assert events[2] == NoteOff(10, 50, 10)
    assert events[3] == ControlChange(PAN_CONTROL, CENTER_PAN)


def test_inverted_midi_range_reverses_the_note():
    low = midi_events(
        Point(-1.0, 0.0),
        Mapping(x_targets=(NOTE,), y_targets=(), midi_range_x=(127, 0)),
        1,
    )
    high = midi_events(
        Point(1.0, 0.0),
        Mapping(x_targets=(NOTE,), y_targets=(), midi_range_x=(127, 0)),
        1,
    )
    assert low[0] == NoteOn(127, 64)
    assert high[0] == NoteOn(0, 64)


def test_duplicate_targets_are_collapsed():
    mapping = Mapping(
        x_targets=(NOTE, NOTE, PAN, PAN),
        y_targets=(ControlTarget(20), ControlTarget(20)),
    )
    assert mapping.x_targets == (NOTE, PAN)
    assert mapping.y_targets == (ControlTarget(20),)


@pytest.mark.parametrize(
    "midi_range",
    [(0, 200), (-1, 10)],
)
def test_mapping_rejects_a_midi_range_outside_seven_bits(midi_range):
    with pytest.raises(ValueError, match="between 0 and 127"):
        Mapping(midi_range_x=midi_range)


def test_mapping_rejects_a_midi_range_that_is_not_a_pair():
    with pytest.raises(ValueError, match="two values"):
        Mapping(midi_range_x=(0,))


def test_one_axis_drives_a_note_and_several_controllers():
    events = midi_events(
        Point(0.0, 1.0),
        Mapping(
            x_targets=(NOTE, ControlTarget(7), ControlTarget(20)),
            y_targets=(VELOCITY, ControlTarget(11)),
        ),
        10,
    )
    assert events == [
        ControlChange(7, 64),
        ControlChange(20, 64),
        ControlChange(11, 127),
        NoteOn(64, 127),
        NoteOff(64, 127, 10),
        ControlChange(SUSTAIN_CONTROL, SUSTAIN_OFF_VALUE),
    ]


def test_y_overwrites_the_same_controller_on_x():
    events = midi_events(
        Point(-1.0, 1.0),
        Mapping(x_targets=(NOTE, PAN), y_targets=(PAN,)),
        4,
    )
    assert events[0] == ControlChange(PAN_CONTROL, 127)
    assert events[1] == NoteOn(0, 64)


def test_pan_returns_to_center_after_the_note():
    events = midi_events(
        Point(0.0, 0.0),
        Mapping(x_targets=(NOTE,), y_targets=(PAN,)),
        5,
    )
    assert events[0] == ControlChange(PAN_CONTROL, 64)
    assert events[-2] == ControlChange(PAN_CONTROL, CENTER_PAN)


def test_events_are_frozen_and_silence_releases_every_note():
    with pytest.raises(AttributeError):
        NoteOn(60, 100).note = 61

    events = silence_events()
    assert events[:-1] == [NoteOff(note, 0) for note in range(128)]
    assert events[-1] == ControlChange(SUSTAIN_CONTROL, SUSTAIN_OFF_VALUE)
    assert SUSTAIN_ON_VALUE == 127
