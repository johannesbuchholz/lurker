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
