from mido import Message, MetaMessage, MidiFile, MidiTrack, bpm2tempo

from henon2midi.domain.events import MidiEvent
from henon2midi.output.mido_messages import to_mido


def midi_file_from_messages(
    messages: list[Message],
    ticks_per_beat: int,
    tempo: int | None,
) -> MidiFile:
    midi_file = MidiFile(ticks_per_beat=ticks_per_beat)
    track = MidiTrack()
    midi_file.tracks.append(track)
    if tempo is not None:
        track.append(MetaMessage("set_tempo", tempo=tempo))
    track.extend(messages)
    return midi_file


def midi_file_from_events(
    events: list[MidiEvent], ticks_per_beat: int, bpm: int
) -> MidiFile:
    return midi_file_from_messages(
        [to_mido(event) for event in events],
        ticks_per_beat,
        bpm2tempo(bpm),
    )


def write_midi_file(
    path: str, events: list[MidiEvent], ticks_per_beat: int, bpm: int
) -> None:
    midi_file_from_events(events, ticks_per_beat, bpm).save(path)
