from dataclasses import dataclass

PAN_CONTROL = 10
SUSTAIN_CONTROL = 64
CENTER_PAN = 64
SUSTAIN_ON_VALUE = 127
SUSTAIN_OFF_VALUE = 0
MIDI_VALUE_RANGE = (0, 127)


@dataclass(frozen=True)
class NoteOn:
    note: int
    velocity: int
    time: int = 0


@dataclass(frozen=True)
class NoteOff:
    note: int
    velocity: int
    time: int = 0


@dataclass(frozen=True)
class ControlChange:
    control: int
    value: int
    time: int = 0


MidiEvent = NoteOn | NoteOff | ControlChange


def silence_events() -> list[MidiEvent]:
    events: list[MidiEvent] = [NoteOff(note, 0) for note in range(128)]
    events.append(ControlChange(SUSTAIN_CONTROL, SUSTAIN_OFF_VALUE))
    return events
