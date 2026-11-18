from collections.abc import Callable
from time import sleep, time
from typing import Protocol

from mido import bpm2tempo, get_output_names, open_output, tick2second

from henon2midi.domain.events import MidiEvent, silence_events
from henon2midi.output.mido_messages import to_mido


class MidiOutputNotFound(Exception):
    pass


class RawMidiOutput(Protocol):
    def send(self, message: object) -> None:
        pass

    def reset(self) -> None:
        pass

    def close(self) -> None:
        pass


class MidiPort:
    def __init__(
        self,
        port_name: str,
        ticks_per_beat: int = 960,
        bpm: int = 120,
        output: RawMidiOutput | None = None,
        clock: Callable[[], float] | None = None,
        sleeper: Callable[[float], None] | None = None,
    ):
        self._output = output if output is not None else open_output(port_name)
        self._ticks_per_beat = ticks_per_beat
        self._tempo = bpm2tempo(bpm)
        self._clock = time if clock is None else clock
        self._sleeper = sleep if sleeper is None else sleeper
        self._started_at = self._clock()
        self._input_time = 0.0
        self._closed = False

    def set_tempo(self, ticks_per_beat: int, bpm: int) -> None:
        if ticks_per_beat < 1:
            raise ValueError("ticks per beat must be at least 1")
        if bpm < 1:
            raise ValueError("bpm must be at least 1")
        self._ticks_per_beat = ticks_per_beat
        self._tempo = bpm2tempo(bpm)

    def send(self, events: list[MidiEvent]) -> None:
        for event in events:
            self._wait_for(event.time)
            self._output.send(to_mido(event))

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._output.reset()
        for event in silence_events():
            self._output.send(to_mido(event))
        self._output.close()

    def __enter__(self) -> "MidiPort":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()

    def _wait_for(self, delta_ticks: int) -> None:
        self._input_time += tick2second(
            delta_ticks,
            ticks_per_beat=self._ticks_per_beat,
            tempo=self._tempo,
        )
        remaining = self._input_time - (self._clock() - self._started_at)
        if remaining > 0:
            self._sleeper(remaining)


def available_midi_output_names() -> list[str]:
    return list(get_output_names())


def default_midi_output_name() -> str:
    output_names = available_midi_output_names()
    if not output_names:
        raise MidiOutputNotFound("No MIDI output devices found")
    return output_names[0]


def resolve_midi_output_name(requested: str) -> str:
    if requested == "default":
        return default_midi_output_name()
    return requested
