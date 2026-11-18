import pytest
from mido import bpm2tempo

from henon2midi.domain.events import ControlChange, NoteOff, NoteOn
from henon2midi.domain.maps import Point, expanding_orbits
from henon2midi.domain.plan import plan_iteration
from henon2midi.domain.mapping import Mapping, midi_events
from henon2midi.output.midi_file import midi_file_from_events
from henon2midi.run import OrbitSchedule, Performance, Timing, events_in_one_pass


def _classic(parameters: tuple[float, ...], **kwargs):
    bound = plan_iteration("classic", None, None, "diagonal").bind(parameters)
    return expanding_orbits(bound.step, start_at=bound.start_at, **kwargs)


def _describe(event):
    if isinstance(event, NoteOn):
        return ("note_on", event.time, event.note, event.velocity, None, None)
    if isinstance(event, NoteOff):
        return ("note_off", event.time, event.note, event.velocity, None, None)
    if isinstance(event, ControlChange):
        return ("control_change", event.time, None, None, event.control, event.value)
    raise AssertionError(f"unexpected event {event!r}")


def test_orbit_prefix_radius_and_boundaries():
    samples = list(
        _classic(
            (1.333,),
            iterations_per_orbit=3,
            starting_radius=0.0,
            radial_step=0.2,
        )
    )[:9]
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
        samples, expected, strict=True
    ):
        assert sample.point.x == pytest.approx(x)
        assert sample.point.y == pytest.approx(y)
        assert sample.radius == pytest.approx(radius)
        assert (sample.iteration, sample.orbit, sample.is_orbit_start) == (
            iteration,
            orbit,
            is_start,
        )


def test_default_coefficients_keep_the_same_opening_points():
    samples = list(
        _classic(
            (1.0,),
            iterations_per_orbit=100,
            starting_radius=0.0,
            radial_step=0.01,
        )
    )
    expected = [
        (0, 0.0, 0.0, 0.0),
        (99, 0.0, 0.0, 0.0),
        (100, -0.0029275396909167785, 0.01376370267617355, 0.01),
        (101, -0.013156301073527894, 0.004968489931664477, 0.01),
    ]
    for index, x, y, radius in expected:
        sample = samples[index]
        assert sample.point.x == pytest.approx(x)
        assert sample.point.y == pytest.approx(y)
        assert sample.radius == pytest.approx(radius)


def test_in_range_point_message_order_and_timing():
    events = midi_events(Point(0.0, 0.0), Mapping(), 240)
    assert [_describe(event) for event in events] == [
        ("control_change", 0, None, None, 10, 64),
        ("note_on", 0, 64, 64, None, None),
        ("note_off", 240, 64, 64, None, None),
        ("control_change", 0, None, None, 10, 64),
        ("control_change", 0, None, None, 64, 0),
    ]


def test_out_of_range_point_is_a_rest_unless_clipped():
    resting = midi_events(Point(2.0, -2.0), Mapping(clamp=False), 240)
    clipped = midi_events(Point(2.0, -2.0), Mapping(clamp=True), 240)
    assert [_describe(event) for event in resting] == [
        ("control_change", 0, None, None, 10, 0),
        ("note_off", 240, 127, 0, None, None),
        ("control_change", 0, None, None, 10, 64),
        ("control_change", 0, None, None, 64, 0),
    ]
    assert [_describe(event) for event in clipped] == [
        ("control_change", 0, None, None, 10, 0),
        ("note_on", 0, 127, 0, None, None),
        ("note_off", 240, 127, 0, None, None),
        ("control_change", 0, None, None, 10, 64),
        ("control_change", 0, None, None, 64, 0),
    ]


def test_sustain_and_pan_controls():
    events = midi_events(Point(0.25, -0.5), Mapping(), 48, sustain=True)
    assert [_describe(event) for event in events] == [
        ("control_change", 0, None, None, 10, 32),
        ("control_change", 0, None, None, 64, 127),
        ("note_on", 0, 79, 32, None, None),
        ("note_off", 48, 79, 32, None, None),
        ("control_change", 0, None, None, 10, 64),
    ]


def test_midi_file_starts_with_tempo_then_the_same_events():
    events = midi_events(Point(0.0, 0.0), Mapping(), 240)
    midi_file = midi_file_from_events(events, ticks_per_beat=960, bpm=120)
    assert midi_file.ticks_per_beat == 960
    assert midi_file.tracks[0][0].type == "set_tempo"
    assert midi_file.tracks[0][0].tempo == bpm2tempo(120)
    assert len(midi_file.tracks[0]) == len(events) + 1


def test_file_export_uses_one_finite_pass():
    bound = plan_iteration("classic", None, None, "diagonal").bind((1.333,))
    config = Performance(
        bound,
        OrbitSchedule(
            iterations_per_orbit=2,
            starting_radius=0.0,
            radial_step=0.5,
        ),
        Timing(ticks_per_beat=960, bpm=100, notes_per_beat=4),
        Mapping(),
    )
    events = events_in_one_pass(config)
    midi_file = midi_file_from_events(events, ticks_per_beat=960, bpm=100)
    assert sum(isinstance(event, NoteOn) for event in events) == 6
    assert midi_file.tracks[0][0].tempo == bpm2tempo(100)
