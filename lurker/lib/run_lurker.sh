#!/bin/sh

print_help() {
  echo "This is a convenience script to launch lurker."
  echo
  echo "Usage: $(basename "$0") [-dm]"
  echo "  -d  Run lurker as docker image assuming the existence of 'lurker:${script_version}'."
  echo "      If not set, runs lurker directly assuming existence of '/usr/bin/python3.9'."
  echo "  -m  Use first match of directory 'lurker' found in /media as LURKER_HOME."
}

find_lurker_home_in_media() {
  find "/media" -maxdepth 3 -type d -name lurker 2>/dev/null | head -1
}

set -e

script_version="0.5.2"

if [ -z "$1" ]; then
  print_help
  exit 0
fi

while getopts ':mds' opt; do
  case "${opt}" in
    m)
      MEDIA_LURKER_HOME=$(find_lurker_home_in_media);;
    d)
      DOCKER=1;;
    ?)
      echo "Unknown option: '$1'" && print_help
      exit 1;;
  esac
done

HOST_LURKER_HOME="${MEDIA_LURKER_HOME:-${HOME}/lurker}"

echo "# Determined lurker home on host machine: ${HOST_LURKER_HOME}"

if [ -z "${DOCKER}" ]; then
  echo "# Run lurker"
  /usr/bin/python3.9 . --lurker-home "${HOST_LURKER_HOME}"
else
  image_to_use="${LURKER_IMAGE:-lurker:${script_version}}"
  echo "# Run lurker docker image: ${image_to_use}"
  docker run \
      --device /dev/snd \
      --mount type=bind,source="${HOST_LURKER_HOME}",target=/lurker/home,readonly \
      -d --rm --name "lurker" \
      "${image_to_use}"
fi

