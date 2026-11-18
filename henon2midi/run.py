from collections.abc import Callable, Iterator
from dataclasses import dataclass, replace
from typing import Protocol, runtime_checkable

from henon2midi.domain.events import MidiEvent
from henon2midi.domain.maps import MAX_ORBIT_RADIUS, Sample, expanding_orbits
from henon2midi.domain.parameters import Parameters
from henon2midi.domain.plan import BoundIteration
from henon2midi.domain.scaling import point_to_cell
from henon2midi.domain.mapping import Mapping, midi_events

BLOCK = "█"


@dataclass(frozen=True)
class Timing:
    ticks_per_beat: int = 960
    bpm: int = 120
    notes_per_beat: int = 4

    def __post_init__(self) -> None:
        if self.ticks_per_beat < 1:
            raise ValueError("ticks per beat must be at least 1")
        if self.bpm < 1:
            raise ValueError("bpm must be at least 1")
        if self.notes_per_beat < 1:
            raise ValueError("notes per beat must be at least 1")

    @property
    def note_duration_ticks(self) -> int:
        return int(self.ticks_per_beat / self.notes_per_beat)


@dataclass(frozen=True)
class OrbitSchedule:
    iterations_per_orbit: int = 100
    starting_radius: float = 0.0
    radial_step: float = 0.01
    max_radius: float = MAX_ORBIT_RADIUS
    seed: int = 0


@dataclass(frozen=True)
class MidiSettings:
    timing: Timing
    mapping: Mapping
    sustain: bool = False


class Performance:
    def __init__(
        self,
        iteration: BoundIteration,
        schedule: OrbitSchedule,
        timing: Timing,
        mapping: Mapping,
        sustain: bool = False,
        loop: bool = False,
    ) -> None:
        self._iteration = iteration
        self.schedule = schedule
        self._midi_settings = MidiSettings(timing, mapping, sustain)
        self.loop = loop

    @property
    def iteration(self) -> BoundIteration:
        return self._iteration

    @property
    def parameters(self) -> Parameters:
        return self._iteration.parameters

    @property
    def midi_settings(self) -> MidiSettings:
        return self._midi_settings

    @midi_settings.setter
    def midi_settings(self, midi_settings: MidiSettings) -> None:
        self._midi_settings = midi_settings

    @property
    def timing(self) -> Timing:
        return self._midi_settings.timing

    @timing.setter
    def timing(self, timing: Timing) -> None:
        self._midi_settings = replace(self._midi_settings, timing=timing)

    @property
    def mapping(self) -> Mapping:
        return self._midi_settings.mapping

    @mapping.setter
    def mapping(self, mapping: Mapping) -> None:
        self._midi_settings = replace(self._midi_settings, mapping=mapping)

    @property
    def sustain(self) -> bool:
        return self._midi_settings.sustain

    @sustain.setter
    def sustain(self, sustain: bool) -> None:
        self._midi_settings = replace(self._midi_settings, sustain=sustain)


class MidiSender(Protocol):
    def send(self, events: list[MidiEvent]) -> None:
        pass


@runtime_checkable
class TempoControl(Protocol):
    def set_tempo(self, ticks_per_beat: int, bpm: int) -> None:
        pass


class Canvas(Protocol):
    width: int
    height: int

    def clear(self) -> None:
        pass

    def set_color(self, color: str) -> None:
        pass

    def draw_point(self, x: int, y: int, character: str = "X") -> None:
        pass


FrameRenderer = Callable[[Sample], None]


def samples_for(performance: Performance) -> Iterator[Sample]:
    schedule = performance.schedule
    iteration = performance.iteration
    return expanding_orbits(
        iteration.step,
        iterations_per_orbit=schedule.iterations_per_orbit,
        starting_radius=schedule.starting_radius,
        radial_step=schedule.radial_step,
        max_radius=schedule.max_radius,
        start_at=iteration.start_at,
        seed=schedule.seed,
    )


def repeating_samples(performance: Performance) -> Iterator[Sample]:
    while True:
        yield from samples_for(performance)
        if not performance.loop:
            return


def events_for(performance: Performance, sample: Sample) -> list[MidiEvent]:
    return _events(sample, performance.midi_settings)


def events_in_one_pass(performance: Performance) -> list[MidiEvent]:
    events: list[MidiEvent] = []
    for sample in samples_for(performance):
        events.extend(events_for(performance, sample))
    return events


def _events(sample: Sample, midi_settings: MidiSettings) -> list[MidiEvent]:
    return midi_events(
        sample.point,
        midi_settings.mapping,
        midi_settings.timing.note_duration_ticks,
        sustain=midi_settings.sustain,
    )


def paint(
    canvas: Canvas,
    sample: Sample,
    clamp: bool,
    source_range_x: tuple[float, float],
    source_range_y: tuple[float, float],
) -> None:
    if sample.iteration == 1:
        canvas.clear()
    if sample.is_orbit_start:
        canvas.set_color("next")
    cell = point_to_cell(
        sample.point.x,
        sample.point.y,
        canvas.width,
        canvas.height,
        source_range_x=source_range_x,
        source_range_y=source_range_y,
        clamp=clamp,
    )
    if cell is None:
        return
    column, row = cell
    canvas.draw_point(column, row, BLOCK)


def play(
    performance: Performance,
    port: MidiSender,
    canvas: Canvas | None = None,
    render_frame: FrameRenderer | None = None,
) -> None:
    for sample in repeating_samples(performance):
        midi_settings = performance.midi_settings
        _set_tempo(port, midi_settings.timing)
        port.send(_events(sample, midi_settings))
        _show(canvas, render_frame, sample, midi_settings.mapping)


def visualize(
    performance: Performance,
    canvas: Canvas,
    render_frame: FrameRenderer | None = None,
) -> None:
    for sample in repeating_samples(performance):
        _show(canvas, render_frame, sample, performance.midi_settings.mapping)


def _show(
    canvas: Canvas | None,
    render_frame: FrameRenderer | None,
    sample: Sample,
    mapping: Mapping,
) -> None:
    if canvas is not None:
        paint(
            canvas,
            sample,
            mapping.clamp,
            mapping.source_range_x,
            mapping.source_range_y,
        )
    if render_frame is not None:
        render_frame(sample)


def _set_tempo(port: MidiSender, timing: Timing) -> None:
    if isinstance(port, TempoControl):
        port.set_tempo(timing.ticks_per_beat, timing.bpm)
