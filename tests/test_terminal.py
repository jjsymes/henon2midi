import signal
import sys
from io import StringIO

import pytest

from henon2midi.domain.maps import Point, Sample
from henon2midi.output.canvas import AsciiCanvas
from henon2midi.output.terminal import TerminalDisplay, grid_size


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def _sample(iteration: int) -> Sample:
    return Sample(Point(0.25, -0.5), iteration, 2, 0.1, False)


def _display(canvas, stream, **overrides):
    clock = overrides.pop("clock", Clock())
    display = TerminalDisplay(
        canvas,
        stream,
        status_for=overrides.pop("status_for", lambda _sample: ("status",)),
        clock=clock,
        terminal_size=overrides.pop("terminal_size", lambda: (20, 10)),
        frame_interval=overrides.pop("frame_interval", 1.0),
        is_tty=overrides.pop("is_tty", True),
        wait_to_close=overrides.pop("wait_to_close", lambda: None),
    )
    return display, clock


def test_grid_keeps_three_rows_for_status():
    assert grid_size(80, 24) == (80, 21)
    assert grid_size(40, 2) == (40, 1)


def test_a_point_is_written_at_its_cell_without_erasing_again():
    stream = StringIO()
    canvas = AsciiCanvas(20, 7, color_order=["white", "red"])
    canvas.set_color("red")
    canvas.draw_point(1, 0, "█")
    display, _clock = _display(canvas, stream)

    with display:
        entered = len(stream.getvalue())
        display.show(_sample(4))
        painted = stream.getvalue()[entered:]

    assert "\033[2J" not in painted
    assert "\033[1;2H\033[0;31m█" in painted


def test_status_lines_sit_on_the_bottom_rows():
    stream = StringIO()
    canvas = AsciiCanvas(20, 7, color_order=["white"])
    display, _clock = _display(
        canvas,
        stream,
        status_for=lambda _sample: ("one", "two", "three"),
    )

    with display:
        display.show(_sample(1))

    output = stream.getvalue()
    assert "\033[8;1H" in output
    assert "\033[9;1H" in output
    assert "\033[10;1H" in output
    assert "one" in output and "two" in output and "three" in output


def test_points_inside_one_frame_are_held_and_not_rewritten():
    clock = Clock()
    stream = StringIO()
    canvas = AsciiCanvas(20, 7, color_order=["white"])
    display, _clock = _display(canvas, stream, clock=clock, frame_interval=1.0)

    with display:
        entered = len(stream.getvalue())
        canvas.draw_point(0, 0, "A")
        display.show(_sample(1))
        after_first = stream.getvalue()
        canvas.draw_point(1, 0, "B")
        display.show(_sample(2))
        assert stream.getvalue() == after_first
        clock.now = 1
        display.show(_sample(3))
        after_second = stream.getvalue()

    first = after_first[entered:]
    split_at = len(after_first)
    second = after_second[split_at:]
    assert "A" in first
    assert "B" not in first
    assert "\033[2J" not in first
    assert "B" in second
    assert "A" not in second
    assert "\033[2J" not in second


def test_clearing_the_grid_erases_old_points():
    clock = Clock()
    stream = StringIO()
    canvas = AsciiCanvas(20, 7, color_order=["white"])
    display, _clock = _display(canvas, stream, clock=clock, frame_interval=1.0)

    with display:
        canvas.draw_point(0, 0, "A")
        display.show(_sample(1))
        clock.now = 1
        before_clear = len(stream.getvalue())
        canvas.clear()
        canvas.draw_point(1, 0, "B")
        display.show(_sample(2))
        painted = stream.getvalue()[before_clear:]

    assert "\033[2J" in painted
    assert "A" not in painted
    assert "B" in painted


def test_a_point_past_the_terminal_is_not_written():
    stream = StringIO()
    canvas = AsciiCanvas(20, 7, color_order=["white"])
    canvas.draw_point(6, 0, "X")
    canvas.draw_point(1, 0, "Y")
    display, _clock = _display(canvas, stream, terminal_size=lambda: (4, 10))

    with display:
        display.show(_sample(1))

    output = stream.getvalue()
    assert "X" not in output
    assert "Y" in output


