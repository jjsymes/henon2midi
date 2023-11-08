import random

from henon2midi.math import rescale_number_to_range

class AsciiArtCanvas:
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
    COLORS_LIST = list(COLORS.keys())
    random.shuffle(COLORS_LIST)

    def __init__(self, width: int = 120, height: int = 80):
        self.width = width
        self.height = height
        self.current_color = "white"
        self.canvas = [[" " for _ in range(width)] for _ in range(height)]

    def draw_point(self, x: int, y: int, character: str = "X"):
        color_escape_code = self.COLORS[self.current_color]
        self.canvas[-y][x] = color_escape_code + character

    def set_color(self, color: str):
        if color == "random":
            color = random.choice(list(self.COLORS.keys()))
        elif color == "next":
            index_of_current_color = self.COLORS_LIST.index(self.current_color)
            index_of_next_color = (index_of_current_color + 1) % len(self.COLORS_LIST)
            color = self.COLORS_LIST[index_of_next_color]
        elif color not in self.COLORS:
            raise Exception(f"Color {color} not supported")

        self.current_color = color

    def clear(self):
        self.canvas = [[" " for _ in range(self.width)] for _ in range(self.height)]

    def generate_string(self):
        return (
            self.RESET_COLOR
            + "\n".join(["".join(row) for row in self.canvas])
            + self.RESET_COLOR
        )


def draw_data_point_on_canvas(
    data_point: tuple[float, float],
    ascii_art_canvas: AsciiArtCanvas,
    is_new_orbit: bool,
    current_iteration: int,
    clip: bool = False,
):
    x = data_point[0]
    y = data_point[1]
    if current_iteration == 1:
        ascii_art_canvas.clear()
    if is_new_orbit:
        ascii_art_canvas.set_color("next")
    try:
        x_canvas_coord = round(
            rescale_number_to_range(
                x,
                (-1.0, 1.0),
                (0, ascii_art_canvas.width - 1),
                clip_value=clip,
            )
        )
        y_canvas_coord = round(
            rescale_number_to_range(
                y,
                (-1.0, 1.0),
                (0, ascii_art_canvas.height - 1),
                clip_value=clip,
            )
        )
    except ValueError:
        pass
    else:
        ascii_art_canvas.draw_point(x_canvas_coord, y_canvas_coord, "█")