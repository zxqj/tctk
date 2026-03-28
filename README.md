# Twitch Streamelements Raffle Joiner

[![PyPI](https://img.shields.io/pypi/v/tserj.svg)](https://pypi.org/project/tserj/)



## Installation

To install this tool using `pip`:
```bash
pip install tserj
```
## Usage

For help, run:
```bash
tserj --help
```
You can also use:
```bash
python -m tserj --help
```
## Development

To contribute to this tool, first checkout the code. Then create a new virtual environment:
```bash
cd tserj
python -m venv venv
source venv/bin/activate
```
Now install the dependencies and test dependencies:
```bash
pip install -e '.[test]'
```
To run the tests:
```bash
python -m pytest
```
copy config.example.yaml to config.yaml and fill in

## Interactive REPL

A `pythonstartup.py` file is provided for interactive sessions. It connects to the Twitch channel defined in `config.yaml` and drops you into a Python REPL with useful objects pre-loaded.

```bash
APP_ENV=production PYTHONSTARTUP=pythonstartup.py uv run python
```

### Available in the REPL

| Name | Description |
|------|-------------|
| `send(msg, delay=None)` | Send a message to the channel (sync wrapper) |
| `sender` | The underlying `ChannelSender` instance (async methods) |
| `V` | `FontVariant` enum for Unicode text formatting |
| `bot` | The `ChatBot` instance |

### Examples

```python
# Send a plain message
send("hello chat")

# Send a delayed message
send("brb", delay=5)

# Send formatted text using FontVariant
send(V.Script.formatter()("fancy text"))
send(V.Script.formatter(bold=True)("bold script"))
send(V.SansSerif.formatter(bold=True, italic=True)("bold italic sans"))
```

### Available FontVariants

`Script`, `Fraktur`, `DoubleStruck`, `SansSerif`, `Monospace` -- each with varying support for `bold` and `italic` options.
