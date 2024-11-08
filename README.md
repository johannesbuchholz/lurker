# Lurker
An offline home assistant tool for handling predefined instructions by spoken words.
By default, lurker is configured to instruct a [HueBridge](https://www.philips-hue.com/en-us/p/hue-bridge/046677458478#overview) in the local network for controlling lights. 

This project is in a dynamic development state.

## Get lurker
Make sure you meet the [requirements](#requirements).

Lurker may be installed from source by either using a raw python installation or by building a docker image.
Both installation methods are conveniently available through the script at `lib/install-lurker.sh`.

If you are brave enough, you may directly run one of the following commands.

For a python installation using a virtual environment, use
```sh
wget -q -O - https://raw.githubusercontent.com/johannesbuchholz/lurker/refs/heads/main/lib/install-lurker.sh | sh -s -- -p
```

If the raw python setup does not work for you, try a docker installation and use
```sh
wget -q -O - https://raw.githubusercontent.com/johannesbuchholz/lurker/refs/heads/main/lib/install-lurker.sh | sh -s -- -d
```

## Requirements
Regardless of your preferred installation method, lurker requires some hardware features:
- Lurker requires enough CPU resources to perform speech-to-text transcription in a satisfying fashion. For example, lurker runs fine on a [raspberry pi 5](https://www.raspberrypi.com/products/raspberry-pi-5/).
- Lurker requires a recording device available to the host machine. On debian systems, you may check available devices with commands like `ls -lh /dev/snd`.
- Optionally: A speaker for playing sounds as feedback to speech inputs.

In order to run lurker offline once the installation finished, any installation has to download the desired model beforehand. Otherwise, the whisper [transcription module](https://github.com/openai/whisper/blob/main/whisper/__init__.py) will download the configured model during first startup.
Lurker runs quiet well using the tiny [openai-whisper](https://github.com/openai/whisper) model. Technically, you may use any available openai-whisper model. Nonetheless, you should probably stick to the "tiny" model for performance reasons.  
The above-mentioned installer scripts take care of downloading the "tiny" mdoel.

## Run lurker on a Raspberry Pi
When installing on a raspberry pi, you may follow the installation guide at [install-on-raspberry-pi.md](https://github.com/johannesbuchholz/lurker/blob/main/install-on-raspberry-pi.md) for a complete setup of all required tools and secondary configuration.
We tested lurker on a raspberry pi 5 (4GB RAM, but 2GB should also suffice) with pleasant performance.

## Run the python project locally
Download the tiny openai whisper model and provide the absolute path via environment variable `LURKER_MODEL` or by setting said variable in the [configuration file](#configuration-file).
The model is currently available at https://openaipublic.azureedge.net/main/whisper/models/65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9/tiny.pt.

Install the required dependencies from `requirements.txt`.
```sh
pip install --require-virtualenv -r requirements.txt
```

Then, run the entrypoint.
```sh
python __main__.py
```

You may also pass the option `--lurker-home <path>` to let lurker load configuration and actions from the provided [home path](#lurker-home). Otherwise, lurkers assumes its home at `$HOME/lurker`. 

## Run a docker container locally
The Dockerfile expects the tiny model at `lurker/models/tiny.pt`.

Build the docker image (approximately 6 GB in size).
```sh
docker build . --tag lurker:latest
```

When running the image, you will need to expose a sound device of your host machine. Additionally, you probably want to mount proper configuration and [actions](#actions).
- For the sound device: Use [docker option `--device`](https://docs.docker.com/reference/cli/docker/container/run/#device) to expose hardware from the host machine to the docker container.
- For configuration and actions: Use [docker option `-v` or `--mount`](https://docs.docker.com/reference/cli/docker/container/run/#mount) to mount the directory containing configuration and actions to the container. Mount the directory to `/lurker/lurker` inside the container.

For example, you may run the docker image in the following way where `${LURKER_HOME}` is a path to your [lurker-home](#lurker-home):
```sh
docker run \
    --device /dev/snd \
    --mount type=bind,source="${LURKER_HOME}",target=/lurker/lurker,readonly \
    -d --rm --name "lurker" \
    lurker:latest
```

## Lurker Home
The lurker home directory is the place where lurker tries to load configuration and action files.
The [configuration](#configuration-file) file is expected at `$LURKER_HOME/config.json`. [Actions](#actions) are loaded from the subdirectory `$LURKER_HOME/actions`.
Specify the lurker home path via command line option `--lurker-home <path>`. If not specified, lurker assumes `$HOME/lurker` as its home path.

### Configuration file
Lurker may be configured through a config file at `<lurker-home>/config.json`. These properties may also be overridden by environment variables.
For an example configuration, have a look at `lurker/config.json`.

All available configuration parameters are defined and briefly described in `src/config.py`.

### Actions
An action is declared through a single json-file and contains a list of key paragraphs and an associated command.
Commands are arbitrary objects passed to an `ActionHandler` whenever one of the respective key-paragraphs has been recognized in a recorded instruction.
Lurker may be configured to use a custom ActionHandler implementation. For that, take a look at `src/config.py` and property `LurkerConfig.LURKER_HANDLER_MODULE`.

Key-paragraphs may also consist of a regular expressions pattern. In case of a math, the corresponding match object is also passed to the registered handler.

#### Hue Bridge ActionHandler
By default, lurker uses an ActionHandler-implementation sending light requests to a HueBridge in the local network. 
For examples of how to prepare actions for the Hue-Handler, take a look at the files in `lurker/actions`. 

A sample action assigning a specific state to lights with ids `1`, `2` and `4` while turning off light `3` might look like this:
```json
{
  "keys": ["make it bright", "show me the colors"],
  "command": {
    "1,2,4": {"on": true, "bri": 123, "hue": 123, "sat": 123},
    "3": {"on":  false}
  }
}
```

Use the special keyword `ALL` for conveniently affecting all available lights:
```json
{
  "keys": ["make it dark"],
  "command": {
    "ALL": {"on":  false}
  }
}
```

For further reading on the hue api, take a look at https://developers.meethue.com/develop/get-started-2/.