def test_a_resize_redraws_points_still_inside_the_terminal():
    clock = Clock()
    stream = StringIO()
    size = {"columns": 20, "rows": 10}
    canvas = AsciiCanvas(20, 7, color_order=["white"])
    display, _clock = _display(
        canvas,
        stream,
        clock=clock,
        terminal_size=lambda: (size["columns"], size["rows"]),
    )

    with display:
        canvas.draw_point(0, 0, "A")
        canvas.draw_point(8, 0, "B")
        display.show(_sample(1))
        clock.now = 1
        size["columns"] = 4
        handler = signal.getsignal(signal.SIGWINCH)
        assert callable(handler)
        handler(signal.SIGWINCH, None)
        display.show(_sample(2))

    output = stream.getvalue()
    assert output.count("A") == 2
    assert output.count("B") == 1


def test_status_is_clipped_to_the_terminal_width():
    stream = StringIO()
    canvas = AsciiCanvas(4, 1, color_order=["white"])
    display, _clock = _display(
        canvas,
        stream,
        terminal_size=lambda: (5, 6),
        status_for=lambda _sample: ("abcdefghij",),
    )

    with display:
        display.show(_sample(1))

    output = stream.getvalue()
    assert "abcde" in output
    assert "abcdef" not in output


def test_a_tty_holds_the_picture_until_enter_and_then_restores_the_terminal():
    waited = []
    stream = StringIO()
    canvas = AsciiCanvas(4, 1, color_order=["white"])
    display, _clock = _display(
        canvas,
        stream,
        terminal_size=lambda: (40, 10),
        wait_to_close=lambda: waited.append(True),
    )

    with display:
        pass

    output = stream.getvalue()
    assert "\033[?1049h" in output
    assert "\033[?25l" in output
    assert "\033[?7l" in output
    assert "Press Enter to close." in output
    assert waited == [True]
    assert output.index("Press Enter to close.") < output.index("\033[?1049l")
    assert "\033[?25h" in output
    assert "\033[?7h" in output


def test_an_interrupt_restores_the_terminal_without_waiting():
    waited = []
    stream = StringIO()
    canvas = AsciiCanvas(4, 1, color_order=["white"])
    display, _clock = _display(
        canvas, stream, wait_to_close=lambda: waited.append(True)
    )

    with pytest.raises(KeyboardInterrupt):
        with display:
            raise KeyboardInterrupt

    output = stream.getvalue()
    assert waited == []
    assert "Press Enter to close." not in output
    assert "\033[?25h" in output
    assert "\033[?1049l" in output


def test_a_finished_tty_reads_enter_from_stdin(monkeypatch):
    monkeypatch.setattr(sys, "stdin", StringIO("\n"))
    stream = StringIO()
    display = TerminalDisplay(
        AsciiCanvas(4, 1, color_order=["white"]),
        stream,
        status_for=lambda _sample: ("status",),
        clock=lambda: 0.0,
        terminal_size=lambda: (40, 8),
        is_tty=True,
    )

    with display:
        pass

    assert "Press Enter to close." in stream.getvalue()


def test_a_pipe_prints_status_text_and_holds_it_to_the_frame_clock():
    clock = Clock()
    stream = StringIO()
    canvas = AsciiCanvas(4, 2, color_order=["white"])
    display, _clock = _display(
        canvas,
        stream,
        clock=clock,
        frame_interval=1.0,
        is_tty=False,
        status_for=lambda sample: (
            f"Current iteration: {sample.iteration}",
            f"Current data point: ({sample.point.x}, {sample.point.y})",
        ),
    )

    with display:
        canvas.draw_point(0, 0, "█")
        display.show(_sample(1))
        after_first = stream.getvalue()
        display.show(_sample(2))
        assert stream.getvalue() == after_first

    output = stream.getvalue()
    assert "\033[" not in output
    assert "Current iteration: 1" in output
    assert "Current iteration: 2" in output
    assert "Current data point: (0.25, -0.5)" in output
    assert "█" not in output
