# Run lurker on a raspberry pi
Lurker runs as a plain python program, that is, there is no container layer in between.
The following recipe takes you through the process of adding the required system tools and installing lurker.

Lurker requires a python version as declared in `.python-version`, for example 3.11.

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
Install [udiskie](https://github.com/coldfix/udiskie) for automatic usb-detection.
```sh
apt install udiskie
```

Create a systemd service unit file `~/.config/systemd/user/udieskie.service` with the following content:
 ```unit file (systemd)
[Unit]
Description=Automountic mounting of usb storage devices
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

Use the directory `lurker/` from this repository as a starting point and create a directory on some portable media device in the following form
```
lurker
├── actions
│        ├── all_lights_on.json
│        └── all_lights_out.json
└── config.json
```

Be sure to plug in a sound input device and set some unique part of its name in `config.json` under `LURKER_INPUT_DEVICE` and `LURKER_OUTPUT_DEVICE`.
To get an idea what devices are currently plugged in, run `ls /dev/snd/by-id`. For more information about sound devices on linux, see https://wiki.archlinux.org/title/Advanced_Linux_Sound_Architecture.

## Install lurker

The following steps take you through the manual step-by-step installation process.

### Install required tools

Install `pip3`
```sh
sudo apt install python3-pip
```

install `libportaudio2`
```sh
sudo apt install libportaudio2
```

### Set up the python environment

Run the python installer script

```shell
wget -q -O - https://raw.githubusercontent.com/johannesbuchholz/lurker/refs/heads/main/lib/install-lurker.sh | sh
```

The script creates a virtual environment, downloads the required models to `~/.local/opt/lurker/<version>/lurker/models/onnx` and asks whether to install the systemd service right away.

## Run
The installer script created an entry-point script at `$HOME/.local/opt/lurker/<version>/run-lurker.sh`.
Run that script to launch lurker and optionally enable option `-m` to read configuration from a device mounted at `/media`

## Start lurker on system startup
You may run lurker whenever the user logs in.
Using the installer script, you are asked if you want to install the systemd service right away. 

Alternatively, you may set up automatic startup by creating a systemd service unit file. For this, run the systemd-unit installer script
```shell
export LURKER_STARTUP_CMD && sh lib/install-lurker-systemd-unit.sh
```
where `LURKER_STARTUP_CMD` holds the command to run your lurker installation.

For example, the python installation may be run with 
```shell
$HOME/.local/opt/lurker/<version>/venv/bin/python $HOME/.local/opt/lurker/<version> --lurker-home $HOME/.local/opt/lurker/<version>/lurker
```
