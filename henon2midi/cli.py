import sys
from dataclasses import dataclass
from importlib.metadata import version

import click

from henon2midi.domain.controls import describe_midi_targets, parse_midi_targets
from henon2midi.domain.maps import MAX_ORBIT_RADIUS, Sample, require_orbit_arguments
from henon2midi.domain.parsing import (
    parse_midi_range,
    parse_parameters,
    parse_source_range,
)
from henon2midi.domain.plan import BoundIteration, plan_iteration
from henon2midi.domain.presets import PRESETS
from henon2midi.domain.mapping import Mapping
from henon2midi.help_text import verbose_help
from henon2midi.output.canvas import AsciiCanvas
from henon2midi.output.midi_file import write_midi_file
from henon2midi.output.midi_port import (
    MidiOutputNotFound,
    MidiPort,
    available_midi_output_names,
    resolve_midi_output_name,
)
from henon2midi.output.terminal import TerminalDisplay, grid_size, read_terminal_size
from henon2midi.run import (
    FrameRenderer,
    OrbitSchedule,
    Performance,
    Timing,
    events_in_one_pass,
    play,
    visualize,
)


def package_version() -> str:
    return version("henon2midi")


def _list_midi_outputs(context: click.Context, _parameter, enabled: bool) -> None:
    if not enabled or context.resilient_parsing:
        return
    names = available_midi_output_names()
    if not names:
        raise click.ClickException("No MIDI output devices found")
    for name in names:
        click.echo(name)
    context.exit()


def _print_verbose_help(context: click.Context, _parameter, enabled: bool) -> None:
    if not enabled or context.resilient_parsing:
        return
    click.echo(verbose_help())
    click.echo()
    click.echo(context.get_help(), color=context.color)
    context.exit()


