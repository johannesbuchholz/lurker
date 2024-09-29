#!/bin/sh

# Script for creating a systemd unit file that starts lurker at system startup.
# Requires sudo privileges to run.

set -e

script_version="0.5.2"

echo "Lurker systemd unit installer script: version ${script_version}"

if ! type "systemd" "systemctl"; then
  echo "ERROR: systemd is not available"
  exit 1
fi

echo "# A systemd unit template that starts lurker on system startup.
# This file has been created in the process of running ${0}
# Unit version ${script_version}

[Unit]
Description=Start lurker
After=default.target

[Service]
ExecStart=${HOME}/lurker/run_lurker.sh -d -m

" >> /usr/systemd/system/start-lurker.service

systemctl enable start-lurker.service
systemctl status start-lurker.service
