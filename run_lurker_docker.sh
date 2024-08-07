#!/bin/sh
# This is a convenience script to launch the lurker docker image with appropriate options to correctly mount
# configuration and expose sound devices of the host machine.

set -e

get_first_media_device_on_host() {
  # use -mindepth and -maxdepth to exclude the root directory
  find "/media/$(whoami)" -maxdepth 1 -mindepth 1 -type d 2>/dev/null | head -1
}

get_lurker_home_path_on_host() {
  # only use first encountered media device if LURKER_USE_MEDIA_OF_HOST is set and not null
  first_media_device="${LURKER_USE_MEDIA_OF_HOST:+$(get_first_media_device_on_host)}"
  echo "${first_media_device:-${HOME}}/lurker"
}

host_lurker_home=$(get_lurker_home_path_on_host)
echo "Determined lurker home on host machine: ${host_lurker_home}"

lurker_image="${LURKER_IMAGE:-johannesbuchholz/lurker:latest}"
echo "Running lurker image: ${lurker_image}"
docker run \
    --device /dev/snd \
    --mount type=bind,source="${host_lurker_home}",target=/lurker/home,readonly \
    "${lurker_image}"
