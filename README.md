# Lurker
An offline home assistant tool for operating HueBridge smart home things by spoken words.

Currently, only light requests are supported.

Uses offline speech recognition provided by [openai-whisper](https://github.com/openai/whisper).

## Requirements
- Python
  - Tested with python 3.9
  - Install the required dependencies by running `pip install --require-virtualenv -r requirements.txt`
- Hardware
  - An active microphone visible as "default" device to the system running this application.

## How to run it
### Run locally
Install the required dependencies from `requirements.txt`.
```commandline
pip install --require-virtualenv -r requirements.txt
```

Run this programm.
```sh
python lurker
```

### Run as docker container
Requirement: Download teh "tiny" openai whisper model to `misc/models`. See https://openaipublic.azureedge.net/main/whisper/models/65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9/tiny.pt.
Build the docker image (currently takes roughly 5 GB of disc space).
```sh
docker build . --tag lurker:latest
```

Run the container with `docker run johannesbuchholz/lurker:docker`. You will need to expose a sound device and probably want to mount proper configuration and actions.
- Sound device: Use option `--device` to expose hardware from the host machine to the docker container.
- Configuration: Use option `-v` or `--mount` to mount a set of configuration files to the container.

Use the shell-script `run_lurker_docker.sh` to conveniently start the docker container with the possibility to read configuration form removable media.
```sh
sh run_lurker.docker.sh
```

## Configuration

Configuration is loaded from environment variable `LURKER_HOME` and expects a .json-File containing key value-pairs of the form `"<lurker env variable>": "<string-value>"`
Example:
```json
{
  "LURKER_HOST": "<host of hue bridge>",
  "LURKER_USER": "<registered user name>",
  "LURKER_KEYWORD": "hey john",
  "LURKER_LOG_LEVEL": "DEBUG",
  "LURKER_INPUT_DEVICE": "Logitech",
  "LURKER_OUTPUT_DEVICE": "pulse"
}
```

### Actions
Actions are pairs of key paragraphs and a request sent to the Hue Bridge. Such actions may be configured file wise under `${LURKER_HOME}/actions/`.
Add one json-file per action. All fields withing "request" are optional and missing field are not send the Hue Bridge.
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

### Environment variables
There are a couple of environment variables available for configuring lurkers behaviour. For details see `src/config.py`
These are the most important variables:
- `LURKER_HOME`: Denotes the path where lurker loads configuration and actions from. Default: `~/lurker`.
- `LURKER_KEYWORD`: Denotes the key word lurker will react to in order to obtain further instructions. Default: `""`.
- `LURKER_HOST`: Denotes the host of the Hue Bridge to send instructions to.
- `LURKER_USER`: Denotes the already registered Hue Bridge user. 
- `LURKER_LOG_LEVEL`: Denotes the log level used when running lurker.
- `LURKER_INPUT_DEVICE`: Denotes the device name or substring lurker will use to record sound.
- `LURKER_OUTPUT_DEVICE`: Denotes the device name or substring lurker will use when playing sounds.
