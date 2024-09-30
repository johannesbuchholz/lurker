#!/bin/sh

# Script to download and install lurker to be run as a python programm.
# This includes
#   - downloading lurker source code from https://github.com/johannesbuchholz/lurker.git to ~/lurker
#   - creating entry point scripts and configuration at ~/lurker

set -e

script_version="0.6.3"

echo
echo "--------------------------------------------------"
echo "Lurker installer script PYTHON ${script_version}"
echo "--------------------------------------------------"

echo
echo "# Checking for required tools"
if ! type "pip" "python" "envsubst" "git" "mktemp" "wget"; then
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
tmp_dir="$(mktemp --directory --tmpdir "install-lurker-python-${script_version}.XXXXXXXXXXXX")/${script_version}"
echo "# Download lurker ${script_version} source code into ${tmp_dir}"
git -c advice.detachedHead=false clone --quiet --depth 1 --branch "v${script_version}" https://github.com/johannesbuchholz/lurker.git "${tmp_dir}"

echo "# Move lurker ${script_version} source code to ${install_dir}"
cp -fr "${tmp_dir}" "${lurker_dir}"

# create configuration templates if not yet present
echo "# Creating configuration templates if not yet present at ${lurker_dir}"
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

# build python environment
venv_dir="${install_dir}/venv"
echo
echo "# Building python environment at ${venv_dir}"
python -m venv "${venv_dir}"
"${venv_dir}/bin/pip" install -r "${install_dir}/requirements.txt"

# create startup script
startup_script_path="${install_dir}/run_lurker.sh"
echo
echo "# Placing lurker startup script at ${startup_script_path}"
export PYTHON_CMD="${venv_dir}/bin/python ${install_dir}"
export MODEL_PATH="${model_path}"
#   shellcheck disable=SC2016
envsubst '${PYTHON_CMD} ${MODEL_PATH}' < "${install_dir}/lib/startup_template_python.sh" > "${startup_script_path}"

# Create systemd service if possible
systemd_install_script_path="${install_dir}/lib/install_lurker_systemd_unit.sh"
echo "# Running subsequent installer script ${systemd_install_script_path}"
if ! (export LURKER_STARTUP_SCRIPT="${startup_script_path}" && sh "${systemd_install_script_path}"); then
  echo "ERROR: Could not install systemd unit in order to run lurker at system startup"
fi

echo
echo "Installation is complete."
echo "What now? Preparing fitting configuration and take a look at ${startup_script_path}."
