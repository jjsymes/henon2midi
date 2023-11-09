from time import sleep, time
from typing import Optional, Union

from mido import (
    Message,
    MetaMessage,
    MidiFile,
    MidiTrack,
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

    def send(self, messages: Union[Message, list[Message]]):
        if isinstance(messages, Message):
            messages = [messages]
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

    def reset(self):
        self.playback_start_time = time()
        self.input_time = 0.0
        self.midi_output.reset()

        sustain_off_msg = Message("control_change", control=64, value=0)
        reset_modulation_msg = Message("control_change", control=1, value=0)
        reset_pan_msg = Message("control_change", control=10, value=64)
        reset_all_controllers_msg = Message("control_change", control=121, value=0)
        all_notes_off_msg = Message("control_change", control=123, value=0)
        note_off_msgs = [
            Message("note_off", note=note, velocity=0) for note in range(128)
        ]

        self.send(
            [
                sustain_off_msg,
                reset_modulation_msg,
                reset_pan_msg,
                reset_all_controllers_msg,
                all_notes_off_msg,
            ]
            + note_off_msgs
        )


def get_available_midi_output_names():
    return get_output_names()


def get_default_midi_output_name() -> str:
    output_names = get_available_midi_output_names()
    if len(output_names) == 0:
        raise Exception("No MIDI output devices found")
    return output_names[0]


def create_midi_file_from_messages(
    messages: list[Message], ticks_per_beat: int = 960, bpm: Optional[int] = None
) -> MidiFile:
    mid = MidiFile(ticks_per_beat=ticks_per_beat)
    track = MidiTrack()
    mid.tracks.append(track)
    if bpm is not None:
        tempo = bpm2tempo(bpm)
        try:
            track.append(MetaMessage("set_tempo", tempo=tempo))
        except ValueError:
            raise Exception(f"Invalid BPM, either too low or too high: BPM={bpm}.")
    track.extend(messages)
    return mid