@click.command("henon2midi")
@click.version_option(package_name="henon2midi", message="henon2midi %(version)s")
@click.option(
    "--help-verbose",
    is_flag=True,
    is_eager=True,
    expose_value=False,
    callback=_print_verbose_help,
    help=(
        "Explain the Henon map, orbits, and how a run becomes MIDI, "
        "then print this option reference, and exit."
    ),
)
@click.option(
    "--list-midi-outputs",
    is_flag=True,
    is_eager=True,
    expose_value=False,
    callback=_list_midi_outputs,
    help=(
        "Print the names of MIDI outputs, then exit. Pass one of them "
        "to --midi-output-name."
    ),
)
@click.option(
    "--map",
    "map_name",
    default="classic",
    show_default=True,
    type=click.Choice(tuple(PRESETS)),
    help=(
        "Built-in map. classic preserves area: its parameter a is a rotation "
        "angle in radians (the default 1 is about 57 degrees), and its window "
        "is -1 to 1. four-parameter couples sines and cosines with parameters "
        "a, b, c, and d, and its window is -2 to 2. --x-prime and --y-prime "
        "replace this choice. Passing them together with --map is an error."
    ),
)
@click.option(
    "--x-prime",
    default=None,
    help=(
        "Expression for the next x. A name other than x, y, pi, e, or a "
        "function is a parameter, filled from -p in alphabetical order. "
        "r, n, and u are only available in --start. Requires --y-prime. "
        "A leading minus needs an equals sign: --x-prime=-y."
    ),
)
@click.option(
    "--y-prime",
    default=None,
    help=(
        "Expression for the next y. Same names and functions as --x-prime. "
        "Requires --x-prime. A leading minus needs an equals sign: --y-prime=-x."
    ),
)
@click.option(
    "--start",
    default="diagonal",
    show_default=True,
    help=(
        "Where each orbit's seed is placed. diagonal is the point (r, r). "
        "random is one point on the circle of radius r; --seed fixes it. "
        "sweep walks around that circle by one radian per orbit. Or pass two "
        "expressions separated by ';', using r, n (orbit index from 0), "
        "u (one sample in [0, 1) per orbit), pi, e, and the parameter names."
    ),
)
@click.option(
    "--source-range",
    default=None,
    help=(
        "Window that x and y are read from, as two comma-separated ends. "
        "The low end maps to the first MIDI value and the high end to the "
        "second. Points outside it are silent unless --clip. classic defaults "
        "to -1,1, four-parameter to -2,2, and a custom map to -1,1."
    ),
)
@click.option(
    "--seed",
    default=0,
    show_default=True,
    type=int,
    help=(
        "Seed for u, including the angle chosen by a random start. One seed "
        "makes the MIDI file and playback share the same points."
    ),
)
@click.option(
    "-p",
    "--function-parameters",
    default="1.0",
    show_default=True,
    help=(
        "Comma-separated values for the parameter names, in alphabetical order. "
        "Startup prints those names in that order. classic needs one value, "
        "the angle a. four-parameter needs four, for example 1,1,1,1. A custom "
        "map with no parameters takes none; the default 1.0 is for classic."
    ),
)
@click.option(
    "-i",
    "--iterations-per-orbit",
    default=100,
    show_default=True,
    type=int,
    help=(
        "How many points to take from each orbit. Each point is one step of "
        "time, including a point that falls silent outside the window."
    ),
)
@click.option(
    "-m",
    "--midi-output-name",
    default="default",
    show_default=True,
    help=(
        "MIDI device to play through. 'default' is the first name from "
        "--list-midi-outputs. A missing device stops the run before any MIDI "
        "file is written. --visualize-only does not play."
    ),
)
@click.option(
    "--ticks-per-beat",
    default=960,
    show_default=True,
    type=int,
    help=(
        "MIDI ticks in one quarter note. Each step lasts this many ticks "
        "divided by how many notes fall in a beat, dropping a remainder. "
        "960 is a common DAW resolution."
    ),
)
@click.option(
    "--bpm",
    default=120,
    show_default=True,
    type=int,
    help="Tempo in quarter notes per minute.",
)
@click.option(
    "--notes-per-beat",
    default=4,
    show_default=True,
    type=int,
    help=(
        "How many orbit points fall in one quarter note. The default 4 places "
        "the steps on a sixteenth-note grid."
    ),
)
@click.option(
    "--x-midi-parameter-mappings",
    default="note",
    show_default=True,
    help=(
        "Comma-separated targets driven by x. note is the pitch. velocity is "
        "how hard the note is struck. A control is a name (pan, volume, "
        "knob-3) or a number (10, cc20). Each target gets the same scaled x. "
        "If y names the same target, y wins."
    ),
)
@click.option(
    "--y-midi-parameter-mappings",
    default="velocity,pan",
    show_default=True,
    help=(
        "Comma-separated targets driven by y. Same kinds of target as x: "
        "note, velocity, a controller name, or a controller number. If x "
        "and y name the same target, y wins."
    ),
)
@click.option(
    "--x-midi-value-range",
    default="0,127",
    show_default=True,
    help=(
        "Two integers from 0 to 127 for values taken from x. The low end of "
        "the source window maps to the first and the high end to the second, "
        "so 127,0 flips x."
    ),
)
@click.option(
    "--y-midi-value-range",
    default="0,127",
    show_default=True,
    help=(
        "Two integers from 0 to 127 for values taken from y. The low end of "
        "the source window maps to the first and the high end to the second, "
        "so 127,0 flips y."
    ),
)
@click.option(
    "-r",
    "--starting-radius",
    default=0.0,
    show_default=True,
    type=float,
    help=(
        "Radius r of the first orbit. diagonal starts at (r, r). random and "
        "sweep start on the circle of radius r. Orbits play while r is at "
        "most 1, so a start above 1 plays nothing."
    ),
)
@click.option(
    "-s",
    "--radial-step",
    default=0.01,
    show_default=True,
    type=float,
    help=(
        "Added to the radius after each orbit. Must be positive. From a start "
        "of 0, the default 0.01 plays about a hundred orbits. A large step "
        "plays only a few, because the radius stops after it passes 1."
    ),
)
@click.option(
    "-o",
    "--out",
    default="henon.mid",
    show_default=True,
    help=(
        "Path of the MIDI file. The file is one pass, written before playback "
        "starts. An empty path skips the file. Playback still needs a device "
        "unless --visualize-only is set."
    ),
)
@click.option(
    "--draw-ascii-art",
    is_flag=True,
    help=(
        "Draw each point in the terminal while playing. The picture uses the "
        "same window as the notes."
    ),
)
@click.option(
    "--sustain",
    is_flag=True,
    help="Hold the sustain pedal so notes can overlap.",
)
@click.option(
    "--clip",
    is_flag=True,
    help=(
        "Play a point that falls outside the source window by clamping it "
        "into the window. Otherwise that step is silent, and time still advances."
    ),
)
@click.option(
    "--continual-loop",
    is_flag=True,
    help=(
        "Play the orbits again from the first radius when the last one "
        "finishes. The MIDI file stays a single pass."
    ),
)
@click.option(
    "--visualize-only",
    is_flag=True,
    help=(
        "Draw the orbits in the terminal without a MIDI file or a MIDI device. "
        "An explicit --out or --midi-output-name is rejected."
    ),
)
@click.pass_context
def cli(
    context: click.Context,
    map_name: str,
    function_parameters: str,
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
    visualize_only: bool,
    x_prime: str | None,
    y_prime: str | None,
    source_range: str | None,
    start: str,
    seed: int,
) -> None:
    """Generate MIDI from iterated Henon mappings.

    A map sends the point (x, y) to the next point, and each point is one
    step of the piece. By default x chooses the note, and y chooses the
    velocity and the pan. Orbits are taken at successive radii, from
    --starting-radius by --radial-step, while the radius is at most 1.

    For the theory of the Henon map, what an orbit is, and how these
    options fit together, run:

    \b
        henon2midi --help-verbose
    """
    try:
        run = build_run(
            map_name=map_name,
            function_parameters=function_parameters,
            iterations_per_orbit=iterations_per_orbit,
            midi_output_name=midi_output_name,
            midi_output_was_set=_was_set_on_command_line(context, "midi_output_name"),
            ticks_per_beat=ticks_per_beat,
            bpm=bpm,
            notes_per_beat=notes_per_beat,
            x_midi_parameter_mappings=x_midi_parameter_mappings,
            y_midi_parameter_mappings=y_midi_parameter_mappings,
            x_midi_value_range=x_midi_value_range,
            y_midi_value_range=y_midi_value_range,
            starting_radius=starting_radius,
            radial_step=radial_step,
            out=out,
            out_was_set=_was_set_on_command_line(context, "out"),
            draw_ascii_art=draw_ascii_art,
            sustain=sustain,
            clip=clip,
            continual_loop=continual_loop,
            visualize_only=visualize_only,
            x_prime=x_prime,
            y_prime=y_prime,
            source_range=source_range,
            start=start,
            seed=seed,
            map_was_set=_was_set_on_command_line(context, "map_name"),
            parameters_were_set=_was_set_on_command_line(
                context, "function_parameters"
            ),
        )
        perform(run)
    except ValueError as error:
        raise click.UsageError(str(error)) from error
    except MidiOutputNotFound as error:
        raise click.ClickException(str(error)) from error


