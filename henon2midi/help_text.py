import textwrap
from dataclasses import dataclass

from henon2midi.domain.formula import FUNCTIONS

_LINE_WIDTH = 72


@dataclass(frozen=True)
class _Literal:
    text: str


def verbose_help() -> str:
    return _page(
        (
            (
                "henon2midi turns an iterated map of the plane into MIDI. "
                "A map sends the point (x, y) to a new point. Repeating the "
                "map traces an orbit. Each image of the starting point is one "
                "step of the music. A run plays a family of orbits at "
                "increasing radii."
            ),
            _literal("""\
The map
-------"""),
            (
                "The state is a point (x, y). One step replaces it with the "
                "point the equations call x' and y'. The first point of an "
                "orbit is a seed, and it is not itself played. "
                "--iterations-per-orbit is how many images of that seed are "
                "taken."
            ),
            (
                "A name in an equation is a parameter, aside from x, y, the "
                "constants pi and e, and function names. -p gives the "
                "parameter values in alphabetical order. Startup prints the "
                "names in that same order. r, n, and u belong to the start "
                "of an orbit. An equation cannot use them."
            ),
            _literal("""\
classic
-------"""),
            (
                "classic is the area-preserving Henon map, the quadratic map "
                "Michel Hénon studied in 1969. A step folds the plane, then "
                "rotates that fold. The fold keeps x and subtracts x squared "
                "from y. The parameter a is the angle of the rotation, in "
                "radians, counterclockwise. The default a = 1 is one radian, "
                "about 57 degrees."
            ),
            _literal("""\
    x' = x*cos(a) - (y - x**2)*sin(a)
    y' = x*sin(a) + (y - x**2)*cos(a)"""),
            (
                "The fold and the rotation each keep area, so a small region "
                "keeps its area while the map stretches it into a thin shape. "
                "For some angles the orbits lie on smooth curves. For others "
                "they wander, and many leave any bounded window. Because the "
                "fold bends distances and the rotation mixes the two axes, a "
                "small change in the seed or in a can rearrange the later "
                "points. classic reads both the notes and the drawing from "
                "the window -1 to 1."
            ),
            _literal("""\
The 1976 attractor
------------------"""),
            (
                "The Henon name also belongs to a second map, the one from "
                "1976, which is the map most articles mean. With the usual "
                "parameters a=1.4 and b=0.3, each step multiplies the "
                "area of a small region by 0.3. Orbits settle onto a thin "
                "folded set, a strange attractor: neither a smooth curve nor "
                "a filled region."
            ),
            _literal("""\
    x' = 1 - a*x**2 + y
    y' = b*x"""),
            (
                "Those equations are a custom map. The names sort "
                "alphabetically, so -p sets a and then b. A picture of this "
                "attractor is usually one long orbit. A large "
                "--iterations-per-orbit, and a radial step that leaves room "
                "for only one radius, moves a run toward that picture. "
                "Points outside the window are silent, so the window below "
                "is wider than the default."
            ),
            _literal("""\
    henon2midi --visualize-only \\
        --x-prime='1 - a*x**2 + y' --y-prime='b*x' \\
        -p 1.4,0.3 --source-range=-1.5,1.5 \\
        -i 200 -r 0.1 -s 1"""),
            _literal("""\
four-parameter
--------------"""),
            (
                "four-parameter is the other built-in preset. It couples "
                "sines and cosines, and it is separate from both Henon maps "
                "above. Its parameters are a, b, c, and d, and its window is "
                "-2 to 2. The default -p "
                "is a single 1.0, which suits classic, so this map needs four "
                "values, for example -p 1,1,1,1."
            ),
            _literal("""\
    x' = sin(a*y) - cos(b*x)
    y' = sin(c*x) - cos(d*y)"""),
            _literal("""\
Orbits
------"""),
            (
                "A run plays many short orbits, one radius at a time. The "
                "radius starts at --starting-radius and grows by "
                "--radial-step. An orbit is played while its radius is at "
                "most 1. A start above 1 plays nothing."
            ),
            _literal("""\
    diagonal   the seed (r, r), on the diagonal
    random     a seed on the circle of radius r
    sweep      a seed on that circle, one radian further each orbit
    x; y       two expressions separated by ';'"""),
            (
                "diagonal does not use the circle. The point (r, r) lies a "
                "distance r*sqrt(2) from the origin. random and sweep do use "
                "the circle. random takes its angle "
                "from u, and --seed fixes the sequence of draws. sweep uses "
                "the orbit index as the angle in radians: the first seed is "
                "at angle 0, which is the point (r, 0), and the next is 1 "
                "radian on. A full turn is 2*pi radians, a little over six "
                "orbits."
            ),
            (
                "A custom start may use r for the radius, n for the orbit "
                "index from 0, and u for one number per orbit, drawn from 0 "
                "up to but not including 1. pi, e, and the map's parameters "
                "are available too. x and y are not available in a start. "
                "Those names mean the point inside the map. The same --seed "
                "makes the MIDI file "
                "and the playback share one sequence."
            ),
            (
                "With a radius of 0, a step of 0.01, and 100 points on each "
                "orbit, the defaults come to about ten thousand notes. At "
                "120 bpm and 4 "
                "notes a beat, that is a piece of about twenty minutes. The "
                "MIDI file is written in full before playback starts. A "
                "short look, with no MIDI device, is:"
            ),
            _literal("""\
    henon2midi --visualize-only -i 20 -s 0.05"""),
            (
                "If an iteration overflows or divides by zero, that orbit "
                "ends and the next radius begins."
            ),
            _literal("""\
From points to MIDI
-------------------"""),
            (
                "x and y are read inside a source window. classic uses -1 "
                "to 1, four-parameter uses -2 to 2, and a custom map uses -1 "
                "to 1 until --source-range replaces it. Pass the two ends "
                "separated by a comma. The low end of the window maps to the "
                "first number of --x-midi-value-range or "
                "--y-midi-value-range, and the high end maps to the second. "
                "Reversing a MIDI range flips that axis. Both numbers are "
                "integers from 0 to 127."
            ),
            (
                "--x-midi-parameter-mappings lists what x controls. "
                "--y-midi-parameter-mappings lists what y controls. Every "
                "target of an axis receives that axis's value."
            ),
            _literal("""\
    note        pitch
    velocity    how hard the note is struck
    pan         a controller name; volume and knob-3 are others
    10, cc20    a controller number"""),
            (
                "The default sends x to note, and y to velocity and pan. If "
                "both axes name one target, the value from y is the one that "
                "is sent. Repeating a target on one axis keeps the first one. "
                "If note or velocity is not named by either axis, it stays "
                "at 64."
            ),
            (
                "A point outside the window plays no note. The step of time "
                "still happens, so the gap is a rest. --clip clamps the point "
                "into the window and plays it. --sustain holds the pedal, so "
                "a note can keep sounding under the next ones. With the pedal "
                "up, each note ends as the next step begins."
            ),
            (
                "--bpm is the tempo in quarter notes per minute. "
                "--notes-per-beat is how many steps fall in one quarter note. "
                "The default 4 is a sixteenth-note grid. --ticks-per-beat is "
                "how many MIDI ticks make up that quarter note. A step lasts "
                "ticks-per-beat / notes-per-beat ticks, and a remainder is "
                "dropped. 960 ticks per beat is a common DAW resolution."
            ),
            (
                "--out is the MIDI file, henon.mid unless another path is "
                "given. An empty path writes no file. The file is a single "
                "pass, including when --continual-loop repeats the playback. "
                "--midi-output-name chooses the device. default means the "
                "first name from --list-midi-outputs. If that device is "
                "missing, the run stops before it writes the file. "
                "--draw-ascii-art plots the points during playback, in the "
                "same window the notes use. --visualize-only only plots. It "
                "needs no MIDI device, and it rejects an explicit --out or "
                "--midi-output-name."
            ),
            _literal("""\
Custom equations
----------------"""),
            (
                "Pass both --x-prime and --y-prime to replace the preset. "
                "Passing --map as well is an error. A name other than x, y, "
                "pi, e, or a function becomes a parameter, filled from -p in "
                "alphabetical order. A leading minus has to be attached with "
                "an equals sign, or the option parser reads it as a flag:"
            ),
            _literal("""\
    --x-prime=-y"""),
            (
                "The arithmetic is + - * / %, ** for a power, and parentheses. "
                "Powers group to the right, as in Python. * / % bind more "
                "tightly than + -. A leading minus applies to the power that "
                "follows, so -2**2 is -(2**2)."
            ),
            "The functions are:",
            _functions_by_arity(),
            (
                "atan2(y, x) follows Python. min and max take two values "
                "here, not a longer list. Startup prints the equations, the "
                "parameter names in -p order, and the source window."
            ),
            "The option reference follows.",
        )
    )


def _literal(text: str) -> _Literal:
    return _Literal(text)


def _page(parts: tuple[str | _Literal, ...]) -> str:
    return "\n\n".join(_render(part) for part in parts)


def _render(part: str | _Literal) -> str:
    if isinstance(part, _Literal):
        return part.text
    return textwrap.fill(
        part,
        width=_LINE_WIDTH,
        break_long_words=False,
        break_on_hyphens=False,
    )


def _functions_by_arity() -> _Literal:
    grouped: dict[int, list[str]] = {}
    for name, (count, _function) in FUNCTIONS.items():
        grouped.setdefault(count, []).append(name)
    lines = []
    for count in sorted(grouped):
        noun = "argument" if count == 1 else "arguments"
        lines.append(
            textwrap.fill(
                f"{count} {noun}: {', '.join(grouped[count])}.",
                width=_LINE_WIDTH,
                subsequent_indent="    ",
                break_long_words=False,
                break_on_hyphens=False,
            )
        )
    return _Literal("\n\n".join(lines))
