# Lurker

Lurker is a private, offline voice assistant for your home. Speak naturally, and lurker turns your
words into actions locally, without sending audio or instructions to a cloud service.

- **Private by design.** Speech recognition runs on your own machine. No account, no cloud, and no
  data leaving the house.
- **Natural language.** Ask for what you want instead of memorizing rigid commands. Choose your own
  wake phrase. Lurker currently supports English and German language.
- **Extensible.** Plugins connect spoken instructions to lights, shutdown, and your own automations via removable media
  - no tinkering with the host machine after installation.
- **Runs on small hardware.** A Raspberry Pi 4B (4GB) is totally enough to run lurker in the living room without performance compromise.

Lurker ships with plugins for controlling lights and for powering off the machine. It is under active
development, so interfaces may still change.

A typical interaction looks like this:

1. Say the wake word and the instruction in one sentence, for example
   "Hey John, turn off all the lights".
2. Lurker detects speech, transcribes it locally and sends the instruction to all capable handlers.
3. Every handler that accepts the remaining instruction executes it.

```text
$ python . run

  _                   _
 | |                 | |
 | |     _   _  _ __ | | __ ___  _ __
 | |    | | | || '__|| |/ // _ \| '__|
 | |____| |_| || |   |   <|  __/| |
 |______|\__,_||_|   |_|\_\\___||_|

<version>

... [    INFO] Lurker (src.run): Bootstrapped lurker
... [    INFO] Lurker (src.plugins): Loaded handlers (2): ['lights', 'shutdown']
... [    INFO] Lurker (src.lurker): Start listening...
```

## Get lurker

