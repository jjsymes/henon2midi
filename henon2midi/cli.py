import click
import pkg_resources
from mido import Message

from henon2midi.ascii_art import AsciiArtCanvas, draw_data_point_on_canvas
from henon2midi.base import create_midi_file_from_data_generator
from henon2midi.data_point_to_midi_conversion import (
    create_midi_messages_from_data_point,
)
from henon2midi.henon_equations import RadiallyExpandingHenonMappingsGenerator
from henon2midi.midi import (
    MidiMessagePlayer,
    get_available_midi_output_names,
    get_default_midi_output_name,
)


@click.version_option()
@click.command()
@click.option(
    "-a",
    "--a-parameter",
    default=1.0,
    help="The a parameter for the Henon mapping.",
    show_default=True,
    type=float,
)
@click.option(
    "-i",
    "--iterations-per-orbit",
    default=100,
    help="The number of iterations per orbit.",
    show_default=True,
    type=int,
)
@click.option(
    "-m",
    "--midi-output-name",
    default=get_default_midi_output_name(),
    help=(
        "The name of the MIDI output device, "
        "Available: [{}]".format(", ".join(set(get_available_midi_output_names())))
    ),
    show_default=True,
    type=str,
)
@click.option(
    "--ticks-per-beat",
    default=960,
    help="The number of ticks per beat.",
    show_default=True,
    type=int,
)
@click.option(
    "--bpm",
    default=120,
    help="The beats per minute.",
    show_default=True,
    type=int,
)
@click.option(
    "--notes-per-beat",
    default=4,
    help="The number of notes per beat.",
    show_default=True,
    type=int,
)
@click.option(
    "--x-midi-parameter-mappings",
    default="note",
    help="The MIDI parameter mappings for the x data point.",
    show_default=True,
    type=str,
)
@click.option(
    "--y-midi-parameter-mappings",
    default="velocity",
    help="The MIDI parameter mappings for the y data point.",
    show_default=True,
    type=str,
)
@click.option(
    "--x-midi-value-range",
    default="0,127",
    help="The MIDI value range for the x data point.",
    show_default=True,
    type=str,
)
@click.option(
    "--y-midi-value-range",
    default="0,127",
    help="The MIDI value range for the y data point.",
    show_default=True,
    type=str,
)
@click.option(
    "-r",
    "--starting-radius",
    default=0.0,
    help="The starting radius for the Henon mapping.",
    show_default=True,
    type=float,
)
@click.option(
    "-s",
    "--radial-step",
    default=0.01,
    help="The radial step for the Henon mapping.",
    show_default=True,
    type=float,
)
@click.option(
    "-o",
    "--out",
    default="henon.mid",
    help="The path to the output MIDI file.",
    show_default=True,
    type=str,
)
@click.option(
    "--draw-ascii-art",
    is_flag=True,
    help="Draw the Henon mapping in ASCII art.",
    type=bool,
)
@click.option("--sustain", is_flag=True, help="Turn the sustain on.", type=bool)
@click.option(
    "--clip",
    is_flag=True,
    help="Clip the MIDI messages to the range of the MIDI parameter.",
    type=bool,
)
@click.option(
    "--default-note",
    default=64,
    help="Default note that plays if note is not mapped to henon output.",
    show_default=True,
    type=int,
)
@click.option(
    "--default-velocity",
    default=64,
    help="Default velocity of note that plays if note is not mapped to henon output.",
    show_default=True,
    type=int,
)
@click.option(
    "--no-output",
    is_flag=True,
    help="Stop midi from playing, write to midi file only.",
    type=bool,
    default=False,
    show_default=True,
)
@click.option(
    "--continual-loop",
    is_flag=True,
    help="Loop back to start when Henon data is exhausted.",
    type=bool,
)
def cli(
    a_parameter: float,
    iterations_per_orbit: int,
    midi_output_name: str,
    ticks_per_beat: int,
    bpm: int,
    notes_per_beat: int,
    x_midi_parameter_mappings: str,
    y_midi_parameter_mappings: str,
    x_midi_value_range: str,
    y_midi_value_range: str,
    starting_radius: float,
    radial_step: float,
    out: str,
    draw_ascii_art: bool,
    sustain: bool,
    clip: bool,
    continual_loop: bool,
    default_note: int,
    default_velocity: int,
    no_output: bool,
):
    """An application that generates midi from procedurally generated Henon mappings."""

    package = "henon2midi"
    version = pkg_resources.require(package)[0].version
    version_string = package + " v" + version + "\n\n"

    midi_output_file_name = out
    if midi_output_name == "default":
        midi_output_name = get_default_midi_output_name()
    else:
        midi_output_name = midi_output_name
    ticks_per_beat = ticks_per_beat
    bpm = bpm
    notes_per_beat = notes_per_beat
    x_midi_parameter_mappings_set = set(x_midi_parameter_mappings.split(","))
    y_midi_parameter_mappings_set = set(y_midi_parameter_mappings.split(","))
    if "" in x_midi_parameter_mappings_set:
        x_midi_parameter_mappings_set.remove("")
    if "" in y_midi_parameter_mappings_set:
        y_midi_parameter_mappings_set.remove("")
    x_midi_value_range_split = x_midi_value_range.split(",")
    if len(x_midi_value_range_split) != 2:
        raise ValueError(
            "x_midi_value_range must be a comma separated list of 2 values"
        )
    else:
        midi_range_x = (
            int(x_midi_value_range_split[0]),
            int(x_midi_value_range_split[1]),
        )
    y_midi_value_range_split = y_midi_value_range.split(",")
    if len(y_midi_value_range_split) != 2:
        raise ValueError(
            "y_midi_value_range must be a comma separated list of 2 values"
        )
    else:
        midi_range_y = (
            int(y_midi_value_range_split[0]),
            int(y_midi_value_range_split[1]),
        )
    starting_radius = starting_radius
    radial_step = radial_step
    draw_ascii_art = draw_ascii_art
    sustain = sustain
    clip = clip

    options_string = (
        "Running with the following parameters. Use --help to see all available options.\n"
        f"\ta parameter: {a_parameter}\n"
        f"\titerations per orbit: {iterations_per_orbit}\n"
        f"\tmidi output name: {midi_output_name}\n"
        f"\tticks per beat: {ticks_per_beat}\n"
        f"\tbpm: {bpm}\n"
        f"\tnotes per beat: {notes_per_beat}\n"
        f"\tx midi parameter mappings: {x_midi_parameter_mappings_set}\n"
        f"\ty midi parameter mappings: {y_midi_parameter_mappings_set}\n"
        f"\tx midi value range: {midi_range_x}\n"
        f"\ty midi value range: {midi_range_y}\n"
        f"\tstarting radius: {starting_radius}\n"
        f"\tradial step: {radial_step}\n"
        f"\tout: {midi_output_file_name}\n"
        f"\tdraw ascii art: {draw_ascii_art}\n"
        f"\tsustain: {sustain}\n"
        f"\tclip: {clip}\n"
        f"\n"
    )

    click.echo(version_string + options_string)

    if midi_output_file_name:
        mid = create_midi_file_from_data_generator(
            RadiallyExpandingHenonMappingsGenerator(
                a_parameter=a_parameter,
                iterations_per_orbit=iterations_per_orbit,
                starting_radius=starting_radius,
                radial_step=radial_step,
            ),
            ticks_per_beat=ticks_per_beat,
            bpm=bpm,
            notes_per_beat=notes_per_beat,
            sustain=sustain,
            clip=clip,
            x_midi_parameter_mappings_set=x_midi_parameter_mappings_set,
            y_midi_parameter_mappings_set=y_midi_parameter_mappings_set,
            source_range_x=(-1.0, 1.0),
            source_range_y=(-1.0, 1.0),
            midi_range_x=midi_range_x,
            midi_range_y=midi_range_y,
            default_note=default_note,
            default_velocity=default_velocity,
        )
        mid.save(midi_output_file_name)

    if draw_ascii_art:
        ascii_art_canvas_width = 160
        ascii_art_canvas_height = 80
        ascii_art_canvas = AsciiArtCanvas(
            ascii_art_canvas_width, ascii_art_canvas_height
        )

    if midi_output_name and not no_output:
        hennon_mappings_generator = RadiallyExpandingHenonMappingsGenerator(
            a_parameter=a_parameter,
            iterations_per_orbit=iterations_per_orbit,
            starting_radius=starting_radius,
            radial_step=radial_step,
        )

        midi_message_player = MidiMessagePlayer(
            midi_output_name=midi_output_name, ticks_per_beat=ticks_per_beat, bpm=bpm
        )
        midi_message_player.reset()

        if sustain:
            sustain_on_msg = Message(
                "control_change",
                control=64,
                value=127,
            )
            midi_message_player.send(sustain_on_msg)

        while True:
            messages = create_midi_messages_from_data_point(
                hennon_mappings_generator.generate_next_data_point(),
                duration_ticks=int(ticks_per_beat / notes_per_beat),
                clip=clip,
                x_midi_parameter_mappings=x_midi_parameter_mappings_set,
                y_midi_parameter_mappings=y_midi_parameter_mappings_set,
                source_range_x=(-1.0, 1.0),
                source_range_y=(-1.0, 1.0),
                midi_range_x=midi_range_x,
                midi_range_y=midi_range_y,
                default_note=default_note,
                default_velocity=default_velocity,
            )

            current_iteration = hennon_mappings_generator.get_current_iteration()
            current_orbit = hennon_mappings_generator.get_current_orbital_iteration()
            current_data_point = hennon_mappings_generator.get_current_data_point()
            is_new_orbit = hennon_mappings_generator.is_new_orbit()

            if not continual_loop:
                if hennon_mappings_generator.get_times_reset() > 0:
                    break

            if draw_ascii_art:
                draw_data_point_on_canvas(
                    current_data_point,
                    ascii_art_canvas,
                    is_new_orbit,
                    current_iteration,
                    clip=clip,
                )
                art_string = ascii_art_canvas.generate_string()
            else:
                art_string = ""
            
            current_state_string = (
                f"Current iteration: {current_iteration}\n"
                f"Current orbit: {current_orbit}\n"
                f"Current data point: {current_data_point}\n"
                "\n"
            )

            refresh_terminal_screen(
                version_string,
                options_string,
                current_state_string,
                art_string,
            )

            try:
                midi_message_player.send(messages)
            except KeyboardInterrupt:
                midi_message_player.reset()
                exit()


def refresh_terminal_screen(
    version_string: str,
    options_string: str,
    current_state_string: str="",
    art_string: str="",
):
    click.clear()
    screen_render = (
        version_string + options_string + current_state_string + art_string
    )
    click.echo(screen_render)
