# Lurker
An offline home assistant tool for operating HueBridge smart home things by spoken words.

Currently, only light requests are supported.

This project is in a dynamic development state.

## Get lurker
Make sure you meet the [requirements](#requirements).
Lurker may be installed from source either using a raw python installation or by building a docker image through the
installer script. Take a look at `lib/install-lurker.sh` to get familiar with the installation steps.

If you are brave enough, you may directly run one of the following commands.

For a python installation using a virtual environment, use
```sh
wget -q -O - https://raw.githubusercontent.com/johannesbuchholz/lurker/refs/heads/main/lib/install-lurker.sh | sh -s -- -p
```

For a docker installation, use
```sh
wget -q -O - https://raw.githubusercontent.com/johannesbuchholz/lurker/refs/heads/main/lib/install-lurker.sh | sh -s -- -d
```
This is recommended whenever the "pure python setup" does not work for you.

### Run lurker on a Raspberry Pi
When installing on a raspberry pi, you may follow the installation guide at [install-on-rasbian.md](https://github.com/johannesbuchholz/lurker/blob/main/install-on-rasbian.md) for a complete setup of all required tools and secondary configuration.
We tested lurker on a raspberry pi 5 (4GB RAM, but 2GB should also suffice) with pleasant performance.

### Requirements
Regardless of your preferred installation method, lurker will need certain things to be set up beforehand:

- Python [3.9, 3.11)
- Hardware
  - Lurker requires enough CPU resources to perform speech-to-text transcription in a satisfying fashion. For example, lurker runs fine on a [raspberry pi 5](https://www.raspberrypi.com/products/raspberry-pi-5/).
  - Lurker requires a recording device available to the host machine. On debian systems, you may check available devices with commands like `ls -lh /dev/snd`.
  - Optionally: A speaker for playing sounds as feedback to speech inputs.
- The "tiny" [openai-whisper](https://github.com/openai/whisper) model. Technically, you may use any available openai-whisper model. Nonetheless, you should probably stick to the "tiny" model for performance reasons.  
  - In order to run lurker offline after the installation completes, you need to [download](https://github.com/openai/whisper/blob/main/whisper/__init__.py) the desired model beforehand. Otherwise, the whisper transcription module will download the configured model on startup.

## Run the python project

Download the "tiny" openai whisper model and provide the absolute path to the model via environment variable `LURKER_MODEL`.
See https://openaipublic.azureedge.net/main/whisper/models/65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9/tiny.pt.

Install the required dependencies from `requirements.txt`.
```sh
pip install --require-virtualenv -r requirements.txt
```

Then, run the entrypoint.
```sh
python __main__.py
```

You may also pass the option `--lurker-home <path>` to let lurker load configuration and actions from the provided [home path](#lurker-home). Otherwise, lurkers assumes its home at `$HOME/lurker`. 

## Run a docker container
The Dockerfile expects the tiny model at `lurker/models/tiny.pt`.
Build the docker image (approximately 6 GB in size).
```sh
docker build . --tag lurker:latest
```

When running the image, you will need to expose a sound device of your host machine. Additionally, you probably want to mount proper configuration and actions.
- For the sound device: Use [docker option `--device`](https://docs.docker.com/reference/cli/docker/container/run/#device) to expose hardware from the host machine to the docker container.
- For configuration: Use [docker option `-v` or `--mount`](https://docs.docker.com/reference/cli/docker/container/run/#mount) to mount a set of configuration files to the container. Mount configuration to `/lurker/lurker` inside the container.

You may run the docker image in the following way where `${LURKER_HOME}` is a path to your configuration files:
```sh
docker run \
    --device /dev/snd \
    --mount type=bind,source="${LURKER_HOME}",target=/lurker/lurker,readonly \
    -d --rm --name "lurker" \
    lurker:latest
```

## Lurker Home
Per default, the lurker home path is set to `$HOME/lurker` unless specified via command line option `--lurker-home <path>`.
The lurker home should point to a directory containing a [configuration](#configuration-file) file at `$LURKER_HOME/config.json` and [actions](#actions) under the directory `$LURKER_HOME/actions`.

### Configuration file
Lurker may be configured through a config file at `<lurker-home>/config.json`. That [configuration](#configuration-parameters) may be overridden by environment variables.
For an example configuration, hav ea look at `lurker/config.json`.

All available configuration parameters are defined in `src/config.py`.

### Actions
Actions are prepared objects passed to an `ActionHandler` whenever one of the respective key-paragraphs has been recognized in a recorded instruction.
Lurker may be configured to use a custom implementation the ActionHandler-Interface. For that, take a look at `src/config.py` and configuration variable `LurkerConfig.LURKER_HANDLER_MODULE`.

#### Hue Bridge ActionHandler
By default, Lurker uses an ActionHandler-implementation sending light requests to a HueBridge in the local network. 
For examples of how to prepare actions for that Hue-Handler, take a look at the files in `lurker/actions`. 

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

Use the special keyword `ALL` for conveniently affect all available lights:
```json
{
  "keys": ["make it dark"],
  "command": {
    "ALL": {"on":  false}
  }
}
```

For further reading on the hue api, take a look at https://developers.meethue.com/develop/get-started-2/.
