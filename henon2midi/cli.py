import click
import pkg_resources
from mido import Message

from henon2midi.ascii_art import AsciiArtCanvas
from henon2midi.base import create_midi_file_from_midi_generator
from henon2midi.henon_midi_generator import HenonMidiGenerator
from henon2midi.math import rescale_number_to_range
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
    default="velocity,pan",
    help="The MIDI parameter mappings for the y data point.",
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
def cli(
    a_parameter: float,
    iterations_per_orbit: int,
    midi_output_name: str,
    ticks_per_beat: int,
    bpm: int,
    notes_per_beat: int,
    x_midi_parameter_mappings: str,
    y_midi_parameter_mappings: str,
    starting_radius: float,
    radial_step: float,
    out: str,
    draw_ascii_art: bool,
    sustain: bool,
    clip: bool,
):
    """An application that generates midi from procedurally generated Henon mappings."""

    package = "henon2midi"
    version = pkg_resources.require(package)[0].version
    version_string = package + " v" + version + "\n\n"
    click.echo(version_string)

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
        f"\tstarting radius: {starting_radius}\n"
        f"\tradial step: {radial_step}\n"
        f"\tout: {midi_output_file_name}\n"
        f"\tdraw ascii art: {draw_ascii_art}\n"
        f"\tsustain: {sustain}\n"
        f"\tclip: {clip}\n"
        f"\n"
    )
    click.echo(options_string)

    henon_midi_generator = HenonMidiGenerator(
        a_parameter=a_parameter,
        iterations_per_orbit=iterations_per_orbit,
        starting_radius=starting_radius,
        radial_step=radial_step,
        note_length_ticks=ticks_per_beat // notes_per_beat,
        sustain=sustain,
        clip=clip,
        x_midi_parameter_mappings=x_midi_parameter_mappings_set,
        y_midi_parameter_mappings=y_midi_parameter_mappings_set,
    )

    if midi_output_file_name:
        mid = create_midi_file_from_midi_generator(
            henon_midi_generator, ticks_per_beat=ticks_per_beat, bpm=bpm
        )
        mid.save(midi_output_file_name)

    if draw_ascii_art:
        ascii_art_canvas_width = 160
        ascii_art_canvas_height = 80
        ascii_art_canvas = AsciiArtCanvas(
            ascii_art_canvas_width, ascii_art_canvas_height
        )
    art_string = ""

    if midi_output_name:
        midi_message_player = MidiMessagePlayer(
            midi_output_name=midi_output_name, ticks_per_beat=ticks_per_beat, bpm=bpm
        )
        while True:
            messages = henon_midi_generator.next_midi_messages()
            current_iteration = henon_midi_generator.current_iteration
            current_orbit = (
                current_iteration // henon_midi_generator.iterations_per_orbit
            )
            try:
                midi_message_player.send(messages)
            except KeyboardInterrupt:
                midi_message_player.midi_output.reset()
                for note in range(128):
                    midi_message_player.midi_output.send(
                        Message("note_off", note=note, velocity=0)
                    )
                sustain_off_msg = Message("control_change", control=64, value=0)
                midi_message_player.midi_output.send(sustain_off_msg)
                midi_message_player.midi_output.close()
                exit()
            current_state_string = (
                f"Current iteration: {current_iteration}\n"
                f"Current orbit: {current_orbit + 1}\n"
                "\n"
            )

            if draw_ascii_art:
                art_string = get_ascii_art(
                    henon_midi_generator.current_data_point,
                    current_iteration,
                    henon_midi_generator.iterations_per_orbit,
                    ascii_art_canvas,
                )

            click.clear()
            screen_render = (
                version_string + options_string + current_state_string + art_string
            )
            click.echo(screen_render)


def get_ascii_art(
    data_point: tuple[float, float],
    current_iteration,
    iterations_per_orbit,
    ascii_art_canvas: AsciiArtCanvas,
) -> str:
    if current_iteration == 0:
        ascii_art_canvas.clear()
    x = data_point[0]
    y = data_point[1]
    draw_point_coord = (
        round(rescale_number_to_range(x, (-1.0, 1.0), (0, ascii_art_canvas.width - 1))),
        round(
            rescale_number_to_range(y, (-1.0, 1.0), (0, ascii_art_canvas.height - 1))
        ),
    )
    ascii_art_canvas.draw_point(draw_point_coord[0], draw_point_coord[1], ".")

    if current_iteration % iterations_per_orbit == 0:
        ascii_art_canvas.set_color("random")
    return ascii_art_canvas.generate_string()
