from dataclasses import replace
from itertools import islice

import pytest

from henon2midi.domain.events import NoteOff, NoteOn
from henon2midi.domain.maps import Point, Sample
from henon2midi.domain.plan import plan_iteration
from henon2midi.domain.scaling import UNIT_INTERVAL
from henon2midi.domain.mapping import Mapping
from henon2midi.output.canvas import AsciiCanvas
from henon2midi.output.midi_port import MidiPort
from henon2midi.run import (
    OrbitSchedule,
    Performance,
    MidiSettings,
    Timing,
    events_for,
    events_in_one_pass,
    paint,
    play,
    repeating_samples,
    samples_for,
    visualize,
)


def test_timing_truncates_the_note_duration_and_rejects_zero():
    assert (
        Timing(ticks_per_beat=1000, bpm=90, notes_per_beat=3).note_duration_ticks == 333
    )
    with pytest.raises(ValueError, match="ticks per beat"):
        Timing(ticks_per_beat=0, bpm=120, notes_per_beat=4)
    with pytest.raises(ValueError, match="bpm"):
        Timing(ticks_per_beat=960, bpm=0, notes_per_beat=4)
    with pytest.raises(ValueError, match="notes per beat"):
        Timing(ticks_per_beat=960, bpm=120, notes_per_beat=0)


def test_one_pass_is_finite_and_the_first_classic_point_is_middle_c(tiny_config):
    samples = list(samples_for(tiny_config))
    assert len(samples) == 4
    assert samples[0].point == Point(0.0, 0.0)
    assert events_for(tiny_config, samples[0])[1] == NoteOn(64, 64)
    assert events_in_one_pass(tiny_config) == [
        event for sample in samples for event in events_for(tiny_config, sample)
    ]


def test_looping_restarts_iteration_numbers(tiny_config):
    config = Performance(
        tiny_config.iteration,
        tiny_config.schedule,
        tiny_config.timing,
        tiny_config.mapping,
        loop=True,
    )
    samples = list(islice(repeating_samples(config), 6))
    one_pass = list(samples_for(tiny_config))
    assert [sample.point for sample in samples] == [
        sample.point for sample in one_pass + one_pass[:2]
    ]
    assert samples[4].iteration == 1
    assert samples[4].orbit == 1


def test_play_sends_before_drawing_and_then_stops(tiny_config):
    order = []
    frames = []

    class Port:
        def send(self, events):
            order.append(("send", len(events)))

    def render(sample):
        order.append("render")
        frames.append((sample.iteration, "█" in canvas.generate_string()))

    canvas = AsciiCanvas(5, 5, color_order=["white", "red"])
    play(tiny_config, Port(), canvas, render)

    assert [item[0] if isinstance(item, tuple) else item for item in order] == [
        "send",
        "render",
    ] * 4
    assert [iteration for iteration, _drawn in frames] == [1, 2, 3, 4]
    assert frames[0][1]


def test_play_without_a_canvas_still_sends_every_note(tiny_config):
    sent = []

    class Port:
        def send(self, events):
            sent.append(events)

    play(tiny_config, Port())
    assert len(sent) == 4


def test_play_propagates_keyboard_interrupt(tiny_config):
    class Port:
        def send(self, _events):
            raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        play(tiny_config, Port())


def test_visualize_walks_one_pass_without_a_port(tiny_config):
    frames = []
    canvas = AsciiCanvas(5, 5, color_order=["white", "red"])
    visualize(
        tiny_config,
        canvas,
        lambda sample: frames.append(sample.iteration),
    )
    assert frames == [1, 2, 3, 4]


