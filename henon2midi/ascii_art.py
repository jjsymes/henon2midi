import random


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

    def __init__(self, width: int = 120, height: int = 80):
        self.width = width
        self.height = height
        self.current_color = "white"
        self.canvas = [[" " for _ in range(width)] for _ in range(height)]

    def draw_point(self, x: int, y: int, character: str = "X"):
        color_escape_code = self.COLORS[self.current_color]
        self.canvas[y][x] = color_escape_code + character

    def set_color(self, color: str):
        if color == "random":
            color = random.choice(list(self.COLORS.keys()))
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