@dataclass(frozen=True)
class Run:
    performance: Performance
    output_path: str | None
    midi_port_name: str | None
    draw: bool


def build_run(
    map_name: str,
    function_parameters: str,
    iterations_per_orbit: int,
    midi_output_name: str,
    midi_output_was_set: bool,
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
    out_was_set: bool,
    draw_ascii_art: bool,
    sustain: bool,
    clip: bool,
    continual_loop: bool,
    visualize_only: bool,
    x_prime: str | None = None,
    y_prime: str | None = None,
    source_range: str | None = None,
    start: str = "diagonal",
    seed: int = 0,
    map_was_set: bool = False,
    parameters_were_set: bool = False,
) -> Run:
    if visualize_only and (out_was_set or midi_output_was_set):
        raise ValueError(
            "--visualize-only draws the orbits and cannot be combined "
            "with --out or --midi-output-name"
        )
    compiled = _compiled_iteration(
        map_name,
        map_was_set,
        x_prime,
        y_prime,
        start,
        source_range,
        function_parameters,
        parameters_were_set,
    )
    require_orbit_arguments(
        iterations_per_orbit, starting_radius, radial_step, MAX_ORBIT_RADIUS
    )
    performance = Performance(
        compiled,
        OrbitSchedule(
            iterations_per_orbit=iterations_per_orbit,
            starting_radius=starting_radius,
            radial_step=radial_step,
            seed=seed,
        ),
        timing=Timing(ticks_per_beat, bpm, notes_per_beat),
        mapping=_mapping(
            x_midi_parameter_mappings,
            y_midi_parameter_mappings,
            x_midi_value_range,
            y_midi_value_range,
            compiled.source_range,
            clip,
        ),
        sustain=sustain,
        loop=continual_loop,
    )
    return Run(
        performance=performance,
        output_path=None if visualize_only else (out or None),
        midi_port_name=None if visualize_only else midi_output_name,
        draw=visualize_only or draw_ascii_art,
    )


def _map_name_alongside_equations(
    map_name: str, x_prime: str | None, map_was_set: bool
) -> str | None:
    if x_prime is None or map_was_set:
        return map_name
    return None


def _compiled_iteration(
    map_name: str,
    map_was_set: bool,
    x_prime: str | None,
    y_prime: str | None,
    start: str,
    source_range: str | None,
    function_parameters: str,
    parameters_were_set: bool,
) -> BoundIteration:
    plan = plan_iteration(
        _map_name_alongside_equations(map_name, x_prime, map_was_set),
        x_prime,
        y_prime,
        start,
        None if source_range is None else parse_source_range(source_range),
    )
    if plan.parameter_count == 0 and not parameters_were_set:
        parameters: tuple[float, ...] = ()
    else:
        parameters = parse_parameters(function_parameters)
    return plan.bind(parameters)


