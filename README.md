# Lurker
An offline home assistant tool for operating HueBridge smart home things by spoken words.

Currently, only light requests are supported.

## Requirements
- Python
  - Tested with python 3.9
  - Install the required dependencies by running `pip install --require-virtualenv -r requirements.txt`
- Hardware
  - Lurker requires a recording device available to the host machine. On debian systems, check available devices with `ls -lh /dev/snd`.
  - Optionally: A speaker for playing sounds as feedback to speech inputs.
- Third party
  - Lurker calls the transcription engine [openai-whisper](https://github.com/openai/whisper) for speech-to-text tasks. By default, lurker uses the "tiny" model provided by openai-whisper. More models can be found here: `.venv/lib/python3.9/site-packages/whisper/__init__.py:17`. If the requested model is not present on the machine, openai-whisper will download the respective model. To avoid that, you may also [configure](#configuration-parameters) lurker to use an already downloaded model.

## How to run
Optionally, download the "tiny" openai whisper model and provide the absolute path to the model via environment variable `LURKER_MODEL`. See https://openaipublic.azureedge.net/main/whisper/models/65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9/tiny.pt.
If no model is provided this way, teh whisper application will download a model.

### Run locally
Install the required dependencies from `requirements.txt`.
```commandline
pip install --require-virtualenv -r requirements.txt
```

Run this programm.
```sh
python lurker
```

You may also pass the option `--lurker-home <path>` to let lurker load configuration and actions from the provided [home path](#lurker-home). Otherwise, lurkers assumes its home at `~/lurker`. 

### Run as docker container
The Dockerfile expects the "tiny" model at `misc/models`.
Build the docker image (~8 GB in size).
```sh
docker build . --tag johannesbuchholz/lurker:latest
```

Run the container with `docker run johannesbuchholz/lurker:docker`. 
You will need to expose a sound device of your host machine. Additionally, you probably want to mount proper configuration and actions.
- Sound device: Use [docker option `--device`](https://docs.docker.com/reference/cli/docker/container/run/#device) to expose hardware from the host machine to the docker container.
- Configuration: Use [docker option `-v` or `--mount`](https://docs.docker.com/reference/cli/docker/container/run/#mount) to mount a set of configuration files to the container. Mount configuration to `/lurker/home` inside the container.

Use the shell-script `run_lurker_docker.sh` to conveniently start the docker container with the possibility to read configuration form removable media.
```sh
sh run_lurker.docker.sh
```

## Lurker Home
The lurker home path may contain a configuration file and actions that link key-paragraphs to requests sent to a Hue Bridge.
Per default, the lurker home path is set to `~/lurker` unsless specified via command line option `--lurker-home <path>`.

### Configuration file
Lurker may be configured through a config file at `<lurker-home>/config.json`. That [configuration](#configuration-parameters) may be overridden by environment variables.
The configuration file may look like this:
```json
{
  "LURKER_HOST": "<host of hue bridge>",
  "LURKER_USER": "<registered user name>",
  "LURKER_KEYWORD": "hey john",
  "LURKER_LOG_LEVEL": "DEBUG",
  "LURKER_INPUT_DEVICE": "jabra",
  "LURKER_OUTPUT_DEVICE": "jabra"
}
```

### Environment variables
Every available configuration may also be provided via environment variables on the host machine running lurker. 

### Actions
Actions are pairs of key paragraphs and a request sent to the Hue Bridge. Such actions may be configured file wise under `<lurker-home>/actions`.
Add one json-file per action. File names do not matter. 

Example:
```json
{
  "keys": ["make it bright", "entertain me"],
  "lights": ["ALL"],
  "request": {
    "on": true,
    "bri": 123,
    "hue": 123,
    "sat": 123
  }
}
```
- `"keys"`: An array of instruction paragraphs that are associated with this request.
- `"lights"`: An array of light ids as strings, typically numbers starting from `"1"`. The special id `"ALL"` targets all available lights.
- `"request"`: The actual light request to be sent to the selected lights.
    - `"on"`: If true, turns the light on else off.
    - `"bri"`: Brightness setting.
    - `"hue"`: Hue setting.
    - `"sat"`: Saturation setting.

All fields withing `request` are optional and missing field are not send the Hue Bridge.

### Configuration parameters
All available configuration parameters are defined here: `src/config.py`

These are the most important variables:
- `LURKER_KEYWORD`: Denotes the key word lurker will react to in order to obtain further instructions.
- `LURKER_HOST`: Denotes the host of the Hue Bridge to send instructions to.
- `LURKER_USER`: Denotes the already registered Hue Bridge user. 
- `LURKER_MODEL`: Denotes the absolute path to an open-ai whisper model that lurker should use instead of downloading one.
- `LURKER_INPUT_DEVICE`: Denotes the device name or substring lurker will use to record sound.
- `LURKER_OUTPUT_DEVICE`: Denotes the device name or substring lurker will use when playing sounds.