def test_paint_keeps_points_until_the_next_pass_and_skips_outsiders():
    canvas = AsciiCanvas(5, 5, color_order=["white", "red", "blue"])
    paint(
        canvas,
        Sample(Point(-1, -1), 1, 1, 0, True),
        False,
        UNIT_INTERVAL,
        UNIT_INTERVAL,
    )
    paint(
        canvas,
        Sample(Point(1, 1), 2, 2, 0.2, True),
        False,
        UNIT_INTERVAL,
        UNIT_INTERVAL,
    )
    assert canvas.generate_string().count("█") == 2

    paint(
        canvas,
        Sample(Point(3, 0), 3, 2, 0.2, False),
        False,
        UNIT_INTERVAL,
        UNIT_INTERVAL,
    )
    assert canvas.generate_string().count("█") == 2
    paint(
        canvas,
        Sample(Point(3, 0), 3, 2, 0.2, False),
        True,
        UNIT_INTERVAL,
        UNIT_INTERVAL,
    )
    assert canvas.generate_string().count("█") == 3

    paint(
        canvas, Sample(Point(0, 0), 1, 1, 0, True), False, UNIT_INTERVAL, UNIT_INTERVAL
    )
    assert canvas.generate_string().count("█") == 1


def test_drawing_and_notes_share_the_configured_source_window(tiny_config):
    outside = replace(tiny_config.iteration, step=lambda _point: Point(-1.5, 0.0))
    schedule = replace(
        tiny_config.schedule,
        iterations_per_orbit=1,
        starting_radius=0.0,
        radial_step=1.0,
        max_radius=0.0,
    )
    wide = Mapping(source_range_x=(-2.0, 2.0), source_range_y=(-2.0, 2.0))
    wide_performance = Performance(outside, schedule, tiny_config.timing, wide)
    unit_performance = Performance(
        outside, schedule, tiny_config.timing, tiny_config.mapping
    )
    wide_canvas = AsciiCanvas(5, 5, color_order=["white"])
    visualize(wide_performance, wide_canvas)
    assert "█" in wide_canvas.generate_string()

    unit_canvas = AsciiCanvas(5, 5, color_order=["white"])
    visualize(unit_performance, unit_canvas)
    assert "█" not in unit_canvas.generate_string()

    sample = next(samples_for(unit_performance))
    wide_events = events_for(wide_performance, sample)
    unit_events = events_for(unit_performance, sample)
    assert any(isinstance(event, NoteOn) for event in wide_events)
    assert not any(isinstance(event, NoteOn) for event in unit_events)


def test_sustain_changes_the_events_for_the_same_orbit(tiny_config):
    config = Performance(
        tiny_config.iteration,
        tiny_config.schedule,
        tiny_config.timing,
        Mapping(),
        sustain=True,
    )
    events = events_for(config, next(samples_for(config)))
    assert any(
        getattr(event, "control", None) == 64 and event.value == 127 for event in events
    )
    assert all(getattr(event, "value", None) != 0 for event in events)


def test_play_uses_a_parameter_change_on_the_next_point():
    bound = plan_iteration(None, "x + a", "y", "0; 0").bind((1.0,))
    performance = Performance(
        bound,
        OrbitSchedule(
            iterations_per_orbit=3,
            starting_radius=0.0,
            radial_step=1.0,
            max_radius=0.0,
        ),
        Timing(),
        Mapping(),
    )
    points = []

    class Port:
        def send(self, _events):
            if len(points) == 0:
                performance.parameters.set("a", 5.0)

    play(performance, Port(), render_frame=lambda sample: points.append(sample.point))
    assert points == [Point(1.0, 0.0), Point(6.0, 0.0), Point(11.0, 0.0)]


def test_one_step_keeps_the_midi_it_started_with(tiny_config):
    first_step = {}

    class Port:
        def set_tempo(self, ticks_per_beat, bpm):
            if "tempo" in first_step:
                return
            first_step["tempo"] = (ticks_per_beat, bpm)
            tiny_config.sustain = True
            tiny_config.timing = Timing(bpm=60, notes_per_beat=1)

        def send(self, events):
            if "duration" in first_step:
                return
            first_step["duration"] = next(
                event.time for event in events if isinstance(event, NoteOff)
            )
            first_step["sustain"] = [
                event.value for event in events if getattr(event, "control", None) == 64
            ]

    play(tiny_config, Port())
    assert first_step["tempo"] == (960, 120)
    assert first_step["duration"] == 240
    assert first_step["sustain"] == [0]


