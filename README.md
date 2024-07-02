# Lurker
An offline home assistant tool for operating HueBridge smart home things by spoken words.

Currently, only light requests are supported.

Uses offline speech recognition provided by [openai-whisper](https://github.com/openai/whisper).

## Requirements
- Python packages
  - Create a virtual environment and run `pip install --require-virtualenv -r requirements.txt`
- Hardware
  - An active microphone visible as "default" device to the system running this application.

## How to run it
### Run locally
Install the required dependencies from `requirements.txt`.
```commandline
pip install -r requirements.txt
```

Run this programm.
```sh
python lurker
```

### Run as docker container
Build the docker image
```sh
docker build . --tag lurker:local
```

Run the container. You will need to expose a sound device and probably want to mount proper configuration and actions.
- Sound device: Use option `--device` to expose hardware from the host machine to the docker container.
- Configuration: Use option `-v` or `--mount` to mount a set of configuration files to the container. L
Lurker expects the configuration at `$LURKER_HOME/config.json`.
```sh
docker run \
    --device /dev/snd \
    -v /path/to/cfg/config.json:/lurker/home/:ro  \
    -v /path/to/actions:/lurker/home/:ro \
    lurker:local
```

## Configuration

Configuration is loaded from `LURKER_HOME` and expects a .json-File containing key value-pairs of the form `"<lurker env variable>": "<string-value>"`
Example:
```json
{
  "LURKER_HOST": "<host of hue bridge>",
  "LURKER_USER": "<registered user name>",
  "LURKER_KEYWORD": "hey john",
  "LURKER_LOG_LEVEL": "DEBUG"
}
```

### Actions
Actions sent to a Hue Bridge instructed by key paragraphs may be configured as separate files under `$LURKER_HOME/actions/`.
Add one json-file per action. All fields under "request" are optional and only set fields are sent to the Hue Bridge.
Example:
```json
{
  "keys": ["make it bright", "entertain me"],
  "lights": ["ALL"],
  "request": {
    "on": false,
    "bri": 123,
    "hue": 123,
    "sat": 123
  }
}
```

- `"keys"`: An array of instruction paragraphs that are associated with this request.
- `"lights"`: An array of light ids as strings, typically numbers starting from "1". "ALL" will target all available lights.
- `"request"`: The actual light request to be sent to the selected lights.
    - `"on"`: If true, turns the light on else off.
    - `"bri"`: Brightness setting.
    - `"hue"`: Heu setting.
    - `"sat"`: Saturation setting.

### Environment variables
There are a couple of environment variables available for configuring lurkers behaviour.
These are the most important ones:
- `LURKER_HOME`: Denotes the path where lurker loads configuration and actions from. Default: `~/lurker`.
- `LURKER_KEYWORD`: Denotes the key word lurker will react to in order to obtain further instructions. Default: `""`.
- `LURKER_HOST`: Denotes the host of the hue bridge to send instructions to.
- `LURKER_USER`: Denotes the user that is registered user to communicate with. 
- `LURKER_SOUND_TOOL`: Denotes the sound tool lurker will use when playing sounds. Default: `/usr/bin/aplay`.
- `LURKER_LOG_LEVEL`: Denotes the log level used when running lurker.
