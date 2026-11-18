import math

UNIT_INTERVAL = (-1.0, 1.0)


def rescale(
    value: float,
    initial_range: tuple[float, float],
    new_range: tuple[float, float],
    clip_value: bool = True,
) -> float:
    _require_finite_range(initial_range, "initial_range")
    _require_finite_range(new_range, "new_range")
    if initial_range[0] == initial_range[1]:
        raise ValueError(f"initial_range {initial_range} must have a non-zero width")
    if math.isnan(value):
        raise ValueError(f"value ({value}) is not a finite number")

    if clip_value:
        if value < initial_range[0]:
            value = initial_range[0]
        elif value > initial_range[1]:
            value = initial_range[1]
    elif value < initial_range[0] or value > initial_range[1]:
        raise ValueError(
            f"value ({value}) is not within initial_range ({initial_range})"
        )

    initial_span = initial_range[1] - initial_range[0]
    new_span = new_range[1] - new_range[0]
    return ((value - initial_range[0]) * (new_span / initial_span)) + new_range[0]


def within_range(value: float, bounds: tuple[float, float]) -> bool:
    lower, upper = bounds
    return lower <= value <= upper


def point_to_cell(
    x: float,
    y: float,
    width: int,
    height: int,
    source_range_x: tuple[float, float] = UNIT_INTERVAL,
    source_range_y: tuple[float, float] = UNIT_INTERVAL,
    clamp: bool = False,
) -> tuple[int, int] | None:
    if width < 1 or height < 1:
        raise ValueError("canvas width and height must be at least 1")
    if math.isnan(x) or math.isnan(y):
        return None
    if not clamp and (
        not within_range(x, source_range_x) or not within_range(y, source_range_y)
    ):
        return None

    column = round(rescale(x, source_range_x, (0, width - 1), clip_value=True))
    row = round(rescale(y, source_range_y, (0, height - 1), clip_value=True))
    return column, row


def _require_finite_range(bounds: tuple[float, float], name: str) -> None:
    if len(bounds) != 2 or not all(math.isfinite(bound) for bound in bounds):
        raise ValueError(f"{name} {bounds} must be two finite numbers")
