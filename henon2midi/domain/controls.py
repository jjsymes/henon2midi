from dataclasses import dataclass

from henon2midi.domain.targets import ControlTarget, MidiTarget, NoteField


@dataclass(frozen=True)
class _ControllerNames:
    number: int
    printed_name: str
    other_names: tuple[str, ...] = ()


def _names(number: int, printed_name: str, *other_names: str) -> _ControllerNames:
    return _ControllerNames(number, printed_name, other_names)


_SPECIFICATION: tuple[_ControllerNames, ...] = (
    _names(0, "bank", "bank-select"),
    _names(1, "modulation", "mod", "mod-wheel", "modulation-wheel"),
    _names(2, "breath", "breath-controller"),
    _names(4, "foot", "foot-controller", "foot-pedal"),
    _names(5, "portamento-time"),
    _names(6, "data-entry"),
    _names(7, "volume", "channel-volume", "main-volume"),
    _names(8, "balance"),
    _names(10, "pan", "panorama"),
    _names(11, "expression"),
    _names(12, "effect-1", "effect-control-1"),
    _names(13, "effect-2", "effect-control-2"),
    _names(16, "general-purpose-1"),
    _names(17, "general-purpose-2"),
    _names(18, "general-purpose-3"),
    _names(19, "general-purpose-4"),
    _names(32, "bank-lsb", "bank-select-lsb"),
    _names(33, "modulation-lsb"),
    _names(34, "breath-lsb"),
    _names(36, "foot-lsb"),
    _names(37, "portamento-time-lsb"),
    _names(38, "data-entry-lsb"),
    _names(39, "volume-lsb"),
    _names(40, "balance-lsb"),
    _names(42, "pan-lsb"),
    _names(43, "expression-lsb"),
    _names(64, "sustain", "damper", "hold", "hold-pedal"),
    _names(65, "portamento", "portamento-switch"),
    _names(66, "sostenuto", "sostenuto-pedal"),
    _names(67, "soft", "soft-pedal", "una-corda"),
    _names(68, "legato", "legato-footswitch"),
    _names(69, "hold-2"),
    _names(70, "sound-variation", "variation", "sound-controller-1"),
    _names(
        71,
        "timbre",
        "resonance",
        "harmonics",
        "harmonic-intensity",
        "sound-controller-2",
    ),
    _names(72, "release", "release-time", "sound-controller-3"),
    _names(73, "attack", "attack-time", "sound-controller-4"),
    _names(74, "brightness", "cutoff", "filter-cutoff", "sound-controller-5"),
    _names(75, "decay", "decay-time", "sound-controller-6"),
    _names(76, "vibrato-rate", "sound-controller-7"),
    _names(77, "vibrato-depth", "sound-controller-8"),
    _names(78, "vibrato-delay", "sound-controller-9"),
    _names(79, "sound-controller-10"),
    _names(80, "general-purpose-5"),
    _names(81, "general-purpose-6"),
    _names(82, "general-purpose-7"),
    _names(83, "general-purpose-8"),
    _names(84, "portamento-control"),
    _names(88, "high-resolution-velocity"),
    _names(91, "reverb", "reverb-send"),
    _names(92, "tremolo"),
    _names(93, "chorus", "chorus-send"),
    _names(94, "detune", "celeste"),
    _names(95, "phaser"),
    _names(96, "data-increment"),
    _names(97, "data-decrement"),
    _names(98, "nrpn-lsb"),
    _names(99, "nrpn-msb"),
    _names(100, "rpn-lsb"),
    _names(101, "rpn-msb"),
)

# Usual chart names. 20 and 21 have no specification name, so the chart name is printed.
_CHART: tuple[tuple[int, tuple[str, ...]], ...] = (
    (16, ("ribbon",)),
    (17, ("knob-1",)),
    (19, ("knob-2",)),
    (20, ("knob-3",)),
    (21, ("knob-4",)),
)


def parse_midi_target(text: str) -> MidiTarget:
    raw = text.strip()
    if raw == "":
        raise ValueError("MIDI target must not be empty")
    number = _controller_number(raw.casefold())
    if number is not None:
        return ControlTarget(number)
    word = _word(raw)
    note = _NOTE_FIELDS.get(word)
    if note is not None:
        return note
    controller = _CONTROL_WORDS.get(word)
    if controller is None:
        raise ValueError(
            f"Unknown MIDI target {raw!r}. "
            "Use note, velocity, a controller name such as pan, volume, or knob-3, "
            "or a controller number such as 10 or cc20."
        )
    return ControlTarget(controller)


def parse_midi_targets(text: str) -> tuple[MidiTarget, ...]:
    return tuple(parse_midi_target(part) for part in text.split(","))


def describe_midi_target(target: MidiTarget) -> str:
    if isinstance(target, NoteField):
        return target.value
    return _PRINTED_NAMES.get(target.number, f"cc{target.number}")


def describe_midi_targets(targets: tuple[MidiTarget, ...]) -> str:
    return ", ".join(describe_midi_target(target) for target in targets)


def _glossary(
    specification: tuple[_ControllerNames, ...],
    chart: tuple[tuple[int, tuple[str, ...]], ...],
) -> tuple[dict[str, int], dict[int, str]]:
    words: dict[str, int] = {}
    printed: dict[int, str] = {}
    for entry in specification:
        names = (entry.printed_name, *entry.other_names)
        _add_controller(words, printed, entry.number, names)
    for number, names in chart:
        _add_controller(words, printed, number, names)
    return words, printed


def _add_controller(
    words: dict[str, int],
    printed: dict[int, str],
    number: int,
    names: tuple[str, ...],
) -> None:
    ControlTarget(number)
    for index, name in enumerate(names):
        key = _word(name)
        _claim_word(words, key, number)
        if index == 0:
            printed.setdefault(number, key)


def _claim_word(words: dict[str, int], key: str, number: int) -> None:
    if key in _NOTE_FIELDS:
        raise ValueError(f"{key} is a note field, not a controller name")
    existing = words.get(key)
    if existing is not None and existing != number:
        raise ValueError(f"{key} already maps to controller {existing}")
    words[key] = number


def _word(text: str) -> str:
    spaced = text.casefold().replace("_", " ").replace("-", " ")
    return "-".join(spaced.split())


def _controller_number(token: str) -> int | None:
    body = token[2:].lstrip(" -_") if token.startswith("cc") else token
    return _whole_integer(body)


def _whole_integer(text: str) -> int | None:
    negative = text.startswith("-")
    digits = text[1:] if negative else text
    if digits == "" or not digits.isdigit():
        return None
    value = int(digits)
    return -value if negative else value


_NOTE_FIELDS = {field.value: field for field in NoteField}
_CONTROL_WORDS, _PRINTED_NAMES = _glossary(_SPECIFICATION, _CHART)
