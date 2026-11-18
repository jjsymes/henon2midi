import random
from dataclasses import dataclass


@dataclass(frozen=True)
class CanvasChanges:
    cleared: bool
    cells: tuple[tuple[int, int, str, str], ...]


class AsciiCanvas:
    RESET_COLOR = "\033[0m"
    COLORS = {
        "black": "\033[0;30m",
        "red": "\033[0;31m",
        "green": "\033[0;32m",
        "yellow": "\033[0;33m",
        "blue": "\033[0;34m",
        "magenta": "\033[0;35m",
        "cyan": "\033[0;36m",
        "white": "\033[0;37m",
        "bright_black": "\033[1;30m",
        "bright_red": "\033[1;31m",
        "bright_green": "\033[1;32m",
        "bright_yellow": "\033[1;33m",
        "bright_blue": "\033[1;34m",
        "bright_magenta": "\033[1;35m",
        "bright_cyan": "\033[1;36m",
        "bright_white": "\033[1;37m",
    }

    def __init__(
        self,
        width: int = 120,
        height: int = 80,
        color_order: list[str] | None = None,
    ):
        if width < 1 or height < 1:
            raise ValueError("canvas width and height must be at least 1")
        self.width = width
        self.height = height
        self._color_order = (
            list(self.COLORS) if color_order is None else list(color_order)
        )
        if color_order is None:
            random.shuffle(self._color_order)
        self.current_color = "white"
        self._rows = self._blank_rows()
        self._dirty: dict[tuple[int, int], tuple[str, str]] = {}
        self._cleared = False

    def draw_point(self, x: int, y: int, character: str = "X") -> None:
        color = self.current_color
        self._rows[y][x] = (character, color)
        self._dirty[(x, y)] = (character, color)

    def set_color(self, color: str) -> None:
        if color == "random":
            color = random.choice(list(self.COLORS))
        elif color == "next":
            index = self._color_order.index(self.current_color)
            color = self._color_order[(index + 1) % len(self._color_order)]
        elif color not in self.COLORS:
            raise ValueError(f"Color {color} not supported")
        self.current_color = color

    def clear(self) -> None:
        self._rows = self._blank_rows()
        self.current_color = "white"
        self._dirty.clear()
        self._cleared = True

    def consume_changes(self) -> CanvasChanges:
        cells = tuple(
            (x, y, character, color)
            for (x, y), (character, color) in self._dirty.items()
        )
        changes = CanvasChanges(self._cleared, cells)
        self._dirty.clear()
        self._cleared = False
        return changes

    def painted_cells(self) -> tuple[tuple[int, int, str, str], ...]:
        cells = []
        for y, row in enumerate(self._rows):
            for x, (character, color) in enumerate(row):
                if color is not None:
                    cells.append((x, y, character, color))
        return tuple(cells)

    def generate_string(self) -> str:
        picture = "\n".join(
            "".join(self._cell_text(cell) for cell in row) for row in self._rows
        )
        return self.RESET_COLOR + picture + self.RESET_COLOR

    def _cell_text(self, cell: tuple[str, str | None]) -> str:
        character, color = cell
        if color is None:
            return character
        return self.COLORS[color] + character

    def _blank_rows(self) -> list[list[tuple[str, str | None]]]:
        return [[(" ", None) for _ in range(self.width)] for _ in range(self.height)]
