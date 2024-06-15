# Lurker
An offline home assistant tool for operating HueBridge smart home things by spoken words.

Currently, only light requests are supported.

Uses offline speech recognition provided by [openai-whisper](https://github.com/openai/whisper).

## Requirements
- Python packages
  - Create a virtual environment and run `pip3 install --require-virtualenv -r requirements.txt`
- Hardware
  - This project has been tested to run fine on a headless RaspberryPi 2 using `Raspberry Pi OS Lite (March 15th 2024)`
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
  "user": "<registered user name>"
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