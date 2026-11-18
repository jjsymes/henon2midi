import math


def parse_parameters(text: str) -> tuple[float, ...]:
    if text.strip() == "":
        raise ValueError("function parameters must not be empty")
    try:
        return tuple(float(part) for part in text.split(","))
    except ValueError as error:
        raise ValueError(
            "function parameters must be comma-separated numbers"
        ) from error


def parse_source_range(text: str) -> tuple[float, float]:
    low, high = _pair(text, "source range", float)
    if low == high or not math.isfinite(low) or not math.isfinite(high):
        raise ValueError("source range must be two different finite numbers")
    return low, high


def parse_midi_range(text: str, name: str) -> tuple[int, int]:
    return _pair(text, name, int)


def _pair(text: str, name: str, convert):
    parts = text.split(",")
    if len(parts) != 2:
        raise ValueError(f"{name} must be a comma separated list of 2 values")
    try:
        return convert(parts[0]), convert(parts[1])
    except ValueError as error:
        raise ValueError(
            f"{name} must be a comma separated list of 2 values"
        ) from error
