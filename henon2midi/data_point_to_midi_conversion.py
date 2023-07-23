from mido import Message

from henon2midi.math import rescale_number_to_range


def create_midi_messages_from_data_point(
    datapoint: tuple[float, float],
    duration_ticks: float = 960,
    sustain: bool = False,
    clip: bool = False,
    x_midi_parameter_mappings: set[str] = {"note"},
    y_midi_parameter_mappings: set[str] = {"velocity", "pan"},
    source_range_x: tuple[float, float] = (-1.0, 1.0),
    source_range_y: tuple[float, float] = (-1.0, 1.0),
    midi_range_x: tuple[int, int] = (0, 127),
    midi_range_y: tuple[int, int] = (0, 127),
) -> list[Message]:
    x = datapoint[0]
    y = datapoint[1]

    midi_values = {
        "note": 64,
        "velocity": 64,
        "pan": 64,
    }

    for x_midi_parameter_mapping in x_midi_parameter_mappings:
        if (x > source_range_x[1] or x < source_range_x[0]) and not clip:
            midi_values["velocity"] = 0
        else:
            midi_values[x_midi_parameter_mapping] = midi_value_from_data_point_value(
                x,
                source_range=source_range_x,
                midi_range=midi_range_x,
            )

    for y_midi_parameter_mapping in y_midi_parameter_mappings:
        if (y > source_range_y[1] or y < source_range_y[0]) and not clip:
            midi_values["velocity"] = 0
        else:
            midi_values[y_midi_parameter_mapping] = midi_value_from_data_point_value(
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

    note_messages = [note_on, note_off]
    pre_note_messages = []
    post_note_messages = []

    if "pan" in x_midi_parameter_mappings or "pan" in y_midi_parameter_mappings:
        pan = Message(
            "control_change",
            control=10,
            value=midi_values["pan"],
        )
        pre_note_messages.append(pan)

        reset_pan = Message(
            "control_change",
            control=10,
            value=64,
        )
        post_note_messages.append(reset_pan)

    if sustain:
        sustain_on_msg = Message(
            "control_change",
            control=64,
            value=127,
        )
        pre_note_messages.append(sustain_on_msg)
    else:
        sustain_off_msg = Message(
            "control_change",
            control=64,
            value=0,
        )
        post_note_messages.append(sustain_off_msg)

    messages = pre_note_messages + note_messages + post_note_messages

    return messages


def midi_value_from_data_point_value(
    x: float,
    source_range: tuple[float, float] = (-1.0, 1.0),
    midi_range: tuple[int, int] = (0, 127),
) -> int:
    min_midi_value = midi_range[0]
    max_midi_value = midi_range[1]

    min_data_point_value = source_range[0]
    max_data_point_value = source_range[1]

    return round(
        rescale_number_to_range(
            x,
            (min_data_point_value, max_data_point_value),
            (min_midi_value, max_midi_value),
            clip_value=True,
        )
    )