def test_play_uses_sustain_and_timing_as_they_stand_for_each_step(tiny_config):
    tempos = []
    sustain_values = []
    durations = []

    class Port:
        def set_tempo(self, ticks_per_beat, bpm):
            tempos.append((ticks_per_beat, bpm))

        def send(self, events):
            sustain_values.append(
                [
                    event.value
                    for event in events
                    if getattr(event, "control", None) == 64
                ]
            )
            durations.append(
                next(event.time for event in events if isinstance(event, NoteOff))
            )
            if len(durations) == 1:
                tiny_config.sustain = True
                tiny_config.timing = Timing(bpm=60, notes_per_beat=1)

    play(tiny_config, Port())
    assert tempos[0] == (960, 120)
    assert tempos[1] == (960, 60)
    assert sustain_values[0] == [0]
    assert sustain_values[1] == [127]
    assert durations[0] == 240
    assert durations[1] == 960


def test_replacing_the_mapping_changes_whether_an_outside_point_plays(tiny_config):
    sample = Sample(Point(-1.5, 0.0), 1, 1, 0.0, True)
    assert not any(
        isinstance(event, NoteOn) for event in events_for(tiny_config, sample)
    )
    tiny_config.mapping = Mapping(
        source_range_x=(-2.0, 2.0), source_range_y=(-2.0, 2.0)
    )
    assert any(isinstance(event, NoteOn) for event in events_for(tiny_config, sample))


def test_assigning_midi_settings_changes_the_next_step_together(tiny_config):
    sample = next(samples_for(tiny_config))
    before = events_for(tiny_config, sample)
    tiny_config.midi_settings = MidiSettings(
        Timing(notes_per_beat=1), Mapping(), sustain=True
    )
    after = events_for(tiny_config, sample)
    assert next(event.time for event in before if isinstance(event, NoteOff)) == 240
    assert next(event.time for event in after if isinstance(event, NoteOff)) == 960
    assert [
        event.value for event in after if getattr(event, "control", None) == 64
    ] == [127]


def test_the_schedule_can_change_without_replacing_the_iteration(tiny_config):
    parameters = tiny_config.parameters
    tiny_config.schedule = replace(tiny_config.schedule, iterations_per_orbit=1)
    assert tiny_config.parameters is parameters
    assert tiny_config.iteration.parameters is parameters
    with pytest.raises(AttributeError):
        tiny_config.iteration = tiny_config.iteration


def test_turning_loop_off_stops_after_the_current_pass(tiny_config):
    tiny_config.loop = True
    samples = repeating_samples(tiny_config)
    assert [sample.iteration for sample in islice(samples, 4)] == [1, 2, 3, 4]
    tiny_config.loop = False
    assert list(samples) == []


def test_the_next_pass_uses_the_orbit_schedule_as_it_stands(tiny_config):
    tiny_config.loop = True
    samples = repeating_samples(tiny_config)
    assert len(list(islice(samples, 4))) == 4
    tiny_config.schedule = replace(
        tiny_config.schedule,
        iterations_per_orbit=1,
        radial_step=1.0,
        max_radius=0.0,
    )
    assert [sample.iteration for sample in islice(samples, 1)] == [1]
    tiny_config.loop = False
    assert list(samples) == []


class _Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


def test_play_follows_a_bpm_change_on_the_midi_port(tiny_config):
    slept = []

    def sleeper(delay):
        slept.append(delay)
        clock.now += delay

    clock = _Clock()
    port = MidiPort(
        "ignored",
        ticks_per_beat=960,
        bpm=120,
        output=_SilentOutput(),
        clock=clock,
        sleeper=sleeper,
    )

    def slow_down(sample):
        if sample.iteration == 1:
            tiny_config.timing = Timing(bpm=60)

    play(tiny_config, port, render_frame=slow_down)
    assert slept == pytest.approx([0.125, 0.25, 0.25, 0.25])


class _SilentOutput:
    def send(self, _message):
        return None

    def reset(self):
        return None

    def close(self):
        return None
