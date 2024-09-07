#!/bin/sh
# This is a convenience script to launch the lurker docker image with appropriate options to correctly mount
# configuration and expose sound devices of the host machine.
# Example:
#   export LURKER_USE_HOST_MEDIA=t && sh run_lurker_docker.sh

find_lurker_home_in_media() {
  # use -mindepth and -maxdepth to exclude the root directory
  find "/media" -maxdepth 4 -type d -name lurker 2>/dev/null | head -1
}

set -e

media_lurker_home="${LURKER_USE_HOST_MEDIA:+$(find_lurker_home_in_media)}"
host_lurker_home="${media_lurker_home:-${HOME}/lurker}"

echo "Determined lurker home on host machine: ${host_lurker_home}"

lurker_image="${LURKER_IMAGE:-lurker:latest}"
echo "Running lurker image: ${lurker_image}"
docker run \
    --device /dev/snd \
    --mount type=bind,source="${host_lurker_home}",target=/lurker/home,readonly \
    "${lurker_image}"
