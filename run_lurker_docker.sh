#!/bin/sh
# This is a convenience script to launch the lurker docker image with appropriate options to correctly mount
# configuration and expose sound devices of the host machine.
# Example:
#   sh run_lurker_docker.sh /abs/path/to/lurkerhome

set -e

input_host_lurker_home="$1"

host_lurker_home="${input_host_lurker_home:-${HOME}/lurker}"
echo "Determined lurker home on host machine: ${host_lurker_home}"

lurker_image="${LURKER_IMAGE:-johannesbuchholz/lurker:latest}"
echo "Running lurker image: ${lurker_image}"
docker run \
    --device /dev/snd \
    --mount type=bind,source="${host_lurker_home}",target=/lurker/home,readonly \
    "${lurker_image}"
