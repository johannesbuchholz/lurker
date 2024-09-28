#!/bin/sh

# Script to download and install the latest lurker version from source.
# This includes
#   - Downloading the latest stable version of lurker from https://github.com/johannesbuchholz/lurker.git to a temporary directory.
#   - Creating entry point scripts and configuration at ~/.lurker

set -e

script_version="0.0.0-PLACEHOLDER"

echo "Lurker installer script: version ${script_version}"

echo
echo "# Checking for required tools"
if ! type "git" "docker" "wget" "mktemp"; then
  echo "ERROR: Not all required tools are installed"
  exit 1
fi

echo
echo "Continue installation? (y/n)"
read  -r userinput
if [ ! "${userinput}" = "y" ]; then
  exit 0
fi

# clone repo
tmp_dir=$(mktemp --directory --dry-run --tmpdir "$(basename "$0").XXXXXXXXXXXX")
echo "# Cloning lurker source code into ${tmp_dir}"
git clone -q https://github.com/johannesbuchholz/lurker.git "${tmp_dir}"

# determine version
lurker_version=$(sh -c "cd ${tmp_dir} && git describe" | tr -d 'v')
echo ">>> Lurker version ${lurker_version}"

# create install dir
install_path="${HOME}/lurker"
echo "# Installation path is ${install_path}"
mkdir -p "${install_path}"

# create lurker home
echo "# Creating programm entry point, install scripts and basic configuration templates"
cp -r "${tmp_dir}/lurker/lib" "${install_path}"
cp -r "${tmp_dir}/lurker/actions" "${install_path}"
cp "${tmp_dir}/lurker/config.json" "${install_path}"

# download whisper model
model_path="${install_path}/model/tiny.pt"
mkdir -p "$(dirname "${model_path}")"
echo "# Downloading openai-whisper model"
wget -nc --show-progress --no-verbose -O "${model_path}" "https://openaipublic.azureedge.net/main/whisper/models/65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9/tiny.pt"

# build docker image
image_tag="lurker:$lurker_version"
echo "# Building docker image $image_tag"
docker build "${tmp_dir}" --build-arg "BUILD_MODEL_PATH=${model_path}" --tag "${image_tag}"

# Create systemd service if possible
echo "Create systemd unit template to start lurker on system startup? You may later do this again by running ${install_path}/install_lurker_systemd_unit.sh"
echo "Continue? (y/n)"
read  -r userinput
if [ "${userinput}" = "y" ]; then
  if ! sh "${install_path}/install_lurker_systemd_unit.sh"; then
    echo "ERROR: Could not install systemd unit for running lurker at system startup"
  fi
fi

echo "Installation is complete"
