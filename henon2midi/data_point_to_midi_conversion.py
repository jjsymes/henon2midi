from typing import List, Tuple, Set
from mido import Message

from henon2midi.math import rescale_number_to_range


def create_midi_messages_from_data_point(
    datapoint: Tuple[float, float],
    duration_ticks: float = 960,
    clip: bool = False,
    x_midi_parameter_mappings: Set[str] = {"note"},
    y_midi_parameter_mappings: Set[str] = {"velocity"},
    source_range_x: Tuple[float, float] = (-1.0, 1.0),
    source_range_y: Tuple[float, float] = (-1.0, 1.0),
    midi_range_x: Tuple[int, int] = (0, 127),
    midi_range_y: Tuple[int, int] = (0, 127),
    default_note: int = 64,
    default_velocity: int = 64,
) -> List[Message]:
    x = datapoint[0]
    y = datapoint[1]

    midi_values = {
        "note": default_note,
        "velocity": default_velocity,
    }

    control_numbers = {
        "modulation": 1,
        "breath": 2,
        "foot_controller": 4,
        "portamento_time": 5,
        "volume": 7,
        "balance": 8,
        "pan": 10,
        "expression": 11,
        "effect_control_1": 12,
        "effect_control_2": 13,
        "general_purpose_controller_1": 16,
        "general_purpose_controller_2": 17,
        "general_purpose_controller_3": 18,
        "general_purpose_controller_4": 19,
        "bank_select": 32,
        "modulation_wheel": 33,
        "breath_controller": 34,
        "foot_pedal": 36,
        "portamento": 37,
        "data_entry": 38,
        "sustain": 64,
        "portamento_65": 65,
        "sostenuto": 66,
        "soft_pedal": 67,
        "legato_footswitch": 68,
        "hold_2": 69,
        "sound_controller_1": 70,
        "sound_controller_2": 71,
        "sound_controller_3": 72,
        "sound_controller_4": 73,
        "sound_controller_5": 74,
        "sound_controller_6": 75,
        "sound_controller_7": 76,
        "sound_controller_8": 77,
        "sound_controller_9": 78,
        "sound_controller_10": 79,
        "general_purpose_controller_5": 80,
        "general_purpose_controller_6": 81,
        "general_purpose_controller_7": 82,
        "general_purpose_controller_8": 83,
        "portamento_control": 84,
        "high_resolution_velocity_prefix": 88,
        "effects_1_depth": 91,
        "effects_2_depth": 92,
        "effects_3_depth": 93,
        "effects_4_depth": 94,
        "effects_5_depth": 95,
    }

    for x_midi_parameter_mapping in x_midi_parameter_mappings:
        midi_values[x_midi_parameter_mapping] = midi_value_from_data_value(
            x,
            source_range=source_range_x,
            midi_range=midi_range_x,
        )

    for y_midi_parameter_mapping in y_midi_parameter_mappings:
        midi_values[y_midi_parameter_mapping] = midi_value_from_data_value(
            y,
            source_range=source_range_y,
            midi_range=midi_range_y,
        )

    note_on = Message(
        "note_on",
        note=midi_values["note"],
        velocity=midi_values["velocity"],
    )
    note_off = Message(
        "note_off",
        note=midi_values["note"],
        velocity=midi_values["velocity"],
        time=duration_ticks,
    )

    if (
        x > source_range_x[1]
        or x < source_range_x[0]
        or y > source_range_y[1]
        or y < source_range_y[0]
    ) and not clip:
        note_messages = [note_off]
    else:
        note_messages = [note_on, note_off]
    pre_note_messages: List[Message] = []
    post_note_messages: List[Message] = []

    for midi_value_name, midi_value in midi_values.items():
        if midi_value_name == "note" or midi_value_name == "velocity":
            continue
        try:
            control_number = control_numbers[midi_value_name]
            pre_note_messages.append(
                Message(
                    "control_change",
                    control=control_number,
                    value=midi_value,
                )
            )
        except KeyError:
            raise ValueError(f"Unknown midi control: {midi_value_name}")

    messages = pre_note_messages + note_messages + post_note_messages

    return messages


def midi_value_from_data_value(
    value: float,
    source_range: tuple[float, float] = (-1.0, 1.0),
    midi_range: tuple[int, int] = (0, 127),
) -> int:
    min_midi_value = midi_range[0]
    max_midi_value = midi_range[1]

    min_data_point_value = source_range[0]
    max_data_point_value = source_range[1]

    return round(
        rescale_number_to_range(
            value,
            (min_data_point_value, max_data_point_value),
            (min_midi_value, max_midi_value),
            clip_value=True,
        )
    )
