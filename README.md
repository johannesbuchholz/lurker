# Lurker
An offline home assistant tool for operating HueBridge smart home things by spoken words.

Currently, only light requests are supported.

Uses offline speech recognition provided by [openai-whisper](https://github.com/openai/whisper).

## Requirements
- Python packages
  - Create a virtual environment and run `pip3 install --require-virtualenv -r requirements.txt`
- Hardware
  - This project has been tested to run fine on a headless RaspberryPi 3B using `Raspberry Pi OS Lite (March 15th 2024)`
  - An active microphone visible as "default" device to the system running this application.

## Run
Running this project for the first time does need an internet connection in order to download the "tiny" model of by openai-whisper. 

To run this programm
```commandline
python3 lurker
```

## Configuration

### Hue Bridge
Configuration is loaded from `~/lurker/config.json` and expect the following file
```json
{
  "host": "<host of hue bridge>",
  "user": "<registered user name>",
  "keyword": "hey bob"
}

```

### Actions
Actions sent to a Hue Bridge instructed by key paragraphs may be configured as separate files at `~/lurker/actions`.
Add one json-file per action in the following form:
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
- `LURKER_HOME`: String. Denotes the path where lurker loads configuration and actions from. Default: `~/lurker`.
- `LURKER_ENABLE_DYNAMIC_CONFIGURATION`: Boolean. If set to "True", lurker will set the application home path to the first attached storage mounted on `/media/<user>/<first_found_device>/lurker`. If no such device could be found, the default LURKER_HOME path is chosen. his is useful when loading configuration from an usb-drive or similar. Default: `False`.
- `LURKER_KEYWORD`: String. Denotes the key word lurker will react to in order to obtain further instructions. Default: `""`.
- `LURKER_SOUND_TOOL`: String. Denotes the sound tool lurker will use when playing sounds. Default: `/usr/bin/aplay`.
- `LURKER_SOUND_TOOL`: String. Denotes the sound tool lurker will use when playing sounds. Default: `/usr/bin/aplay`.
- `KEYWORD_QUEUE_LENGTH_SECONDS`: Float. The number of seconds lurker will buffer input when waiting for the keyword. Higher values increase cpu load.
- `INSTRUCTION_QUEUE_LENGTH_SECONDS`: Float. The number of seconds lurker will buffer input when waiting for an instruction. Higher values increase cpu load.