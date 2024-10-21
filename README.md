# Lurker
An offline home assistant tool for operating HueBridge smart home things by spoken words.

Currently, only light requests are supported.

This project is in a dynamic development state.

## Get lurker
Make sure you meet the [requirements](#requirements).
Lurker may be installed from source either using a raw python installation or by building a docker image through the
installer script at `lib/install-lurker.sh`.

If you are brave enough, you may directly run one of the following commands
For a docker installation, use
> wget -q -O - https://raw.githubusercontent.com/johannesbuchholz/lurker/refs/heads/main/lib/install-lurker.sh | sh -s -- -d

For a python installation, use
> wget -q -O - https://raw.githubusercontent.com/johannesbuchholz/lurker/refs/heads/main/lib/install-lurker.sh | sh -s -- -p

For installation on raspberry pi, you may follow you may follow the installation guide at [install-on-rasbian.md](https://github.com/johannesbuchholz/lurker/blob/main/install-on-rasbian.md)

### Requirements
Regardless of your preferred installation method, lurker will need certain things to be set up beforehand:

- Python [3.9, 3.11)
- Hardware
  - Lurker requires enough CPU resources to perform in a satisfying fashion. For example, lurker runs fine on a [raspberry pi 5](https://www.raspberrypi.com/products/raspberry-pi-5/).
  - Lurker requires a recording device available to the host machine. On debian systems, check available devices with `ls -lh /dev/snd`.
  - Optionally: A speaker for playing sounds as feedback to speech inputs.
- The "tiny" openai-whisper model
  - Lurker calls the transcription engine [openai-whisper](https://github.com/openai/whisper) for speech-to-text tasks.
  - In order to run lurker offline after the installation completes, you need to [download](https://github.com/openai/whisper/blob/main/whisper/__init__.py) the model beforehand. Otherwise, the whisper transcription module will download the tiny model on startup.

## Run locally

Download the "tiny" openai whisper model and provide the absolute path to the model via environment variable `LURKER_MODEL`. S
See https://openaipublic.azureedge.net/main/whisper/models/65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9/tiny.pt.

Install the required dependencies from `requirements.txt`.
```commandline
pip install --require-virtualenv -r requirements.txt
```

Then, run the entrypoint.
```sh
python __main__.py
```

You may also pass the option `--lurker-home <path>` to let lurker load configuration and actions from the provided [home path](#lurker-home). Otherwise, lurkers assumes its home at `~/lurker`. 

## Run as docker container
The Dockerfile expects the tiny model at `lurker/models/tiny.pt`.
Build the docker image (~6dock GBEOFin size).
```sh
docker build . --tag lurker:latest
```

Run the container with `docker run lurker:latest` (the image `johannesbuchholz/lurker:latest` is also available on docker hub but may change at any time). 
You will need to expose a sound device of your host machine. Additionally, you probably want to mount proper configuration and actions.
- Sound device: Use [docker option `--device`](https://docs.docker.com/reference/cli/docker/container/run/#device) to expose hardware from the host machine to the docker container.
- Configuration: Use [docker option `-v` or `--mount`](https://docs.docker.com/reference/cli/docker/container/run/#mount) to mount a set of configuration files to the container. Mount configuration to `/lurker/lurker` inside the container.

You may run the docker image in the following way where `${LURKER_HOME}` is a path to your configuration files:
```sh
docker run \
    --device /dev/snd \
    --mount type=bind,source="${LURKER_HOME}",target=/lurker/lurker,readonly \
    -d --rm --name "lurker" \
    lurker:latest
```

## Lurker Home
The lurker home path may contain a configuration file and actions that link key-paragraphs to requests sent to a Hue Bridge.
Per default, the lurker home path is set to `~/lurker` unless specified via command line option `--lurker-home <path>`.

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

All fields under `request` are optional and missing fields are not send the Hue Bridge.

### Configuration parameters
All available configuration parameters are defined here: `src/config.py`

These are the most important variables:
- `LURKER_KEYWORD`: Denotes the key word lurker will react to in order to obtain further instructions.
- `LURKER_HOST`: Denotes the host of the Hue Bridge to send instructions to.
- `LURKER_USER`: Denotes the already registered Hue Bridge user. 
- `LURKER_MODEL`: Denotes the absolute path to an open-ai whisper model that lurker should use instead of downloading one.
- `LURKER_INPUT_DEVICE`: Denotes the device name or substring lurker will use to record sound.
- `LURKER_OUTPUT_DEVICE`: Denotes the device name or substring lurker will use when playing sounds.



# Hue Bridge Specifics

## Hue Bridge API Documentation

https://developers.meethue.com/develop/get-started-2/
