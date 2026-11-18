#!/bin/sh

print_help() {
  echo "
  Script to launch lurker.

  At startup, lurker will look for configuration in the provided lurker home directory.
  This script launches lurker using the lurker home directory of the installation.
  Option flag -m additionally overlays configuration and plugins from removable media.

  Usage: $(basename "$0") [-m]
    -m  Additionally use the first match of directory 'lurker' found in /media as an overlay home.
        This overlays configuration and plugins on top of the installation's lurker home.
        If no such directory could be found, the installation's lurker home directory is used as before.
        Use this option if you want to change configuration without accessing files directly on the host machine.

  Version ${script_version}
  "
}

find_lurker_home_in_media() {
  find "/media" -maxdepth 3 -type d -name lurker 2>/dev/null | head -1
}

set -e

script_version="0.20.0"

MEDIA_LURKER_HOME=""

while getopts ':m' opt; do
  case "${opt}" in
    m)
      MEDIA_LURKER_HOME=$(find_lurker_home_in_media);;
    ?)
      echo "Unknown option: '$1'" && print_help
      exit 1;;
  esac
done

LURKER_HOME="${LURKER_HOME_DEFAULT}"

echo "# Determined lurker home on host machine: ${LURKER_HOME}"

if [ -n "${MEDIA_LURKER_HOME}" ]; then
  echo "# Determined overlay home on removable media: ${MEDIA_LURKER_HOME}"
  ${LURKER_CMD} run --lurker-home "${LURKER_HOME}" --overlay-home "${MEDIA_LURKER_HOME}"
else
  ${LURKER_CMD} run --lurker-home "${LURKER_HOME}"
fi
