#!/bin/sh

print_help() {
  echo "
  Script to launch lurker.

  At startup, lurker will look for configuration in the provided lurker home directory.
  This script launches lurker using '~/lurker' as its home directory unless option flag -m is set.

  Usage: $(basename "$0") [-m]
    -m  Use first match of directory 'lurker' found in /media to be passed to option '--lurker-home' when starting lurker.
        If no such directory could be found, defaults to '~/lurker' as lurker home.
        Use this option if you want to change configuration without accessing files directly on the host machine.

  Version ${script_version}
  "
}

find_lurker_home_in_media() {
  find "/media" -maxdepth 3 -type d -name lurker 2>/dev/null | head -1
}

set -e

script_version="0.16.3"

while getopts ':m' opt; do
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

${LURKER_CMD}
