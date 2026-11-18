from dataclasses import dataclass

CUSTOM_SOURCE_RANGE = (-1.0, 1.0)


@dataclass(frozen=True)
class Preset:
    name: str
    x_prime: str
    y_prime: str
    source_range: tuple[float, float]


CLASSIC = Preset(
    "classic",
    "x*cos(a) - (y - x**2)*sin(a)",
    "x*sin(a) + (y - x**2)*cos(a)",
    (-1.0, 1.0),
)
FOUR_PARAMETER = Preset(
    "four-parameter",
    "sin(a*y) - cos(b*x)",
    "sin(c*x) - cos(d*y)",
    (-2.0, 2.0),
)
PRESETS = {
    CLASSIC.name: CLASSIC,
    FOUR_PARAMETER.name: FOUR_PARAMETER,
}
