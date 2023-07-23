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

- Sending midi output to a specific device:

```
henon2midi --midi-out-device device_name
```

Where `device_name` is the name of the midi device you want to send the output to. Use a `device name` of 'default' to use the first available device e.g.

```bash
henon2midi --midi-out-device 'device_name'
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
source venv/bin/activate
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
Extra arguments can be passed by providing EXTRA_ARGS variable e.g.
```bash
make run EXTRA_ARGS="--help"
```

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
