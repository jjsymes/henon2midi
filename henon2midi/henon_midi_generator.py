from mido import Message

from henon2midi.henon_equations import radially_expanding_henon_mappings_generator
from henon2midi.math import rescale_number_to_range


class HenonMidiGenerator:
    def __init__(
        self,
        a_parameter: float,
        iterations_per_orbit: int = 50,
        starting_radius: float = 0.0,
        radial_step: float = 0.05,
        note_length_ticks: int = 960,
        sustain: bool = False,
        clip: bool = False,
        x_midi_parameter_mappings: set[str] = {"note"},
        y_midi_parameter_mappings: set[str] = {"velocity", "pan"},
    ):
        self.a_parameter = a_parameter
        self.iterations_per_orbit = iterations_per_orbit
        self.starting_radius = starting_radius
        self.radial_step = radial_step
        self.note_length_ticks = note_length_ticks
        self.sustain = sustain
        self.clip = clip
        self.x_midi_parameter_mappings = x_midi_parameter_mappings
        self.y_midi_parameter_mappings = y_midi_parameter_mappings
        self.current_iteration = 0
        self.current_radius = self.starting_radius
        self.current_data_point = (self.starting_radius, self.starting_radius)
        self.current_iteration_midi_messages: list[Message] = []
        self.datapoint_generator = radially_expanding_henon_mappings_generator(
            a_parameter=self.a_parameter,
            iterations_per_orbit=self.iterations_per_orbit,
            starting_radius=self.starting_radius,
            radial_step=self.radial_step,
        )
        self.reset()

    def next_midi_messages(self) -> list[Message]:
        try:
            datapoint = next(self.datapoint_generator)
        except StopIteration:
            self.reset()
            midi_messages = self.current_iteration_midi_messages
        else:
            self.current_data_point = datapoint
            self.current_iteration += 1
            if self.current_iteration % self.iterations_per_orbit == 0:
                self.current_radius += self.radial_step
                self.datapoint_generator = radially_expanding_henon_mappings_generator(
                    a_parameter=self.a_parameter,
                    iterations_per_orbit=self.iterations_per_orbit,
                    starting_radius=self.current_radius,
                    radial_step=self.radial_step,
                )
            midi_messages = create_midi_messages_from_data_point(
                datapoint,
                duration_ticks=self.note_length_ticks,
                sustain=self.sustain,
                clip=self.clip,
                x_midi_parameter_mappings=self.x_midi_parameter_mappings,
                y_midi_parameter_mappings=self.y_midi_parameter_mappings,
            )
            self.current_iteration_midi_messages = midi_messages
        return midi_messages

    def reset(self):
        self.current_iteration = 0
        self.current_radius = self.starting_radius
        self.current_data_point = (self.starting_radius, self.starting_radius)
        self.current_iteration_midi_messages = create_midi_messages_from_data_point(
            self.current_data_point,
            duration_ticks=self.note_length_ticks,
            sustain=self.sustain,
            clip=self.clip,
            x_midi_parameter_mappings=self.x_midi_parameter_mappings,
            y_midi_parameter_mappings=self.y_midi_parameter_mappings,
        )
        self.datapoint_generator = radially_expanding_henon_mappings_generator(
            a_parameter=self.a_parameter,
            iterations_per_orbit=self.iterations_per_orbit,
            starting_radius=self.starting_radius,
            radial_step=self.radial_step,
        )

    def generate_all_midi_messages(self) -> list[Message]:
        self.reset()
        complete = False
        midi_messages = []
        midi_messages.extend(self.current_iteration_midi_messages)
        while not complete:
            midi_messages.extend(self.next_midi_messages())
            if self.current_iteration == 0:
                complete = True
        return midi_messages


def create_midi_messages_from_data_point(
    datapoint: tuple[float, float],
    duration_ticks: float = 960,
    sustain: bool = False,
    clip: bool = False,
    x_midi_parameter_mappings: set[str] = {"note"},
    y_midi_parameter_mappings: set[str] = {"velocity", "pan"},
) -> list[Message]:
    x = datapoint[0]
    y = datapoint[1]

    midi_values = {
        "note": 64,
        "velocity": 64,
        "pan": 64,
    }

    for x_midi_parameter_mapping in x_midi_parameter_mappings:
        if (x > 1.0 or x < -1.0) and not clip:
            midi_values[x_midi_parameter_mapping] = 0
        else:
            midi_values[x_midi_parameter_mapping] = midi_value_from_data_point_value(x)

    for y_midi_parameter_mapping in y_midi_parameter_mappings:
        if (y > 1.0 or y < -1.0) and not clip:
            midi_values[y_midi_parameter_mapping] = 0
        else:
            midi_values[y_midi_parameter_mapping] = midi_value_from_data_point_value(y)

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
    data_point_range: tuple[float, float] = (-1.0, 1.0),
    midi_range: tuple[int, int] = (0, 127),
) -> int:
    min_midi_value = midi_range[0]
    max_midi_value = midi_range[1]

    min_data_point_value = data_point_range[0]
    max_data_point_value = data_point_range[1]

    return round(
        rescale_number_to_range(
            x,
            (min_data_point_value, max_data_point_value),
            (min_midi_value, max_midi_value),
            clip_value=True,
        )
    )