Make sure you meet the [requirements](#requirements).

Lurker is installed from source using a plain Python installation. The installer script at
`lib/install-lurker.sh` performs the setup for you. Each version is installed into
`~/.local/opt/lurker/<version>`, containing the source code, a virtual environment, and the
[lurker home](#lurker-home) with configuration, plugins, and models.

If you are brave enough, run:

```sh
wget -q -O - https://raw.githubusercontent.com/johannesbuchholz/lurker/refs/heads/main/lib/install-lurker.sh | sh
```

## Requirements

- Python 3.11 or newer. The installer enforces the major and minor version declared in
  `.python-version`.
- Enough CPU resources for local speech-to-text transcription. Lurker runs well on a
  [Raspberry Pi 5](https://www.raspberrypi.com/products/raspberry-pi-5/) and has also been pleasantly tested on a Raspberry Pi 4B with 4 GB RAM.
- A recording device available to the host. On Debian-based systems, inspect the devices with
  `ls -lh /dev/snd` or `arecord -l`. A USB speakerphone like [Jabra Speak](https://www.jabra.com/business/speakerphones/jabra-speak-series) works well for both input and output.
- `libportaudio2`, which is required by `sounddevice`.
- Optionally, an output device for the feedback sounds.

Lurker needs ONNX model files for speech recognition and, when the shipped `lights` plugin does not use the
`noop` backend, an embedding model for intent matching:

- Speech: [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) streaming zipformer models, 
  for example `sherpa-onnx-streaming-zipformer-en-kroko-2025-08-06`.
- Embedding: `paraphrase-multilingual-MiniLM-L12-v2`

The installer downloads the German and English speech models. Plugin resources, such as the
embedding model, are downloaded optionally by the plugins during lurker installation or on first startup.

## Run lurker on a Raspberry Pi

For a complete setup of the required system tools, automounting, and secondary configuration, follow
[install-on-raspberry-pi.md](install-on-raspberry-pi.md). Lurker has been tested on a Raspberry Pi 5
and a Raspberry Pi 4B with 4 GB RAM; 2 GB should also be sufficient.

## Run the python project locally

Clone this repository. Then, place the required speech models in the [lurker home](#lurker-home), for example under
`lurker/models/onnx`. The runtime selects the model whose name contains the
configured language, such as `-en-` or `-de-`. Plugin resources are fetched automatically by the plugins themselves.

Create a virtual environment and install the dependencies from `requirements.txt`:

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

Then run the entrypoint with a command:

```sh
python . run
```

The first argument selects `run`, `setup` or `version`. For example, `python . version` prints the version.

You may pass `--lurker-home <path>` to load configuration and plugins from the provided
[home path](#lurker-home). Otherwise, lurker assumes its home at `<current directory>/lurker`.
Pass `--overlay-home <path>` to overlay configuration and plugins from a second home. 
With that, you may target removable media or some other directory to host sensitive information, for example.
Run`python . setup --lurker-home <path>` to provision every plugin's resources once and exit without starting the listener.

## Lurker Home

The lurker home directory is where lurker loads its configuration, models, and action-handler plugins. 

A typical home looks like this:

```text
lurker/
├── config.json
├── models/
│   └── onnx/
└── plugins/
    ├── config/
    │   ├── lights.json
    │   └── shutdown.json
    ├── lights/
    └── shutdown/
```

The [configuration file](#configuration-file) is expected at `<lurker-home>/config.json`. Plugins
are discovered under `<lurker-home>/plugins`, and their configuration is read from
`<lurker-home>/plugins/config/<plugin-name>.json`. If `--lurker-home` is not specified, lurker uses
`<current directory>/lurker`.

Configuration from the overlay is shallow-merged over the base configuration, and overlay plugins replace base 
plugins with the same directory name. The base home still provides models and any plugins that the overlay does
not replace.

### Configuration file

Lurker is configured through `<lurker-home>/config.json`. Values may be overridden by environment
variables. When an overlay home is used, its `config.json` overrides the base values, and environment
variables override both.

An example configuration:

```json
{
  "LURKER_KEYWORD": ["/hey john(ny)?/", "hey john"],
  "LURKER_LANGUAGE": "en",
  "LURKER_INPUT_DEVICE": "jabra",
  "LURKER_OUTPUT_DEVICE": "jabra",
  "LURKER_LOG_LEVEL": "INFO"
}
```

The most important settings are:

- `LURKER_KEYWORD`: A list of wake words. Plain strings are matched case-insensitively; values
  wrapped in `/` are regular expressions.
- `LURKER_LANGUAGE`: Language used for speech recognition and plugin defaults, for example `en` or `de`.
- `LURKER_INPUT_DEVICE` and `LURKER_OUTPUT_DEVICE`: Names or name fragments of the recording and playback devices.
- `LURKER_LOG_LEVEL` and `LURKER_LOG_FILE`: Logging level and optional log file. A relative log file
  name is resolved against the lurker home.
- `LURKER_SPEECH_MODEL_SUFFIX`: Optional filter for selecting a speech model by name fragment.
- `LURKER_SPEECH_CONFIG`: Optional nested object for voice activity detection and speech capture
  tuning.

All available parameters are defined and documented in `src/config.py`.

### Plugins

Action-handler plugins live in directory packages under `<lurker-home>/plugins`. A plugin is a
directory with an `__init__.py` exposing a `Handler` class:

```python
# plugins/clock/__init__.py
from .handler import ClockHandler as Handler

__all__ = ["Handler"]
```

```python
# plugins/clock/handler.py
from src.action_handler import ActionHandler, LurkerContext


class ClockHandler(ActionHandler):
    key = "clock"

    def __init__(self, context: LurkerContext, config: dict) -> None:
        super().__init__(context, config)
        self._timezone = config.get("timezone", "UTC")

    def accepts(self, instruction: str) -> bool:
        return "time" in instruction.lower()

    def handle(self, instruction: str) -> int:
        self._logger.info(f"Time requested ({self._timezone})")
        return 0
```

- Plugin configuration is a JSON object at `<plugin-root>/config/<plugin-name>.json`. A missing file
  means `{}`, and an overlay config is shallow-merged over the base config.
- A plugin may provide `requirements.txt`. Lurker installs it with pip in the running virtual
  environment before importing the plugin. **Only install plugins you trust!**
- The plugin discovery considers directory packages only and skips names starting with `_` or `.`
  and non-identifiers. Single-file plugins are ignored. A plugin from the overlay home replaces the
  base plugin with the same directory name; overlay-only plugins are added.

### Lights plugin

The shipped `lights` plugin lives at `lurker/plugins/lights/`. Configure it in
`<lurker-home>/plugins/config/lights.json`.

To control a Philips Hue bridge (API v1), use:

```json
{"backend": "hue", "host": "<host of hue bridge>", "user": "<registered user name>"}
```

To accept light instructions without acting on them, use `{"backend": "noop"}`.
When the backend is `dummy` or `hue`, the plugin downloads the embedding model into
`<lurker-home>/models/onnx/paraphrase-multilingual-MiniLM-L12-v2` during startup or setup unless it
is already present.

### Shutdown plugin

The shipped `shutdown` plugin lives at `lurker/plugins/shutdown/`. It powers off the machine when the
instruction contains the configured trigger. Configure it in `<lurker-home>/plugins/config/shutdown.json`:

```json
{"trigger": "lorem ipsum", "delay": "3"}
```

The plugin schedules `poweroff` in the background after a delay.
The user running lurker must be allowed to power off the machine.
