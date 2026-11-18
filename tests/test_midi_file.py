from mido import MidiFile, bpm2tempo

from henon2midi.domain.events import ControlChange, NoteOff, NoteOn
from henon2midi.output.midi_file import (
    midi_file_from_events,
    midi_file_from_messages,
    write_midi_file,
)
from henon2midi.output.mido_messages import to_mido


def test_event_file_starts_with_tempo_and_keeps_delta_times(tmp_path):
    events = [
        ControlChange(10, 64),
        NoteOn(60, 100),
        NoteOff(60, 40, 240),
    ]
    midi_file = midi_file_from_events(events, ticks_per_beat=480, bpm=100)

    assert midi_file.ticks_per_beat == 480
    track = midi_file.tracks[0]
    assert track[0].type == "set_tempo"
    assert track[0].tempo == bpm2tempo(100)
    assert [(message.type, message.time) for message in track[1:]] == [
        ("control_change", 0),
        ("note_on", 0),
        ("note_off", 240),
    ]
    assert track[2].note == 60
    assert track[2].velocity == 100
    assert track[3].velocity == 40

    path = tmp_path / "song.mid"
    write_midi_file(str(path), events, 480, 100)
    loaded = MidiFile(path)
    assert loaded.ticks_per_beat == 480
    assert loaded.tracks[0][0].tempo == bpm2tempo(100)
    loaded_messages = [
        message for message in loaded.tracks[0] if message.type != "end_of_track"
    ]
    assert loaded_messages[2].note == 60
    assert [message.bytes() for message in loaded_messages[1:]] == [
        to_mido(event).bytes() for event in events
    ]


def test_a_file_without_a_tempo_contains_only_the_messages():
    message = to_mido(NoteOn(64, 64))
    midi_file = midi_file_from_messages([message], ticks_per_beat=960, tempo=None)
    assert [event.type for event in midi_file.tracks[0]] == ["note_on"]
