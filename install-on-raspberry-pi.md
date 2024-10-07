# Run lurker on a raspberry pi
Running the lurker python project directly on a raspberry pi may be difficult depending on the existence of a suiting python version (3.9 to 3.11).
Therefor, setting up a Dockerfile to collect all necessary dependencies seems reasonable instead of crafting a fitting python environment locally.   

The following recipe takes you through the process of adding the required system tools and lets you build and run a lurker.
There are two alternatives:
1. Set up and run lurker as a python programm
2. Build and run lurker inside a docker container

In the following, we assume you are running some debian distribution like [raspberri Pi OS](https://www.raspberrypi.com/software/operating-systems/) with an internet connection already set up.

## Installing basic tools
Start by updating `apt` indexes.

```shell
sudo apt update
```

Install `git`
```shell
sudo apt install git
```

## Configure the system
Install udiskie for automatic usb-detection.
> apt install udiskie
 
Create a systemd service unite file `~/.config/systemd/user/udieskie.service` with the following content:
 ```unit file (systemd)
[Unit]
Description=Start udiskie to automount usbdrives
After=default.target

[Service]
ExecStart=/usr/bin/udiskie
Restart=always

[Install]
WantedBy=default.target
```

Configure udiskie to mount drives with read-write access by creating a configfile at `.config/udiskie/udiskie.yaml` with the following content:
```yaml
device_config:
- options: [rw]
```

Enable and start the service
```shell
systemctl --user daemon-reload
systemctl enable --user udieskie.service
systemctl start --user udieskie.service
```

## Prepare lurker configuration

Use the directory `lurker/` from this repository as a starting point and create a directory on an usb stick in the following form
```
lurker
├── actions
│        ├── all_lights_on.json
│        └── all_lights_out.json
└── config.json
```

Be sure to plug in a sound input device and set some unique part of its name in `config.json` under `LURKER_INPUT_DEVICE` and `LURKER_OUTPUT_DEVICE`.
To get an idea what devices are currently plugged in, run `ls /dev/snd/by-id`. for more about sound devices on linux, see https://wiki.archlinux.org/title/Advanced_Linux_Sound_Architecture.

## Alternative 1: Run lurker as a python programm

We assume, you already have installed a suiting python version.

### Install required tools

Install `pip3`
> sudo apt install python3-pip

install `libportaudio2`
> sudo apt install libportaudio2

### Set up python environment

Clone lurker
> git clone https://github.com/johannesbuchholz/lurker.git

Change directory to the freshly downloaded source
> cd lurker

Create virtual environment
> python -m venv venv

Install requirements into virtual environments
> venv/bin/pip install -r --require-venv requirements.txt

Assuming your lurker configuration lies in `~/lurker`, run the python programm with the following command
> venv/bin/python . --lurker-home ${HOME}/lurker

## Alternative 2: Run lurker as a docker image

### Install docker

Install debian docker as described in https://docs.docker.com/engine/install/debian/

For example, use the convenience script (be aware of the downsides mentioned on the above website):
 ```shell
 curl -fsSL https://get.docker.com -o get-docker.sh
 sudo sh ./get-docker.sh --dry-run
 sudo sh ./get-docker.sh
 ```

Add user to docker group
 ```shell
 newgrp docker
 sudo usermod -aG docker $USER
 docker info
 ```

### Build the docker image

Clone lurker
> git clone https://github.com/johannesbuchholz/lurker.git

Download openai-whisper model from the url provided in whisper source code
> wget -q --show-progress --progress=bar -O tiny.pt https://openaipublic.azureedge.net/main/whisper/models/65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9/tiny.pt
   
Build the docker image. This will take some time and about 6GB of disk space.
> docker build --tag lurker:latest lurker/

Assuming your lurker configuration lies in `~/lurker`, run the docker image with the following command
```shell
export LURKER_HOME=${HOME}/lurker && docker run \
--device /dev/snd \
--mount type=bind,source="${LURKER_HOME}",target=/lurker/home,readonly \
-d --rm --name "lurker" \
lurker:latest
```
