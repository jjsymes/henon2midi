from pathlib import Path

import pytest
from click.testing import CliRunner
from mido import MidiFile

from henon2midi.cli import Run, build_run, cli, format_frame, format_options, perform
from henon2midi.domain.formula import FUNCTIONS
from henon2midi.domain.maps import Point, Sample, StartContext
from henon2midi.domain.presets import CLASSIC
from henon2midi.domain.targets import ControlTarget, NoteField
from henon2midi.output.midi_port import MidiOutputNotFound
from henon2midi.run import samples_for

runner = CliRunner()


def _do_not_open_a_port(*_args, **_kwargs):
    raise AssertionError("opened a MIDI port")


def _missing_port(_name):
    raise MidiOutputNotFound("No MIDI output devices found")


def arguments(**overrides):
    values = dict(
        map_name="classic",
        function_parameters="1.0",
        iterations_per_orbit=100,
        midi_output_name="default",
        midi_output_was_set=False,
        ticks_per_beat=960,
        bpm=120,
        notes_per_beat=4,
        x_midi_parameter_mappings="note",
        y_midi_parameter_mappings="velocity,pan",
        x_midi_value_range="0,127",
        y_midi_value_range="0,127",
        starting_radius=0.0,
        radial_step=0.01,
        out="henon.mid",
        out_was_set=False,
        draw_ascii_art=False,
        sustain=False,
        clip=False,
        continual_loop=False,
        visualize_only=False,
        x_prime=None,
        y_prime=None,
        start="diagonal",
        seed=0,
        map_was_set=False,
        parameters_were_set=False,
        source_range=None,
    )
    values.update(overrides)
    return values


def test_default_config_matches_the_historical_music_settings():
    run = build_run(**arguments())
    performance = run.performance
    assert performance.iteration.name == "classic"
    assert performance.parameters.values == (1.0,)
    assert performance.schedule.iterations_per_orbit == 100
    assert performance.schedule.starting_radius == 0.0
    assert performance.schedule.radial_step == 0.01
    assert performance.timing.note_duration_ticks == 240
    assert performance.mapping.x_targets == (NoteField.NOTE,)
    assert performance.mapping.y_targets == (NoteField.VELOCITY, ControlTarget(10))
    assert performance.mapping.clamp is False
    assert run.output_path == "henon.mid"
    assert run.midi_port_name == "default"
    assert run.draw is False
    assert performance.loop is False
    assert performance.sustain is False
    assert performance.iteration.start == "diagonal"
    assert performance.schedule.seed == 0
    assert performance.iteration.equations == (CLASSIC.x_prime, CLASSIC.y_prime)
    assert performance.iteration.parameter_names == ("a",)
    assert performance.iteration.source_range == (-1.0, 1.0)
    assert performance.mapping.source_range_x == (-1.0, 1.0)
    assert performance.mapping.source_range_y == (-1.0, 1.0)


def test_visualize_only_draws_and_drops_midi_destinations():
    run = build_run(**arguments(visualize_only=True, draw_ascii_art=False))
    assert run.draw is True
    assert run.output_path is None
    assert run.midi_port_name is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"visualize_only": True, "out_was_set": True},
        {"visualize_only": True, "midi_output_was_set": True},
    ],
)
def test_visualize_only_rejects_an_explicit_midi_destination(overrides):
    with pytest.raises(ValueError, match="cannot be combined"):
        build_run(**arguments(**overrides))


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"function_parameters": "1,2"}, "classic expects 1"),
        ({"function_parameters": ""}, "must not be empty"),
        ({"function_parameters": "nope"}, "comma-separated numbers"),
        ({"map_name": "missing"}, "Unknown map"),
        ({"x_midi_value_range": "0"}, "comma separated list of 2 values"),
        ({"y_midi_value_range": "a,b"}, "comma separated list of 2 values"),
        ({"x_midi_value_range": "0,200"}, "between 0 and 127"),
        ({"x_midi_value_range": "0,1,2"}, "comma separated list of 2 values"),
        ({"x_midi_parameter_mappings": "not-a-control"}, "Unknown MIDI target"),
        ({"x_midi_parameter_mappings": "cc200"}, "outside 0 to 127"),
        ({"x_midi_parameter_mappings": "200"}, "outside 0 to 127"),
        ({"y_midi_parameter_mappings": ""}, "must not be empty"),
        ({"radial_step": 0}, "radial step"),
        ({"iterations_per_orbit": 0}, "at least 1"),
        ({"notes_per_beat": 0}, "notes per beat"),
        ({"source_range": "0"}, "comma separated list of 2 values"),
        ({"source_range": "a,b"}, "comma separated list of 2 values"),
        ({"source_range": "1,1"}, "two different finite numbers"),
        ({"source_range": "inf,2"}, "two different finite numbers"),
        (
            {"map_name": "four-parameter", "function_parameters": "1,1,1"},
            "expects 4",
        ),
    ],
)
def test_build_run_rejects_bad_input(overrides, message):
    with pytest.raises(ValueError, match=message):
        build_run(**arguments(**overrides))


