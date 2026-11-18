import math


class Parameters:
    def __init__(self, names: tuple[str, ...], values: tuple[float, ...]):
        if len(names) != len(set(names)):
            raise ValueError("parameter names must be unique")
        _require_count(names, values)
        self.names = names
        self._index = {name: index for index, name in enumerate(names)}
        self._values = _finite_values(names, values)

    @property
    def values(self) -> tuple[float, ...]:
        return self._values

    def get(self, name: str) -> float:
        return self._values[self._position(name)]

    def set(self, name: str, value: float) -> None:
        position = self._position(name)
        updated = list(self._values)
        updated[position] = _finite_value(name, value)
        self._values = tuple(updated)

    def replace(self, values: tuple[float, ...]) -> None:
        _require_count(self.names, values)
        self._values = _finite_values(self.names, values)

    def bindings(self) -> dict[str, float]:
        return dict(zip(self.names, self._values))

    def _position(self, name: str) -> int:
        try:
            return self._index[name]
        except KeyError as error:
            raise ValueError(_unknown(name, self.names)) from error

    def __repr__(self) -> str:
        pairs = ", ".join(
            f"{name}={value}" for name, value in zip(self.names, self._values)
        )
        return f"Parameters({pairs})"


def _require_count(names: tuple[str, ...], values: tuple[float, ...]) -> None:
    if len(names) == len(values):
        return
    listed = ", ".join(names) if names else "none"
    raise ValueError(
        f"expected {len(names)} parameter values ({listed}), got {len(values)}"
    )


def _finite_values(
    names: tuple[str, ...], values: tuple[float, ...]
) -> tuple[float, ...]:
    return tuple(_finite_value(name, value) for name, value in zip(names, values))


def _finite_value(name: str, value: float) -> float:
    if _is_finite_number(value):
        return float(value)
    raise ValueError(f"{name} must be a finite number")


def _is_finite_number(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(value)


def _unknown(name: str, names: tuple[str, ...]) -> str:
    listed = ", ".join(names) if names else "none"
    return f"{name} is not a parameter of this map; parameters are {listed}"
