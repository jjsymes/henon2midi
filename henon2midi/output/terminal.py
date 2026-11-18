import shutil
import signal
import sys
from collections.abc import Callable, Sequence
from time import monotonic
from types import FrameType
from typing import Any, TextIO

from henon2midi.domain.maps import Sample
from henon2midi.output.canvas import AsciiCanvas, CanvasChanges

STATUS_ROWS = 3
FRAME_INTERVAL_SECONDS = 1 / 30

ENTER_ALTERNATE_SCREEN = "\033[?1049h"
LEAVE_ALTERNATE_SCREEN = "\033[?1049l"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"
DISABLE_LINE_WRAP = "\033[?7l"
ENABLE_LINE_WRAP = "\033[?7h"
CLEAR_SCREEN = "\033[2J"
CURSOR_HOME = "\033[H"
CLEAR_TO_END_OF_LINE = "\033[K"
CLOSE_PROMPT = "Press Enter to close."

StatusLines = Callable[[Sample], Sequence[str]]
TerminalSize = Callable[[], tuple[int, int]]
_ResizeHandler = Callable[[int, FrameType | None], Any] | int | None


def grid_size(columns: int, rows: int) -> tuple[int, int]:
    return max(columns, 1), max(rows - STATUS_ROWS, 1)


class TerminalDisplay:
    def __init__(
        self,
        canvas: AsciiCanvas,
        stream: TextIO,
        status_for: StatusLines,
        clock: Callable[[], float] | None = None,
        terminal_size: TerminalSize | None = None,
        frame_interval: float = FRAME_INTERVAL_SECONDS,
        is_tty: bool | None = None,
        wait_to_close: Callable[[], None] | None = None,
    ) -> None:
        self._canvas = canvas
        self._stream = stream
        self._status_for = status_for
        self._clock = monotonic if clock is None else clock
        self._terminal_size = (
            read_terminal_size if terminal_size is None else terminal_size
        )
        self._frame_interval = frame_interval
        self._is_tty = _stream_is_tty(stream) if is_tty is None else is_tty
        self._wait_to_close = _read_enter if wait_to_close is None else wait_to_close
        self._last_flush: float | None = None
        self._latest: Sample | None = None
        self._status_pending = False
        self._resized = False
        self._closed = False
        self._listening_for_resize = False
        self._previous_resize_handler: _ResizeHandler = None

    def __enter__(self) -> "TerminalDisplay":
        if self._is_tty:
            self._open_screen()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        try:
            self.flush()
            if self._is_tty and exc_type is None:
                self._ask_to_close()
                self._wait_to_close()
        finally:
            self._restore_terminal()

    def show(self, sample: Sample) -> None:
        self._latest = sample
        self._status_pending = True
        if self._frame_is_due():
            self.flush()

    def flush(self) -> None:
        changes = self._canvas.consume_changes()
        redraw = self._resized or changes.cleared
        if not _has_work(changes, redraw, self._status_pending):
            return
        self._resized = False
        if self._is_tty:
            self._paint_screen(changes, redraw)
        elif self._status_pending and self._latest is not None:
            self._write_plain_status(self._latest)
        self._status_pending = False
        self._stream.flush()
        self._last_flush = self._clock()

    def _open_screen(self) -> None:
        self._write(
            ENTER_ALTERNATE_SCREEN
            + HIDE_CURSOR
            + DISABLE_LINE_WRAP
            + CLEAR_SCREEN
            + CURSOR_HOME
        )
        self._stream.flush()
        self._listen_for_resize()

    def _frame_is_due(self) -> bool:
        if self._last_flush is None:
            return True
        return self._clock() - self._last_flush >= self._frame_interval

    def _paint_screen(self, changes: CanvasChanges, redraw: bool) -> None:
        if redraw:
            self._write(CLEAR_SCREEN + CURSOR_HOME)
            self._paint_cells(self._canvas.painted_cells())
        elif changes.cells:
            self._paint_cells(changes.cells)
        if self._latest is not None and (self._status_pending or redraw):
            self._paint_status(self._latest)

    def _paint_cells(self, cells: Sequence[tuple[int, int, str, str]]) -> None:
        columns, grid_rows = self._grid_viewport()
        pieces = [
            _colored_cell(x, y, character, color)
            for x, y, character, color in cells
            if x < columns and y < grid_rows
        ]
        self._write("".join(pieces))

    def _paint_status(self, sample: Sample) -> None:
        columns, rows = self._terminal_size()
        lines = _visible_lines(self._status_for(sample), columns, rows)
        if not lines:
            return
        first_row = rows - len(lines) + 1
        self._write(
            "".join(
                _status_line(first_row + index, line)
                for index, line in enumerate(lines)
            )
        )

    def _write_plain_status(self, sample: Sample) -> None:
        for line in self._status_for(sample):
            self._write(f"{line}\n")

    def _grid_viewport(self) -> tuple[int, int]:
        columns, rows = self._terminal_size()
        return columns, max(rows - STATUS_ROWS, 0)

    def _ask_to_close(self) -> None:
        columns, rows = self._terminal_size()
        self._write(_status_line(max(rows, 1), CLOSE_PROMPT[:columns]) + SHOW_CURSOR)
        self._stream.flush()

    def _listen_for_resize(self) -> None:
        if not hasattr(signal, "SIGWINCH"):
            return
        self._previous_resize_handler = signal.signal(signal.SIGWINCH, self._on_resize)
        self._listening_for_resize = True

    def _on_resize(self, _signum: int, _frame: FrameType | None) -> None:
        self._resized = True

    def _restore_terminal(self) -> None:
        if not self._is_tty or self._closed:
            return
        self._closed = True
        self._stop_listening_for_resize()
        self._write(
            AsciiCanvas.RESET_COLOR
            + ENABLE_LINE_WRAP
            + SHOW_CURSOR
            + LEAVE_ALTERNATE_SCREEN
        )
        self._stream.flush()

    def _stop_listening_for_resize(self) -> None:
        if not self._listening_for_resize:
            return
        self._listening_for_resize = False
        if self._previous_resize_handler is not None:
            signal.signal(signal.SIGWINCH, self._previous_resize_handler)

    def _write(self, text: str) -> None:
        self._stream.write(text)


def _has_work(changes: CanvasChanges, redraw: bool, status_pending: bool) -> bool:
    return redraw or bool(changes.cells) or status_pending


def _visible_lines(lines: Sequence[str], columns: int, rows: int) -> list[str]:
    fitted = [line[:columns] for line in list(lines)[:STATUS_ROWS]]
    return fitted[:rows]


def _colored_cell(x: int, y: int, character: str, color: str) -> str:
    return f"{_cursor(y + 1, x + 1)}{AsciiCanvas.COLORS[color]}{character}"


def _status_line(row: int, text: str) -> str:
    return f"{_cursor(row, 1)}{AsciiCanvas.RESET_COLOR}{text}{CLEAR_TO_END_OF_LINE}"


def _cursor(row: int, column: int) -> str:
    return f"\033[{row};{column}H"


def read_terminal_size() -> tuple[int, int]:
    size = shutil.get_terminal_size(fallback=(80, 24))
    return size.columns, size.lines


def _stream_is_tty(stream: TextIO) -> bool:
    isatty = getattr(stream, "isatty", None)
    if not callable(isatty):
        return False
    return bool(isatty())


def _read_enter() -> None:
    sys.stdin.readline()