def test_build_run_accepts_the_four_parameter_map_and_cleans_targets():
    run = build_run(
        **arguments(
            map_name="four-parameter",
            function_parameters="1, 2, 3, 4",
            x_midi_parameter_mappings="note, note, pan",
            y_midi_parameter_mappings=" velocity ",
            x_midi_value_range="10,20",
            out="",
            clip=True,
            sustain=True,
            continual_loop=True,
            draw_ascii_art=True,
        )
    )
    performance = run.performance
    assert performance.parameters.values == (1.0, 2.0, 3.0, 4.0)
    assert performance.mapping.source_range_x == (-2.0, 2.0)
    assert performance.mapping.source_range_y == (-2.0, 2.0)
    assert performance.mapping.x_targets == (NoteField.NOTE, ControlTarget(10))
    assert performance.mapping.y_targets == (NoteField.VELOCITY,)
    assert performance.mapping.midi_range_x == (10, 20)
    assert performance.mapping.clamp is True
    assert performance.sustain is True
    assert performance.loop is True
    assert run.draw is True
    assert run.output_path is None


def test_controller_spellings_collapse_to_one_name_in_the_listing():
    run = build_run(
        **arguments(
            x_midi_parameter_mappings="note, volume, CC20, knob-3",
            y_midi_parameter_mappings="cc7, expression, 47",
        )
    )
    assert run.performance.mapping.x_targets == (
        NoteField.NOTE,
        ControlTarget(7),
        ControlTarget(20),
    )
    assert run.performance.mapping.y_targets == (
        ControlTarget(7),
        ControlTarget(11),
        ControlTarget(47),
    )
    listing = format_options(run, None)
    assert "x midi parameter mappings: note, volume, knob-3" in listing
    assert "y midi parameter mappings: volume, expression, cc47" in listing


def test_formatters_include_the_state_a_performer_needs():
    run = build_run(**arguments(visualize_only=True))
    options = format_options(run, None)
    assert "map: classic" in options
    assert "start: diagonal" in options
    assert "parameter names: a" in options
    assert "parameters: (1.0,)" in options
    assert "midi output name: none" in options
    assert "out: none" in options
    assert "draw ascii art: True" in options
    assert "--help-verbose" in options
    frame = format_frame(
        "banner\n", options, Sample(Point(0.5, -0.25), 3, 2, 0.2, False), "art"
    )
    assert frame.startswith("banner\n")
    assert "Current iteration: 3" in frame
    assert "Current orbit: 2" in frame
    assert "Current data point: (0.5, -0.25)" in frame
    assert frame.endswith("art")


def _refuse_to_touch_midi(monkeypatch):
    def explode(*_args, **_kwargs):
        raise AssertionError("MIDI devices were queried")

    monkeypatch.setattr("henon2midi.output.midi_port.get_output_names", explode)
    monkeypatch.setattr("henon2midi.output.midi_port.open_output", explode)


def test_help_lists_the_new_modes_without_querying_devices(monkeypatch):
    _refuse_to_touch_midi(monkeypatch)
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "--visualize-only" in result.output
    assert "--list-midi-outputs" in result.output
    assert "--map" in result.output
    assert "--source-range" in result.output
    assert "--x-prime" in result.output
    assert "--y-prime" in result.output
    assert "--start" in result.output
    assert "--seed" in result.output
    assert "1.0" in result.output
    assert "knob-3" in result.output
    assert "cc20" in result.output
    description, options = result.output.split("Options:", maxsplit=1)
    assert "henon2midi --help-verbose" in description
    assert "--help-verbose" in options
    assert "preserves area" in result.output
    assert "sixteenth-note" in result.output
    assert "x*cos(a)" not in result.output


