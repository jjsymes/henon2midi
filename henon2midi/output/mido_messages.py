from mido import Message

from henon2midi.domain.events import ControlChange, MidiEvent, NoteOff, NoteOn


def to_mido(event: MidiEvent) -> Message:
    if isinstance(event, NoteOn):
        return Message(
            "note_on", note=event.note, velocity=event.velocity, time=event.time
        )
    if isinstance(event, NoteOff):
        return Message(
            "note_off", note=event.note, velocity=event.velocity, time=event.time
        )
    if isinstance(event, ControlChange):
        return Message(
            "control_change",
            control=event.control,
            value=event.value,
            time=event.time,
        )
    raise TypeError(f"Unsupported MIDI event {event!r}")
