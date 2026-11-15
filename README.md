# Lurker
An offline home assistant tool for handling predefined instructions by spoken words (english or german).
It ships with a `lights` action handler plugin that maps spoken instructions to lights. Its default
backend logs actions against a set of example lights; alternative backends control a
[HueBridge](https://www.philips-hue.com/en-us/p/hue-bridge/046677458478#overview) in the local
network or do nothing.

This project is in a dynamic development state.

The lurker instruction-to-action flow looks like this:
1. Wake lurker with a keyword or key paragraph ('hey john').
2. Wait for the audio cue indicating that lurker is ready to record an instruction.
3. Instruct a command in natural language ('Turn all the lights out!').
4. Wait for lurker to process and execute the instruction.

```text
2024-11-10 22:45:43,513 [    INFO] Lurker (__main__): 
  _                   _               
 | |                 | |              
 | |     _   _  _ __ | | __ ___  _ __ 
 | |    | | | || '__|| |/ // _ \| '__|
 | |____| |_| || |   |   <|  __/| |   
 |______|\__,_||_|   |_|\_\\___||_|                                         

0.19.6

2024-11-10 22:45:43,517 [    INFO] Lurker (__main__): Determined lurker home: /media/johannes/INTENSO/lurker
2024-11-10 22:45:43,517 [    INFO] Lurker (__main__): Loaded configuration:
LURKER_LOG_LEVEL=INFO
LURKER_LOG_FILE=lurkerlog
LURKER_INPUT_DEVICE=jabra
LURKER_OUTPUT_DEVICE=jabra
LURKER_KEYWORD=hey john
LURKER_LANGUAGE=de
2024-11-10 22:45:43,523 [    INFO] Lurker (src.plugins): Loaded handlers: ['lights']
2024-11-10 22:45:43,924 [    INFO] Lurker (src.lurker): Initializing...
2024-11-10 22:45:44,030 [    INFO] Lurker (SpeechToTextListener): Start recording using keyword 'hey john'
```

## Get lurker
Make sure you meet the [requirements](#requirements).

Lurker is installed from source using a raw python installation.
This installation method is conveniently available through the installer script at `lib/install-lurker.sh`.
Each version is installed into `~/.local/opt/lurker/<version>`, holding the source code, the virtual environment and the [lurker home](#lurker-home) with configuration, plugins and models.

If you are brave enough, you may directly run the following command.
```sh
wget -q -O - https://raw.githubusercontent.com/johannesbuchholz/lurker/refs/heads/main/lib/install-lurker.sh | sh
```

## Requirements

- Lurker requires enough CPU resources to perform speech-to-text transcription in a satisfying fashion. For example, lurker runs fine on a [raspberry pi 5](https://www.raspberrypi.com/products/raspberry-pi-5/).
- Lurker requires a recording device available to the host machine. On debian systems, you may check available devices with commands like `ls -lh /dev/snd`. In our local setup, we were very happy using a [jabra speak](https://www.jabra.com/business/speakerphones/jabra-speak-series) device.
- Optionally: A speaker for playing sounds as feedback to speech inputs.

Lurker requires onnx model files for speech-to-text recognition and, for the `lights` plugin, an
embedder for intent matching.
- Speech: [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) for example `https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-streaming-zipformer-en-kroko-2025-08-06.tar.bz2`
- Embedding: `paraphrase-multilingual-MiniLM-L12-v2` for example `https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2/resolve/main`

The installer script downloads the speech models. Plugin resources such as the embedding model are
downloaded by the plugins themselves: either when the installer asks whether to download resources
for the default plugins now, when running `python . setup`, or on first use.

## Run lurker on a Raspberry Pi
When installing on a raspberry pi, you may follow the installation guide at [install-on-raspberry-pi.md](https://github.com/johannesbuchholz/lurker/blob/main/install-on-raspberry-pi.md) for a complete setup of all required tools and secondary configuration.
We tested lurker on a raspberry pi 5 and 4B (4GB RAM, but 2GB should also suffice) with pleasant performance.

## Run the python project locally
Place the required speech models as described in [requirements](#requirements) in your
[lurker home](#lurker-home), for example `lurker/models/onnx` in this repository. Plugin resources
are fetched automatically when needed.

Install the required dependencies from `requirements.txt`.
```sh
pip install --require-virtualenv -r requirements.txt
```

Then, run the entrypoint with a command.
```sh
python . run
```

The first argument selects `run`, `setup`, or `version`. `python . version` prints the version.

You may pass `--lurker-home <path>` to load configuration and plugins from the provided
[home path](#lurker-home). Otherwise, lurker assumes its home at `<current directory>/lurker`.
Pass `--overlay-home <path>` to overlay configuration and plugins from a second home.
Run `python . setup --lurker-home <path>` to download every plugin's resources without
starting the listener.

## Lurker Home
The lurker home directory is the place where lurker loads configuration and action handler plugins.
The [configuration](#configuration-file) file is expected at `$LURKER_HOME/config.json`. Plugins are
discovered under `$LURKER_HOME/plugins`, and their configuration is read from
`$LURKER_HOME/plugins/config/<plugin-name>.json`.
Specify the lurker home path via command line option `--lurker-home <path>`. If not specified, lurker assumes `<current directory>/lurker` as its home path.

The startup script created by the installer script, `$HOME/.local/opt/lurker/<version>/run-lurker.sh`, passes `$HOME/.local/opt/lurker/<version>/lurker` as the base home. When started with option `-m`, it additionally passes the `lurker` directory found on removable media as `--overlay-home`: configuration and plugins from the media overlay the installation's base home instead of replacing it.

### Configuration file
Lurker may be configured through a config file at `<lurker-home>/config.json`. These properties may also be overridden by environment variables. When an overlay home is used, its `config.json` overrides the base values, and environment variables override both.
For an example configuration, have a look at `lurker/config.json`.

All available configuration parameters are defined and briefly described in `src/config.py`.
Plugins are always loaded from `<lurker-home>/plugins`.

### Plugins
Action handler plugins live in directory packages under `<lurker-home>/plugins`. A plugin is a
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
        super().__init__(context)
        self._timezone = config.get("timezone", "UTC")

    def accepts(self, instruction: str) -> bool:
        return "time" in instruction.lower()

    def handle(self, instruction: str) -> int:
        self._logger.info(f"Time requested ({self._timezone})")
        return 0
```

- Core constructs the handler as `Handler(context, config)`. `context` contains `lurker_home`,
  `plugin_root_dir`, `log_level` and `language`.
- Plugin configuration is a JSON object at `<plugin-root>/config/<plugin-name>.json`; a missing file
  means `{}`, and an overlay config is shallow-merged over the base. Plugins own their defaults and
  schema.
- A plugin may provide `requirements.txt`; core installs it with pip in the running virtual
  environment before importing the plugin. Only install plugins you trust.
- `ensure_resources()` is called after construction on every start and by `setup`. It must be
  cheap when resources are present. If it raises, only that plugin is skipped.
- Discovery considers directory packages only and skips `config`, names starting with `_` or `.`,
  and non-identifiers. Single-file plugins are ignored. A plugin from the overlay home replaces the
  base plugin with the same directory name; overlay-only plugins are added.
- Every handler whose `accepts` returns true receives the instruction. Lurker signals OK only when
  all of them return 0.

### Lights plugin
The shipped plugin is `lights` at `lurker/plugins/lights/`. Configure it in
`<lurker-home>/plugins/config/lights.json`; the default backend is `dummy`:

```json
{"backend": "dummy"}
```

`dummy` keeps a fixed set of example lights and logs generated actions. To control a Philips Hue
bridge (API v1), use:

```json
{"backend": "hue", "host": "<host of hue bridge>", "user": "<registered user name>"}
```

To accept light instructions without acting on them, use:

```json
{"backend": "noop"}
```

The first non-noop action downloads the embedding model into
`<lurker-home>/models/onnx/paraphrase-multilingual-MiniLM-L12-v2` unless it is already present.