def _mapping(
    x_midi_parameter_mappings: str,
    y_midi_parameter_mappings: str,
    x_midi_value_range: str,
    y_midi_value_range: str,
    source_range: tuple[float, float],
    clip: bool,
) -> Mapping:
    return Mapping(
        x_targets=parse_midi_targets(x_midi_parameter_mappings),
        y_targets=parse_midi_targets(y_midi_parameter_mappings),
        source_range_x=source_range,
        source_range_y=source_range,
        midi_range_x=parse_midi_range(x_midi_value_range, "x_midi_value_range"),
        midi_range_y=parse_midi_range(y_midi_value_range, "y_midi_value_range"),
        clamp=clip,
    )


def perform(run: Run) -> None:
    performance = run.performance
    port_name = _resolved_port_name(run)
    banner = f"henon2midi v{package_version()}\n\n"
    options = format_options(run, port_name)
    click.echo(banner)
    click.echo(options)
    if run.output_path is not None:
        write_midi_file(
            run.output_path,
            events_in_one_pass(performance),
            performance.timing.ticks_per_beat,
            performance.timing.bpm,
        )
    try:
        if run.draw:
            _draw(performance, port_name)
        else:
            _play_or_visualize(performance, port_name, None, None)
    except KeyboardInterrupt:
        return


def format_options(run: Run, port_name: str | None) -> str:
    performance = run.performance
    compiled = performance.iteration
    names = ", ".join(compiled.parameter_names) if compiled.parameter_names else "none"
    x_prime, y_prime = compiled.equations
    lines = [
        "Running with the following parameters. "
        "Use --help for every option, or --help-verbose for the theory.",
        f"\tmap: {compiled.name}",
        f"\tx': {x_prime}",
        f"\ty': {y_prime}",
        f"\tstart: {compiled.start}",
        f"\tparameters: {compiled.parameters.values}",
        f"\tparameter names: {names}",
        f"\tsource range: {compiled.source_range}",
        f"\tseed: {performance.schedule.seed}",
        f"\titerations per orbit: {performance.schedule.iterations_per_orbit}",
        f"\tmidi output name: {port_name or 'none'}",
        f"\tticks per beat: {performance.timing.ticks_per_beat}",
        f"\tbpm: {performance.timing.bpm}",
        f"\tnotes per beat: {performance.timing.notes_per_beat}",
        f"\tx midi parameter mappings: {describe_midi_targets(performance.mapping.x_targets)}",
        f"\ty midi parameter mappings: {describe_midi_targets(performance.mapping.y_targets)}",
        f"\tx midi value range: {performance.mapping.midi_range_x}",
        f"\ty midi value range: {performance.mapping.midi_range_y}",
        f"\tstarting radius: {performance.schedule.starting_radius}",
        f"\tradial step: {performance.schedule.radial_step}",
        f"\tout: {run.output_path or 'none'}",
        f"\tdraw ascii art: {run.draw}",
        f"\tsustain: {performance.sustain}",
        f"\tclip: {performance.mapping.clamp}",
        f"\tcontinual loop: {performance.loop}",
    ]
    return "\n".join(lines) + "\n\n"


def status_lines(sample: Sample) -> tuple[str, str, str]:
    point = sample.point
    return (
        f"Current iteration: {sample.iteration}",
        f"Current orbit: {sample.orbit}",
        f"Current data point: ({point.x}, {point.y})",
    )


def format_frame(banner: str, options: str, sample: Sample, art: str) -> str:
    state = "\n".join(status_lines(sample)) + "\n\n"
    return banner + options + state + art


def _was_set_on_command_line(context: click.Context, name: str) -> bool:
    source = context.get_parameter_source(name)
    return source is not None and source.name == "COMMANDLINE"


def _resolved_port_name(run: Run) -> str | None:
    if run.midi_port_name is None:
        return None
    return resolve_midi_output_name(run.midi_port_name)


def _draw(performance: Performance, port_name: str | None) -> None:
    sys.stdout.flush()
    columns, rows = read_terminal_size()
    canvas = AsciiCanvas(*grid_size(columns, rows))
    display = TerminalDisplay(
        canvas, sys.stdout, status_lines, terminal_size=read_terminal_size
    )
    with display:
        _play_or_visualize(performance, port_name, canvas, display.show)


def _play_or_visualize(
    performance: Performance,
    port_name: str | None,
    canvas: AsciiCanvas | None,
    render: FrameRenderer | None,
) -> None:
    if port_name is not None:
        with MidiPort(
            port_name, performance.timing.ticks_per_beat, performance.timing.bpm
        ) as port:
            play(performance, port, canvas, render)
        return
    if canvas is not None:
        visualize(performance, canvas, render)
