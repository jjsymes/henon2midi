import pytest
from mido import bpm2tempo

from henon2midi.domain.events import NoteOff, NoteOn
from henon2midi.output.midi_port import (
    MidiOutputNotFound,
    MidiPort,
    available_midi_output_names,
    default_midi_output_name,
    resolve_midi_output_name,
)
from henon2midi.output.mido_messages import to_mido


class FakeOutput:
    def __init__(self):
        self.messages = []
        self.reset_count = 0
        self.closed = False

    def send(self, message):
        self.messages.append(message)

    def reset(self):
        self.reset_count += 1

    def close(self):
        self.closed = True


class FakeClock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


def _port(output, clock, sleeper=None):
    return MidiPort(
        "ignored",
        ticks_per_beat=960,
        bpm=120,
        output=output,
        clock=clock,
        sleeper=sleeper or (lambda _delay: None),
    )


def test_send_waits_only_for_the_time_still_ahead_of_the_clock():
    output = FakeOutput()
    clock = FakeClock()
    slept = []

    def sleeper(delay):
        slept.append(delay)
        clock.now += delay

    port = _port(output, clock, sleeper)
    port.send([NoteOn(60, 100, 0), NoteOff(60, 0, 960)])
    port.send([NoteOff(62, 0, 960)])

    assert slept == pytest.approx([0.5, 0.5])
    assert [message.type for message in output.messages] == [
        "note_on",
        "note_off",
        "note_off",
    ]
    assert output.messages[0].note == 60
    assert output.messages[0].velocity == 100
    assert output.messages[1].time == 960


def test_set_tempo_changes_later_waits_and_keeps_the_clock():
    output = FakeOutput()
    clock = FakeClock()
    slept = []

    def sleeper(delay):
        slept.append(delay)
        clock.now += delay

    port = _port(output, clock, sleeper)
    port.send([NoteOff(60, 0, 960)])
    port.set_tempo(960, 120)
    port.send([NoteOff(60, 0, 960)])
    port.set_tempo(960, 60)
    port.send([NoteOff(60, 0, 960)])

    assert slept == pytest.approx([0.5, 0.5, 1.0])
    with pytest.raises(ValueError, match="bpm"):
        port.set_tempo(960, 0)
    with pytest.raises(ValueError, match="ticks per beat"):
        port.set_tempo(0, 120)


def test_send_does_not_sleep_when_playback_is_already_behind():
    output = FakeOutput()
    clock = FakeClock()
    port = _port(output, clock, sleeper=lambda _delay: pytest.fail("slept"))
    clock.now += 10
    port.send([NoteOff(60, 0, 960)])
    assert output.messages[0].note == 60


def test_close_silences_every_note_without_waiting_and_can_be_repeated():
    output = FakeOutput()
    clock = FakeClock()
    slept = []
    port = _port(output, clock, sleeper=lambda delay: slept.append(delay))
    port.send([NoteOn(60, 100, 0)])
    slept.clear()

    port.close()
    port.close()

    assert slept == []
    assert output.reset_count == 1
    assert output.closed
    note_offs = [message for message in output.messages if message.type == "note_off"]
    assert [message.note for message in note_offs] == list(range(128))
    assert {message.velocity for message in note_offs} == {0}
    assert output.messages[-1].type == "control_change"
    assert output.messages[-1].control == 64
    assert output.messages[-1].value == 0
    assert bpm2tempo(120) > 0


def test_context_manager_closes_the_port_when_playback_fails():
    output = FakeOutput()
    with pytest.raises(RuntimeError, match="boom"):
        with _port(output, FakeClock()):
            raise RuntimeError("boom")
    assert output.closed
    assert output.reset_count == 1


def test_to_mido_rejects_an_unknown_event():
    with pytest.raises(TypeError):
        to_mido(object())


def test_output_names_are_a_copy_of_the_device_list(monkeypatch):
    monkeypatch.setattr(
        "henon2midi.output.midi_port.get_output_names",
        lambda: ["Bus 1", "Bus 2"],
    )
    names = available_midi_output_names()
    names.append("changed")
    assert available_midi_output_names() == ["Bus 1", "Bus 2"]
    assert default_midi_output_name() == "Bus 1"
    assert resolve_midi_output_name("default") == "Bus 1"
    assert resolve_midi_output_name("Bus 2") == "Bus 2"


def test_missing_output_devices_raise_a_specific_error(monkeypatch):
    monkeypatch.setattr(
        "henon2midi.output.midi_port.get_output_names",
        lambda: [],
    )
    with pytest.raises(MidiOutputNotFound, match="No MIDI output devices found"):
        default_midi_output_name()
