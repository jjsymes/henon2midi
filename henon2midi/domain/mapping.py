from dataclasses import dataclass

from henon2midi.domain.events import (
    CENTER_PAN,
    MIDI_VALUE_RANGE,
    PAN_CONTROL,
    SUSTAIN_CONTROL,
    SUSTAIN_OFF_VALUE,
    SUSTAIN_ON_VALUE,
    ControlChange,
    MidiEvent,
    NoteOff,
    NoteOn,
)
from henon2midi.domain.maps import Point
from henon2midi.domain.scaling import UNIT_INTERVAL, rescale, within_range
from henon2midi.domain.targets import ControlTarget, MidiTarget, NoteField

DEFAULT_MIDI_VALUE = 64


@dataclass(frozen=True)
class _MidiValues:
    note: int
    velocity: int
    controls: tuple[tuple[ControlTarget, int], ...]


@dataclass(frozen=True)
class Mapping:
    x_targets: tuple[MidiTarget, ...] = (NoteField.NOTE,)
    y_targets: tuple[MidiTarget, ...] = (NoteField.VELOCITY, ControlTarget(PAN_CONTROL))
    source_range_x: tuple[float, float] = UNIT_INTERVAL
    source_range_y: tuple[float, float] = UNIT_INTERVAL
    midi_range_x: tuple[int, int] = MIDI_VALUE_RANGE
    midi_range_y: tuple[int, int] = MIDI_VALUE_RANGE
    clamp: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "x_targets", _without_duplicate_targets(self.x_targets)
        )
        object.__setattr__(
            self, "y_targets", _without_duplicate_targets(self.y_targets)
        )
        object.__setattr__(
            self,
            "midi_range_x",
            _validated_midi_range(self.midi_range_x, "x midi range"),
        )
        object.__setattr__(
            self,
            "midi_range_y",
            _validated_midi_range(self.midi_range_y, "y midi range"),
        )


def midi_events(
    point: Point,
    mapping: Mapping,
    duration_ticks: int,
    sustain: bool = False,
) -> list[MidiEvent]:
    values = _midi_values(point, mapping)
    events: list[MidiEvent] = []
    _append_before_note(events, values, sustain)
    if mapping.clamp or _inside_source(point, mapping):
        events.append(NoteOn(values.note, values.velocity))
    events.append(NoteOff(values.note, values.velocity, duration_ticks))
    _append_after_note(events, values, sustain)
    return events


def _midi_values(point: Point, mapping: Mapping) -> _MidiValues:
    values = _MidiValues(DEFAULT_MIDI_VALUE, DEFAULT_MIDI_VALUE, ())
    values = _with_axis(
        values,
        mapping.x_targets,
        point.x,
        mapping.source_range_x,
        mapping.midi_range_x,
    )
    return _with_axis(
        values,
        mapping.y_targets,
        point.y,
        mapping.source_range_y,
        mapping.midi_range_y,
    )


def _with_axis(
    values: _MidiValues,
    targets: tuple[MidiTarget, ...],
    source: float,
    source_range: tuple[float, float],
    midi_range: tuple[int, int],
) -> _MidiValues:
    if not targets:
        return values
    midi_value = _scaled_midi_value(source, source_range, midi_range)
    note = values.note
    velocity = values.velocity
    controls = dict(values.controls)
    for target in targets:
        if target is NoteField.NOTE:
            note = midi_value
        elif target is NoteField.VELOCITY:
            velocity = midi_value
        else:
            controls[target] = midi_value
    return _MidiValues(note, velocity, tuple(controls.items()))


def _scaled_midi_value(
    value: float,
    source_range: tuple[float, float],
    midi_range: tuple[int, int],
) -> int:
    return round(rescale(value, source_range, midi_range, clip_value=True))


def _inside_source(point: Point, mapping: Mapping) -> bool:
    return within_range(point.x, mapping.source_range_x) and within_range(
        point.y, mapping.source_range_y
    )


def _append_before_note(
    events: list[MidiEvent],
    values: _MidiValues,
    sustain: bool,
) -> None:
    for control, value in values.controls:
        events.append(ControlChange(control.number, value))
    if sustain:
        events.append(ControlChange(SUSTAIN_CONTROL, SUSTAIN_ON_VALUE))


def _append_after_note(
    events: list[MidiEvent],
    values: _MidiValues,
    sustain: bool,
) -> None:
    if _uses_pan(values):
        events.append(ControlChange(PAN_CONTROL, CENTER_PAN))
    if not sustain:
        events.append(ControlChange(SUSTAIN_CONTROL, SUSTAIN_OFF_VALUE))


def _uses_pan(values: _MidiValues) -> bool:
    return any(control.number == PAN_CONTROL for control, _value in values.controls)


def _without_duplicate_targets(
    targets: tuple[MidiTarget, ...],
) -> tuple[MidiTarget, ...]:
    chosen: list[MidiTarget] = []
    for target in targets:
        if target not in chosen:
            chosen.append(target)
    return tuple(chosen)


def _validated_midi_range(midi_range: tuple[int, int], name: str) -> tuple[int, int]:
    if len(midi_range) != 2:
        raise ValueError(f"{name} must be two values")
    start, end = midi_range
    if start < 0 or start > 127 or end < 0 or end > 127:
        raise ValueError(f"{name} values must be between 0 and 127")
    return start, end
