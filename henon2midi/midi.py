from time import sleep, time

from mido import (
    Message,
    MidiFile,
    bpm2tempo,
    get_output_names,
    open_output,
    tick2second,
)
from mido.backends.rtmidi import Output


class MidiMessagePlayer:
    def __init__(
        self, midi_output_name: str, ticks_per_beat: int = 960, bpm: int = 120
    ):
        self.midi_output: Output = open_output(midi_output_name)
        self.ticks_per_beat = ticks_per_beat
        self.tempo = bpm2tempo(bpm)
        self.playback_start_time = time()
        self.input_time = 0.0

    def send(self, messages: list[Message]):
        for msg in messages:
            time_s = tick2second(
                msg.time, ticks_per_beat=self.ticks_per_beat, tempo=self.tempo
            )
            self.input_time += time_s
            current_playback_time = time() - self.playback_start_time
            duration_to_next_event_s = self.input_time - current_playback_time

            if duration_to_next_event_s > 0:
                sleep(duration_to_next_event_s)

            self.midi_output.send(msg)


def get_available_midi_output_names():
    return get_output_names()


def get_default_midi_output_name() -> str:
    output_names = get_available_midi_output_names()
    if len(output_names) == 0:
        raise Exception("No MIDI output devices found")
    return output_names[0]


def save_midi_file(midi: MidiFile, filename: str):
    midi.save(filename)
