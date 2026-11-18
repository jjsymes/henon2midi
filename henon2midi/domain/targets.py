from dataclasses import dataclass
from enum import Enum


class NoteField(Enum):
    NOTE = "note"
    VELOCITY = "velocity"


@dataclass(frozen=True)
class ControlTarget:
    number: int

    def __post_init__(self) -> None:
        if self.number < 0 or self.number > 127:
            raise ValueError(f"Controller number {self.number} is outside 0 to 127")


MidiTarget = NoteField | ControlTarget
