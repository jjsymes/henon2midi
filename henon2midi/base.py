from mido import MetaMessage, MidiFile, MidiTrack, bpm2tempo

from henon2midi.data_point_to_midi_conversion import (
    create_midi_messages_from_data_point,
)
from henon2midi.henon_equations import RadiallyExpandingHenonMappingsGenerator


def create_midi_file_from_data_generator(
    henon_midi_generator: RadiallyExpandingHenonMappingsGenerator,
    ticks_per_beat: int = 960,
    bpm: int = 120,
    notes_per_beat: int = 4,
    sustain: bool = False,
    clip: bool = False,
    x_midi_parameter_mappings_set: set[str] = {"note"},
    y_midi_parameter_mappings_set: set[str] = {"velocity", "pan"},
) -> MidiFile:
    mid = MidiFile(ticks_per_beat=ticks_per_beat)
    track = MidiTrack()
    mid.tracks.append(track)
    tempo = bpm2tempo(bpm)
    track.append(MetaMessage("set_tempo", tempo=tempo))
    for datapoint in henon_midi_generator.radially_expending_henon_mappings_generator():
        midi_messages = create_midi_messages_from_data_point(
            datapoint,
            duration_ticks=int(ticks_per_beat / notes_per_beat),
            sustain=sustain,
            clip=clip,
            x_midi_parameter_mappings=x_midi_parameter_mappings_set,
            y_midi_parameter_mappings=y_midi_parameter_mappings_set,
        )
        track.extend(midi_messages)
    return mid
