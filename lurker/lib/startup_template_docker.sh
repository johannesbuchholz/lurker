#!/bin/sh

print_help() {
  echo "
  This is a convenience script to launch lurker.

  Runs lurker as a python programm assuming the existence of a python environment with all necessary dependencies.

  At startup, lurker will look for configuration in the provided lurker home directory.
  This script launches lurker to '~/lurker' as its home directory unless using option -m.

  Usage: $(basename "$0") [-m]
    -m  Use first match of directory 'lurker' found in /media to be passed to option '--lurker-home' when starting lurker.
        This is helpful when you want to be able to change configuration without accessing files directly
        on the host machine, for example when running on a raspberry pi or similar devices.
        To make best use of this option, be sure that your storage devices is automatically mounted to /media.
  "
}

find_lurker_home_in_media() {
  find "/media" -maxdepth 3 -type d -name lurker 2>/dev/null | head -1
}

set -e

script_version="0.6.0"

if [ -z "$1" ]; then
  print_help
  exit 0
fi

while getopts ':mds' opt; do
  case "${opt}" in
    m)
      MEDIA_LURKER_HOME=$(find_lurker_home_in_media);;
    ?)
      echo "Unknown option: '$1'" && print_help
      exit 1;;
  esac
done

LURKER_HOME="${MEDIA_LURKER_HOME:-${HOME}/lurker}"

echo "# Determined lurker home on host machine: ${LURKER_HOME}"

image_to_use="${LURKER_IMAGE:-lurker:${script_version}}"
echo "# Run lurker docker image: ${image_to_use}"

docker run \
    --device /dev/snd \
    --mount type=bind,source="${LURKER_HOME}",target=/lurker/home,readonly \
    -d --rm --name "lurker" \
    "${image_to_use}"
