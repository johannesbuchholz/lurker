# Lurker
An offline home assistant tool for handling predefined instructions by spoken words (english or german).
By default, lurker is configured to instruct a [HueBridge](https://www.philips-hue.com/en-us/p/hue-bridge/046677458478#overview) in the local network to control lights. 

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

0.15.8

2024-11-10 22:45:43,517 [    INFO] Lurker (__main__): Determined lurker home: /media/johannes/INTENSO/lurker
2024-11-10 22:45:43,517 [    INFO] Lurker (__main__): Loaded configuration:
LURKER_LOG_LEVEL=INFO
LURKER_LOG_FILE=lurkerlog
LURKER_INPUT_DEVICE=jabra
LURKER_OUTPUT_DEVICE=jabra
LURKER_KEYWORD=hey john
LURKER_LANGUAGE=de
LURKER_SPEECH_CONFIG={'instruction_queue_length_seconds': 3.0, 'keyword_queue_length_seconds': 1.2, 'min_silence_threshold': 600, 'queue_check_interval_seconds': 0.1, 'speech_bucket_count': 60, 'required_leading_silence_ratio': 0.1, 'required_speech_ratio': 0.15, 'required_trailing_silence_ratio': 0.2, 'ambiance_level_factor': 1.5}
LURKER_HANDLER_MODULE=src.handlers.hue_client
LURKER_HANDLER_CONFIG={'host': '<host of hue bridge>', 'user': '<registered user name>'}
2024-11-10 22:45:43,523 [    INFO] Lurker (src.lurker): Loaded action handler: <class 'src.handlers.hue_client.HueClient'>
2024-11-10 22:45:43,924 [    INFO] Lurker (src.lurker): Initializing...
2024-11-10 22:45:43,951 [    INFO] Lurker (ActionRegistry): Loaded actions: count=4, files=['all_lights_on.json', 'exit.json', 'all_lights_out.json', 'save.json']
2024-11-10 22:45:43,951 [    INFO] Lurker (ActionRegistry): Starting periodic reloading of new or updated actions: location=/media/johannes/INTENSO/lurker/actions, interval_duration_s=5
2024-11-10 22:45:43,952 [    INFO] Lurker (src.sound): Loading sounds
2024-11-10 22:45:44,019 [    INFO] Lurker (src.lurker): Start listening...
2024-11-10 22:45:44,030 [ WARNING] Lurker (src.sound): Could not play sound: No output device matching 'jabra'
2024-11-10 22:45:44,030 [    INFO] Lurker (SpeechToTextListener): Start recording using keyword 'hey john'
```

## Get lurker
Make sure you meet the [requirements](#requirements).

Lurker is installed from source using a raw python installation.
This installation method is conveniently available through the installer script at `lib/install-lurker.sh`.
Each version is installed into `~/.local/opt/lurker/<version>`, holding the source code, the virtual environment and the [lurker home](#lurker-home) with configuration, actions and models.

If you are brave enough, you may directly run the following command.
```sh
wget -q -O - https://raw.githubusercontent.com/johannesbuchholz/lurker/refs/heads/main/lib/install-lurker.sh | sh
```

## Requirements

- Lurker requires enough CPU resources to perform speech-to-text transcription in a satisfying fashion. For example, lurker runs fine on a [raspberry pi 5](https://www.raspberrypi.com/products/raspberry-pi-5/).
- Lurker requires a recording device available to the host machine. On debian systems, you may check available devices with commands like `ls -lh /dev/snd`. In our local setup, we were very happy using a [jabra speak](https://www.jabra.com/business/speakerphones/jabra-speak-series) device.
- Optionally: A speaker for playing sounds as feedback to speech inputs.

Lurker requires multiple onnx model files for speech-to-text recognition and embedders for intent matching.
- Speech: [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) for example `https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-streaming-zipformer-en-kroko-2025-08-06.tar.bz2`
- Embedding: `paraphrase-multilingual-MiniLM-L12-v2` for example `https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2/resolve/main`

- When using the above-mentioned installer script, you do not need to download the models yourself as the script takes care of that.

## Run lurker on a Raspberry Pi
When installing on a raspberry pi, you may follow the installation guide at [install-on-raspberry-pi.md](https://github.com/johannesbuchholz/lurker/blob/main/install-on-raspberry-pi.md) for a complete setup of all required tools and secondary configuration.
We tested lurker on a raspberry pi 5 and 4B (4GB RAM, but 2GB should also suffice) with pleasant performance.

## Run the python project locally
Place the required models as described in [requirements](#requirements) in your [lurker home](#lurker-home), for example `lurker/models/onnx` in this repository.

Install the required dependencies from `requirements.txt`.
```sh
pip install --require-virtualenv -r requirements.txt
```

Then, run the entrypoint.
```sh
python __main__.py
```

You may also pass the option `--lurker-home <path>` to let lurker load configuration and actions from the provided [home path](#lurker-home). Otherwise, lurker assumes its home at `<current directory>/lurker`. 

## Lurker Home
The lurker home directory is the place where lurker tries to load configuration and action files.
The [configuration](#configuration-file) file is expected at `$LURKER_HOME/config.json`. [Actions](#actions) are loaded from the subdirectory `$LURKER_HOME/actions`.
Specify the lurker home path via command line option `--lurker-home <path>`. If not specified, lurker assumes `<current directory>/lurker` as its home path.

The startup script created by the installer script, `$HOME/.local/opt/lurker/<version>/run-lurker.sh`, passes `$HOME/.local/opt/lurker/<version>/lurker` explicitly, or the `lurker` directory found on removable media when started with option `-m`.

### Configuration file
Lurker may be configured through a config file at `<lurker-home>/config.json`. These properties may also be overridden by environment variables.
For an example configuration, have a look at `lurker/config.json`.

All available configuration parameters are defined and briefly described in `src/config.py`.

### Actions
An action is declared through a single json-file and contains a list of key paragraphs and an associated command.
Commands are arbitrary objects passed to an `ActionHandler` whenever one of the respective key-paragraphs has been recognized in a recorded instruction.
Lurker may be configured to use a custom ActionHandler implementation. For that, take a look at `src/config.py` and property `LurkerConfig.LURKER_HANDLER_MODULE`a s well as the base class `src.action.ActionHandler`.

Key-paragraphs may also consist of a regular expressions pattern. To indicate a regex pattern, surround the paragraph with `/` like this: `/.*save as (.*)$/`. 

#### Hue Bridge
Currently, lurker uses HueBridge API version v1.
