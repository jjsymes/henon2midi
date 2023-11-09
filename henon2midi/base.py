from mido import Message, MidiFile

from henon2midi.data_point_to_midi_conversion import (
    create_midi_messages_from_data_point,
)
from henon2midi.henon_equations import RadiallyExpandingHenonMappingsGenerator
from henon2midi.midi import create_midi_file_from_messages


def create_midi_file_from_data_generator(
    henon_midi_generator: RadiallyExpandingHenonMappingsGenerator,
    ticks_per_beat: int = 960,
    bpm: int = 120,
    notes_per_beat: int = 4,
    sustain: bool = False,
    clip: bool = False,
    x_midi_parameter_mappings_set: set[str] = {"note"},
    y_midi_parameter_mappings_set: set[str] = {"velocity"},
    source_range_x: tuple[float, float] = (-1.0, 1.0),
    source_range_y: tuple[float, float] = (-1.0, 1.0),
    midi_range_x: tuple[int, int] = (0, 127),
    midi_range_y: tuple[int, int] = (0, 127),
    default_note: int = 64,
    default_velocity: int = 64,
) -> MidiFile:
    messages = []
    if sustain:
        sustain_on_msg = Message(
            "control_change",
            control=64,
            value=127,
        )
        messages.append(sustain_on_msg)
    for datapoint in henon_midi_generator:
        messages.extend(
            create_midi_messages_from_data_point(
                datapoint,
                duration_ticks=int(ticks_per_beat / notes_per_beat),
                clip=clip,
                x_midi_parameter_mappings=x_midi_parameter_mappings_set,
                y_midi_parameter_mappings=y_midi_parameter_mappings_set,
                source_range_x=source_range_x,
                source_range_y=source_range_y,
                midi_range_x=midi_range_x,
                midi_range_y=midi_range_y,
                default_note=default_note,
                default_velocity=default_velocity,
            )
        )
    return create_midi_file_from_messages(messages, ticks_per_beat, bpm)
