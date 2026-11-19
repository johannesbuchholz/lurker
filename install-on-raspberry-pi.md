# Run lurker on a Raspberry Pi

Lurker runs as a plain Python program, with no container layer in between. This guide prepares a
Raspberry Pi running a Debian-based distribution such as
[Raspberry Pi OS](https://www.raspberrypi.com/software/operating-systems/) with the system tools,
audio stack, USB automounting, and media configuration that lurker needs.

Install and run lurker with the installer script described in the
[README](README.md#get-lurker). This guide does not repeat the installer steps.

## Installing basic tools

Update the `apt` indexes and install the tools required by the lurker installer and the audio stack:

```shell
sudo apt update
sudo apt install git wget tar gettext python3 python3-venv libportaudio2
```

The installer uses `mktemp`, `wget`, `git`, `envsubst`, `python`, and `tar`. On Debian, `envsubst` is
provided by `gettext`, and `python3-venv` provides `python -m venv`. Make sure the `python` command
points to Python 3.11 or newer; install `python-is-python3` if `python` is not available.
`libportaudio2` is required by `sounddevice`.

## Configure the system

Install [udiskie](https://github.com/coldfix/udiskie) for automatic USB storage detection:

```sh
sudo apt install udiskie
```

Create the configuration directories and a systemd user service at
`~/.config/systemd/user/udiskie.service`:

```sh
mkdir -p ~/.config/systemd/user ~/.config/udiskie
```

```unit file (systemd)
[Unit]
Description=Automount USB storage devices
After=default.target

[Service]
ExecStart=/usr/bin/udiskie
Restart=always

[Install]
WantedBy=default.target
```

Configure udiskie to mount drives with read-write access by creating
`~/.config/udiskie/udiskie.yaml`:

```yaml
device_config:
  - options: [rw]
```

Enable and start the service:

```shell
systemctl --user daemon-reload
systemctl --user enable --now udiskie.service
```

## Prepare lurker configuration

Use the `lurker/` directory from this repository as a starting point and create a home directory on
portable media in this form:

```text
lurker/
├── config.json
└── plugins/
    └── config/
        ├── lights.json
        └── shutdown.json
```

The media home is an overlay. The installation's base home still provides the models and any plugins
that the overlay does not replace. `plugins/config/lights.json` overrides the lights plugin
configuration, for example:

```json
{"backend": "hue", "host": "<host of hue bridge>", "user": "<registered user name>"}
```

`plugins/config/shutdown.json` overrides the shutdown trigger, for example:

```json
{"trigger": "einfach mal abschalten"}
```

Plug the sound device into the Raspberry Pi and set a unique part of its name in `config.json` under
`LURKER_INPUT_DEVICE` and `LURKER_OUTPUT_DEVICE`. To inspect the connected devices, run
`ls /dev/snd/by-id` or `arecord -l`. For more information about sound devices on Linux, see the
[ALSA documentation](https://wiki.archlinux.org/title/Advanced_Linux_Sound_Architecture).

## Install lurker

Install lurker with the installer script described in the [README](README.md#get-lurker).

## Run

After installation, start lurker with the generated `run-lurker.sh` script. Option `-m` additionally
overlays configuration and plugins from the first `lurker` directory found on a device mounted under
`/media`. See the [README](README.md#lurker-home) for the installed paths and overlay behavior.

## Start lurker on system startup

Accept the installer's systemd prompt if you want lurker to start when the user logs in. Afterward,
check the service with:

```sh
systemctl --user status lurker.service
```
