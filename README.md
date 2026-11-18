# henon2midi

This application generates midi output and midi files from Henon map data.

## Installation

- Install from PyPI:
```bash
pip3 install henon2midi
```

## Usage

- For help:
```bash
henon2midi --help
```

- Run with default settings:
```bash
henon2midi
```
This will generate a midi file in the current working directory.

- List MIDI outputs, then send to one of them. `default` is the first device:

```bash
henon2midi --list-midi-outputs
henon2midi --midi-output-name "IAC Driver Bus 1"
```

- Enabling midi loopback driver on macOS (e.g. for use with DAWS):
    1. Open 'Audio MIDI Setup.app'
    2. Click 'Window' -> 'Show MIDI Studio'
    3. Double click 'IAC Driver' device
    4. Check 'Device is online' checkbox
    5. Click 'Apply'
    6. Make sure 'IAC Driver' enabled as a midi input device in your DAW

## Installation from source

- Prerequisites:
    - Python 3
    - pip

Make sure pip is up to date:
```bash
python3 -m pip install --upgrade pip
```

- Install package from source code:
```bash
pip install .
```

- Now you can run the application from the command line e.g.
```bash
henon2midi --version
```

## Development

- Pre-requisites:
    - Python 3
    - pip
    - virtualenv

- Use the Makefile for local development:

1. Activate a virtual environment:
```bash
make virtualenv
```

2. Activate the virtual environment (not strictly necessary, if using the Makefile only):
```bash
source .venv/bin/activate
```

3. Install dependencies:
```bash
make install
```

Then you can:

- Run the application:
```bash
make run
```
That is the historical default: classic map, coefficient `1.0`, about 100 orbits, write `henon.mid`, and play the first MIDI device. It is a long playback. Pass flags with `EXTRA_ARGS`:
```bash
make run EXTRA_ARGS="--help"
make run EXTRA_ARGS="--visualize-only -i 20 -s 0.05"
```

Short examples, also listed by `make help`:

```bash
make example-classic    # draw the classic map, no MIDI device needed
make example-sweep      # same map, orbit starts walk around the circle
make example-four       # four-parameter map, coefficients 2,2,2,2, swept start
make example-rotation   # custom equations x'=y, y'=-x
make list-midi          # print MIDI output names
make example-file       # write sweep.mid and play it; needs a MIDI output
```

`example-file` fails before writing if no MIDI output is connected, because playback is part of that run. The other `example-*` targets only draw. Add your own flags after the built-in ones with `EXTRA_ARGS`, for example `make example-four EXTRA_ARGS="--clip"`.

- Run tests:
```bash
make test
```

- Run linter:
```bash
make lint
```
`make fmt` can be used to automatically fix some linting errors.

- Other useful make targets are provided too, see the Makefile for details. Or run `make`/`make help`