def test_verbose_help_explains_the_map_then_lists_the_options(monkeypatch):
    _refuse_to_touch_midi(monkeypatch)
    result = runner.invoke(cli, ["--help-verbose"])
    assert result.exit_code == 0, result.output
    assert "Running with the following" not in result.output
    assert "area-preserving" in result.output
    assert "Hénon" in result.output
    assert "1969" in result.output
    assert "1976" in result.output
    assert "x*cos(a) - (y - x**2)*sin(a)" in result.output
    assert "1 - a*x**2 + y" in result.output
    assert "sin(a*y) - cos(b*x)" in result.output
    assert "--x-prime='1 - a*x**2 + y'" in result.output
    assert "-p 1.4,0.3" in result.output
    assert "strange attractor" in result.output
    for name in FUNCTIONS:
        assert name in result.output
    essay, reference = result.output.split("Usage:", maxsplit=1)
    assert "x*cos(a)" in essay
    assert "--help-verbose" in reference
    assert "--map" in reference


def test_verbose_help_exits_before_the_other_options_are_checked(monkeypatch):
    _refuse_to_touch_midi(monkeypatch)
    result = runner.invoke(cli, ["--map", "not-a-map", "--help-verbose"])
    assert result.exit_code == 0, result.output
    assert "area-preserving" in result.output


def test_version_prints_the_package_name():
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "henon2midi" in result.output


def test_list_midi_outputs(monkeypatch):
    monkeypatch.setattr(
        "henon2midi.cli.available_midi_output_names",
        lambda: ["Bus 1", "IAC Driver"],
    )
    result = runner.invoke(cli, ["--list-midi-outputs"])
    assert result.exit_code == 0
    assert "Bus 1" in result.output
    assert "IAC Driver" in result.output


def test_list_midi_outputs_fails_when_there_are_none(monkeypatch):
    monkeypatch.setattr("henon2midi.cli.available_midi_output_names", lambda: [])
    result = runner.invoke(cli, ["--list-midi-outputs"])
    assert result.exit_code != 0
    assert "No MIDI output devices found" in result.output


def test_visualize_only_prints_the_listing_once(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        cli,
        ["--visualize-only", "-i", "5", "-r", "0", "-s", "1"],
    )
    assert result.exit_code == 0, result.output
    assert result.output.count("map: classic") == 1
    assert "Current iteration: 1" in result.output


def test_visualize_only_draws_one_pass_and_writes_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("henon2midi.output.midi_port.open_output", _do_not_open_a_port)
    result = runner.invoke(
        cli,
        ["--visualize-only", "-i", "1", "-r", "1", "-s", "1", "--clip", "--sustain"],
    )
    assert result.exit_code == 0, result.output
    assert "Current iteration: 1" in result.output
    assert "\033[?1049h" not in result.output
    assert "clip: True" in result.output
    assert "sustain: True" in result.output
    assert "map: classic" in result.output
    assert not Path("henon.mid").exists()


