#!/bin/sh

set -e

script_version="0.18.0"

print_help() {
  echo "
  Script to download and install lurker to be run as a python program.

  Performs a python installation. This includes building a virtual environment and installing all required dependencies.
  Running the generated entry point script will run the installed python program.

  Installation sources are placed inside your home directory at ${HOME}/.local/opt/lurker.

  The installation includes
  - downloading lurker source code
  - downloading the speech recognition models (de, en)
  - downloading the sentence embedding model
  - creating an entry point script
  - optionally creating a systemd unit that starts lurker at user login

  Synopsis:
    $(basename "$0")
  "
}

echo
echo "-------------------------------------------------------------------------"
echo "Lurker installer script ${script_version}"
echo "-------------------------------------------------------------------------"
echo

required_tools="mktemp wget git envsubst python tar"

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
lurker_dir="${HOME}/.local/opt/lurker"
install_dir="${lurker_dir}/${script_version}"
echo
echo "# Installation path is ${install_dir}"
mkdir -p "${install_dir}"

# clone repo (first clone to tmp dir and then move to the potentially already existing dir)
tmp_dir="$(mktemp --directory --tmpdir "install-lurker-${script_version}.XXXXXXXXXXXX")/${script_version}"
echo
echo "# Download lurker ${script_version} source code into ${tmp_dir}"
git -c advice.detachedHead=false clone --quiet --depth 1 --branch "v${script_version}" https://github.com/johannesbuchholz/lurker.git "${tmp_dir}"

echo
echo "# Move lurker ${script_version} source code to ${install_dir}"
cp -fr "${tmp_dir}" "${lurker_dir}"

# check python version against the one declared in the downloaded .python-version
required_version="$(cat "${install_dir}/.python-version")"
python_version="$(python --version 2>&1 | cut -d' ' -f2)"
if [ "$(echo "${python_version}" | cut -d. -f1-2)" != "$(echo "${required_version}" | cut -d. -f1-2)" ]; then
  echo "ERROR: Python $(echo "${required_version}" | cut -d. -f1-2).x is required, found ${python_version}"
  exit 1
fi

# download models
# NOTE: models are placed next to the configuration that lurker is started with
models_dir="${install_dir}/lurker/models/onnx"
mkdir -p "${models_dir}"

speech_models="sherpa-onnx-streaming-zipformer-de-kroko-2025-08-06
sherpa-onnx-streaming-zipformer-en-kroko-2025-08-06"

for speech_model in ${speech_models}; do
  speech_model_dir="${models_dir}/${speech_model}"
  speech_model_url="https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/${speech_model}.tar.bz2"
  if [ -f "${speech_model_dir}/tokens.txt" ]; then
    echo
    echo "Model ${speech_model} already exists"
  else
    echo
    echo "# Downloading speech recognition model ${speech_model} to ${speech_model_dir}"
    wget -q --show-progress --progress=bar -O "${models_dir}/${speech_model}.tar.bz2" "${speech_model_url}"
    tar -xjf "${models_dir}/${speech_model}.tar.bz2" -C "${models_dir}"
    rm "${models_dir}/${speech_model}.tar.bz2"
    if [ ! -f "${speech_model_dir}/tokens.txt" ]; then
      echo "ERROR: Expected ${speech_model_dir}/tokens.txt after extracting speech recognition model ${speech_model}"
      exit 1
    fi
  fi
done

embedding_model="paraphrase-multilingual-MiniLM-L12-v2"
embedding_model_dir="${models_dir}/${embedding_model}"
embedding_model_url="https://huggingface.co/sentence-transformers/${embedding_model}/resolve/main"

echo
echo "# Downloading sentence embedding model to ${embedding_model_dir}"
mkdir -p "${embedding_model_dir}"
for embedding_file in tokenizer.json onnx/model_O4.onnx; do
  if [ -f "${embedding_model_dir}/$(basename "${embedding_file}")" ]; then
    echo "File ${embedding_file} already exists"
  else
    wget -q --show-progress --progress=bar -O "${embedding_model_dir}/$(basename "${embedding_file}")" "${embedding_model_url}/${embedding_file}?download=true"
  fi
done

# build python environment
venv_dir="${install_dir}/venv"
echo
echo "# Building python environment at ${venv_dir}"
python -m venv "${venv_dir}"
"${venv_dir}/bin/python" -m pip install -r "${install_dir}/requirements.txt"

LURKER_HOME_DEFAULT="${install_dir}/lurker"

LURKER_CMD="${venv_dir}/bin/python ${install_dir} --lurker-home \${LURKER_HOME}
"

startup_script_path="${install_dir}/run-lurker.sh"
echo
echo "# Placing lurker startup script at ${startup_script_path}"
export LURKER_CMD LURKER_HOME_DEFAULT
# shellcheck disable=SC2016
envsubst '${LURKER_CMD} ${LURKER_HOME_DEFAULT}' < "${install_dir}/lib/run-lurker-template.sh" > "${startup_script_path}"
chmod +x "${startup_script_path}"

echo
echo "Installation is complete."
echo "Lurker is started with the lurker home at ${install_dir}/lurker, adapt the configuration there."
echo "What now? Take a look at ${startup_script_path}"

# create systemd service if possible
systemd_install_script_path="${install_dir}/lib/install-lurker-systemd-unit.sh"
echo
echo "# Running subsequent installer script ${systemd_install_script_path}"
if ! (export LURKER_STARTUP_CMD="/bin/sh -c '${startup_script_path} -m'" && sh "${systemd_install_script_path}"); then
  echo "ERROR: Could not install systemd unit in order to run lurker at system startup"
fi
