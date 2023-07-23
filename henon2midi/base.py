from mido import MetaMessage, MidiFile, MidiTrack, bpm2tempo

from henon2midi.henon_midi_generator import HenonMidiGenerator


def create_midi_file_from_midi_generator(
    henon_midi_generator: HenonMidiGenerator,
    ticks_per_beat: int = 960,
    bpm: int = 120,
) -> MidiFile:
    mid = MidiFile(ticks_per_beat=ticks_per_beat)
    track = MidiTrack()
    mid.tracks.append(track)
    tempo = bpm2tempo(bpm)
    track.append(MetaMessage("set_tempo", tempo=tempo))
    track.extend(henon_midi_generator.generate_all_midi_messages())
    return mid