def test_visualize_only_rejects_flags_that_ask_for_midi(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    written = tmp_path / "song.mid"
    result = runner.invoke(cli, ["--visualize-only", "--out", str(written)])
    assert result.exit_code != 0
    assert "cannot be combined" in result.output
    assert not written.exists()

    result = runner.invoke(cli, ["--visualize-only", "--midi-output-name", "Bus 1"])
    assert result.exit_code != 0
    assert "cannot be combined" in result.output


def test_cli_rejects_the_old_four_number_default_on_the_classic_map():
    result = runner.invoke(cli, ["--visualize-only", "-p", "1,1,1,1"])
    assert result.exit_code != 0
    assert "expects 1" in result.output


def test_four_parameter_map_can_be_visualized(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        cli,
        [
            "--map",
            "four-parameter",
            "-p",
            "1,1,1,1",
            "--visualize-only",
            "-i",
            "1",
            "-r",
            "1",
            "-s",
            "1",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "map: four-parameter" in result.output
    assert "parameters: (1.0, 1.0, 1.0, 1.0)" in result.output


def test_unknown_map_is_rejected_by_the_command():
    result = runner.invoke(cli, ["--map", "logistic", "--visualize-only"])
    assert result.exit_code != 0


def test_missing_device_fails_before_a_file_is_written(tmp_path, monkeypatch):
    monkeypatch.setattr("henon2midi.output.midi_port.get_output_names", lambda: [])
    monkeypatch.setattr("henon2midi.output.midi_port.open_output", _do_not_open_a_port)
    destination = tmp_path / "out.mid"
    result = runner.invoke(
        cli,
        ["-i", "1", "-r", "1", "-s", "1", "--out", str(destination)],
    )
    assert result.exit_code != 0
    assert "No MIDI output devices found" in result.output
    assert not destination.exists()
    assert result.exception is None or not isinstance(result.exception, AssertionError)


def test_perform_writes_a_file_without_opening_a_port(
    tiny_config, tmp_path, monkeypatch
):
    monkeypatch.setattr("henon2midi.output.midi_port.open_output", _do_not_open_a_port)
    destination = tmp_path / "out.mid"
    perform(Run(tiny_config, str(destination), None, False))
    loaded = MidiFile(destination)
    assert loaded.tracks[0][0].type == "set_tempo"
    assert any(message.type == "note_on" for message in loaded.tracks[0])


def test_perform_plays_one_pass_and_closes_after_interrupt(tiny_config, monkeypatch):
    class FakePort:
        def __init__(self, name, ticks_per_beat, bpm):
            self.name = name
            self.closed = False
            FakePort.instance = self

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            self.closed = True
            return False

        def send(self, _events):
            raise KeyboardInterrupt

    monkeypatch.setattr("henon2midi.cli.MidiPort", FakePort)
    monkeypatch.setattr("henon2midi.cli.resolve_midi_output_name", lambda name: name)
    perform(Run(tiny_config, None, "Bus 1", False))
    assert FakePort.instance.name == "Bus 1"
    assert FakePort.instance.closed


def test_drawing_while_playing_walks_the_orbits_once(tiny_config, monkeypatch):
    sent = []

    class FakePort:
        def __init__(self, _name, _ticks_per_beat, _bpm):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def send(self, events):
            sent.append(events)

    def visualize_should_not_run(*_args, **_kwargs):
        raise AssertionError("playback also walked the orbits with no MIDI")

    monkeypatch.setattr("henon2midi.cli.MidiPort", FakePort)
    monkeypatch.setattr("henon2midi.cli.resolve_midi_output_name", lambda name: name)
    monkeypatch.setattr("henon2midi.cli.visualize", visualize_should_not_run)
    perform(Run(tiny_config, None, "Bus 1", True))
    assert len(sent) == len(list(samples_for(tiny_config)))


def test_perform_stops_when_visualization_is_interrupted(tiny_config, monkeypatch):
    def interrupt(*_args, **_kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr("henon2midi.cli.visualize", interrupt)
    perform(Run(tiny_config, None, None, True))


def test_custom_equations_bind_names_in_alphabetical_order():
    performance = build_run(
        **arguments(
            x_prime="b",
            y_prime="a",
            function_parameters="1, 2",
            parameters_were_set=True,
            start="a; b",
        )
    ).performance
    assert performance.iteration.name == "custom"
    assert performance.iteration.parameter_names == ("a", "b")
    assert performance.iteration.step(Point(0.0, 0.0)) == Point(2.0, 1.0)
    origin = performance.iteration.start_at(StartContext(4.0, 0, 0.0))
    assert origin == Point(1.0, 2.0)
    assert performance.mapping.source_range_x == (-1.0, 1.0)


def test_a_parameterless_equation_ignores_the_default_parameter():
    performance = build_run(**arguments(x_prime="y", y_prime="-x")).performance
    assert performance.parameters.values == ()
    assert performance.iteration.step(Point(1.0, 0.25)) == Point(0.25, -1.0)


def test_source_range_overrides_the_preset_window():
    run = build_run(**arguments(source_range="-2, 2"))
    performance = run.performance
    assert performance.iteration.source_range == (-2.0, 2.0)
    assert performance.mapping.source_range_x == (-2.0, 2.0)
    assert performance.mapping.source_range_y == (-2.0, 2.0)
    assert "source range: (-2.0, 2.0)" in format_options(run, None)


def test_a_start_expression_cannot_invent_a_parameter():
    with pytest.raises(ValueError, match="not a parameter"):
        build_run(
            **arguments(
                start="S; 0",
                function_parameters="9, 0.3",
                parameters_were_set=True,
            )
        )


def test_build_run_rejects_half_an_equation_and_an_explicit_map():
    with pytest.raises(ValueError, match="both an x equation and a y equation"):
        build_run(**arguments(x_prime="y"))
    with pytest.raises(ValueError, match="replace the selected map"):
        build_run(**arguments(x_prime="y", y_prime="-x", map_was_set=True))
    with pytest.raises(ValueError, match="expects 0"):
        build_run(
            **arguments(
                x_prime="y",
                y_prime="-x",
                function_parameters="1",
                parameters_were_set=True,
            )
        )


def test_the_configured_seed_is_what_both_passes_draw():
    overrides = dict(
        start="random",
        iterations_per_orbit=1,
        starting_radius=0.5,
        radial_step=0.5,
        visualize_only=True,
    )
    performance = build_run(**arguments(seed=2, **overrides)).performance
    first = [sample.point for sample in samples_for(performance)]
    assert first == [sample.point for sample in samples_for(performance)]
    other = build_run(**arguments(seed=3, **overrides)).performance
    assert [sample.point for sample in samples_for(other)] != first


def test_custom_equations_and_a_swept_start_can_be_visualized(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("henon2midi.output.midi_port.open_output", _do_not_open_a_port)
    result = runner.invoke(
        cli,
        [
            "--visualize-only",
            "--x-prime=y",
            "--y-prime=-x",
            "--start",
            "sweep",
            "-i",
            "1",
            "-r",
            "1",
            "-s",
            "1",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "map: custom" in result.output
    assert "x': y" in result.output
    assert "y': -x" in result.output
    assert "start: sweep" in result.output
    assert "Current data point: (0.0, -1.0)" in result.output
    assert not Path("henon.mid").exists()


def test_the_attractor_example_from_verbose_help_can_be_drawn(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("henon2midi.output.midi_port.open_output", _do_not_open_a_port)
    result = runner.invoke(
        cli,
        [
            "--visualize-only",
            "--x-prime=1 - a*x**2 + y",
            "--y-prime=b*x",
            "-p",
            "1.4,0.3",
            "--source-range=-1.5,1.5",
            "-i",
            "1",
            "-r",
            "0.1",
            "-s",
            "1",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "map: custom" in result.output
    assert "parameter names: a, b" in result.output
    assert "parameters: (1.4, 0.3)" in result.output
    assert "source range: (-1.5, 1.5)" in result.output
    assert not Path("henon.mid").exists()


def test_the_command_rejects_a_mixed_or_broken_specification():
    missing_half = runner.invoke(cli, ["--visualize-only", "--x-prime", "y"])
    assert missing_half.exit_code != 0
    assert "both an x equation" in missing_half.output

    explicit_map = runner.invoke(
        cli,
        ["--visualize-only", "--map", "classic", "--x-prime", "y", "--y-prime", "x"],
    )
    assert explicit_map.exit_code != 0
    assert "replace the selected map" in explicit_map.output

    explicit_parameter = runner.invoke(
        cli,
        ["--visualize-only", "--x-prime=y", "--y-prime=-x", "-p", "1"],
    )
    assert explicit_parameter.exit_code != 0
    assert "expects 0" in explicit_parameter.output

    broken = runner.invoke(
        cli, ["--visualize-only", "--x-prime", "sin(", "--y-prime", "y"]
    )
    assert broken.exit_code != 0
    assert "x'" in broken.output


def test_perform_reports_a_missing_port(tiny_config, monkeypatch):
    monkeypatch.setattr(
        "henon2midi.cli.resolve_midi_output_name",
        _missing_port,
    )
    with pytest.raises(MidiOutputNotFound):
        perform(Run(tiny_config, None, "default", False))
