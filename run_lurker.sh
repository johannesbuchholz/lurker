#!/bin/sh

print_help() {
  echo "This is a convenience script to launch lurker."
  echo
  echo "Usage: $(basename "$0") [-dm]"
  echo "  -d  Run lurker as docker image assuming teh existence of 'lurker:latest'."
  echo "      If not set, runs lurker directly assuming existence of '/usr/bin/python3.9'."
  echo "  -m  Use directory 'lurker' on the first media device found on this machine"
  echo "      as LURKER_HOME (see lurker configuration regarding LURKER_HOME)."
}

find_lurker_home_in_media() {
  find "/media" -maxdepth 3 -type d -name lurker 2>/dev/null | head -1
}

set -e

if [ -z "$1" ]; then
  print_help
  exit 0
fi

while getopts ':md' opt; do
  case "${opt}" in
    m)
      HOST_MEDIA=1;;
    d)
      DOCKER=1;;
    ?)
      echo "Unknown option: '$1'" && print_help
      exit 1;;
  esac
done

echo "REMAINING ARGS: $*"

MEDIA_LURKER_HOME="${HOST_MEDIA:+$(find_lurker_home_in_media)}"
HOST_LURKER_HOME="${MEDIA_LURKER_HOME:-${HOME}/lurker}"

echo "Determined lurker home on host machine: ${HOST_LURKER_HOME}"

if [ -z "${DOCKER}" ]; then
  echo "Run lurker"
  /usr/bin/python3.9 . --lurker-home "${HOST_LURKER_HOME}"
else
  image_to_use="${LURKER_IMAGE:-lurker:latest}"
  echo "Run lurker as docker image: ${image_to_use}"
  docker run \
      --device /dev/snd \
      --mount type=bind,source="${HOST_LURKER_HOME}",toptet=/lurker/home,readonly \
      -d --rm --name "lurker" \
      "${image_to_use}"
fi

