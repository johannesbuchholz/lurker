#!/bin/sh

# Script to download and install lurker to be run as a docker container.
# This includes
#   - downloading lurker source code from https://github.com/johannesbuchholz/lurker.git to ~/lurker
#   - creating entry point scripts and configuration at ~/lurker

set -e

script_version="0.6.7"

print_help() {
  echo "
Script to download and install lurker to be run as either a docker image or as a python programm.

Installation happens from source and is placed inside your home directory at to ~/lurker.

The installation includes
- downloading lurker source code from https://github.com/johannesbuchholz/lurker.git
- downloading the openai-whisper model 'tiny'
- creating an entry point script
- optionally creating a systemd unit that starts lurker at user login.

Synopsis:
  install-lurker.sh -d|-p
  -d  Perform a docker installation. This includes building a lurker docker image from source.
      Running the generated entry point script will run the created image.
  -p  Perform a python installation. This includes building a virtual environment and installing all required dependencies.
      Running the generated entry point script will run the installed python programm.
  Exactly one of the two options must be provided.
"
}

type_docker=""
type_python=""
while getopts ':pd' opt; do
  case "${opt}" in
    p)
      type_python=1;;
    d)
      type_docker=1;;
    ?)
      echo "Unknown option: '$1'" && print_help
      exit 1;;
  esac
done

if [ ${type_docker} -eq ${type_python} ]; then
  echo "Define exactly one installation type: given='$*'"
  print_help
  exit 1
fi

echo
echo "-------------------------------------------------------------------------"
echo "Lurker installer script ${script_version}: ${type_python:+PYTHON}${type_docker:+DOCKER}"
echo "-------------------------------------------------------------------------"

required_tools="mktemp wget git"

if [ ${type_docker} -eq 1 ]; then
  required_tools="${required_tools} docker"
else
  required_tools="${required_tools} envsubst pip python"
fi

echo
echo "# Checking for required tools"
# shellcheck disable=SC2086
if ! type ${required_tools}; then
  echo "ERROR: Not all required tools are installed"
  exit 1
fi

echo
echo "Continue installation? (y/n)"
read -r userinput </dev/tty
if [ ! "${userinput}" = "y" ]; then
  exit 0
fi

# create install dir
lurker_dir="${HOME}/lurker"
install_dir="${lurker_dir}/${script_version}"
echo
echo "# Installation path is ${install_dir}"
mkdir -p "${install_dir}"

# clone repo (first clone to tmp dir and then move to the potentially already existing dir)
tmp_dir="$(mktemp --directory --tmpdir "install-lurker-docker-${script_version}.XXXXXXXXXXXX")/${script_version}"
echo "# Download lurker ${script_version} source code into ${tmp_dir}"
git -c advice.detachedHead=false clone --quiet --depth 1 --branch "v${script_version}" https://github.com/johannesbuchholz/lurker.git "${tmp_dir}"

echo "# Move lurker ${script_version} source code to ${install_dir}"
cp -fr "${tmp_dir}" "${lurker_dir}"

# create configuration templates if not yet present
echo "Creating configuration templates if not yet present at ${lurker_dir}"
cp -nr "${install_dir}/lurker/actions" "${lurker_dir}"
cp -n "${install_dir}/lurker/config.json" "${lurker_dir}"

# download whisper model
model_dir="${install_dir}/lurker/models"
mkdir -p "${model_dir}"
model_path="${model_dir}/tiny.pt"
echo "# Downloading openai-whisper model to ${model_path}"
if [ -f "${model_path}" ]; then
  echo "Model already exists"
else
  wget -q --show-progress --progress=bar -O "${model_path}" "https://openaipublic.azureedge.net/main/whisper/models/65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9/tiny.pt"
fi

# Prepare executable
if [ -n "${type_docker}" ]; then
  # build docker image
  image_tag="lurker:$script_version"
  echo
  echo "# Building docker image $image_tag"
  docker build "${install_dir}" --tag "${image_tag}"
elif [ -n "${type_python}" ]; then
  # build python environment
  venv_dir="${install_dir}/venv"
  echo
  echo "# Building python environment at ${venv_dir}"
  python -m venv "${venv_dir}"
  "${venv_dir}/bin/pip" install -r "${install_dir}/requirements.txt"
else
  echo "Unexpected state: type_docker=$type_docker, type_python=$type_python"
  exit 1
fi

# create startup script
if [ -n "${type_docker}" ]; then
  LURKER_CMD="
  echo \"# Run lurker docker image: lurker:${script_version}\"
  docker run \
      --device /dev/snd \
      --mount type=bind,source=${LURKER_HOME},target=/lurker/home,readonly \
      -d --rm --name \"lurker\" \
      lurker:${script_version}
  "
elif [ -n "${type_python}" ]; then
  LURKER_CMD="
  export LURKER_MODEL=${model_path}
  ${venv_dir}/bin/python ${install_dir} --lurker-home ${LURKER_HOME}
  "
else
  echo "Unexpected state: type_docker=$type_docker, type_python=$type_python"
  exit 1
fi

startup_script_path="${install_dir}/run-lurker.sh"
echo "# Placing lurker startup script at ${startup_script_path}"
export LURKER_CMD
# shellcheck disable=SC2016
envsubst '${LURKER_CMD}' < "${install_dir}/lib/run-lurker-template.sh" > "${startup_script_path}"

# create systemd service if possible
systemd_install_script_path="${install_dir}/lib/install-lurker-systemd-unit.sh"
echo
echo "# Running subsequent installer script ${systemd_install_script_path}"
if ! (export LURKER_STARTUP_SCRIPT="${startup_script_path}" && sh "${systemd_install_script_path}"); then
  echo "ERROR: Could not install systemd unit in order to run lurker at system startup"
fi

echo
echo "Installation is complete."
echo "What now? Prepare fitting configuration and take a look at ${startup_script_path}."
