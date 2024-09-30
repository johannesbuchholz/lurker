#!/bin/sh

# Script for creating a systemd unit file that starts lurker at system startup.
# Requires sudo privileges to run.

set -e

script_version="0.6.0"

echo "Lurker systemd unit installer script in order to run lurker at system startup: version ${script_version}"

echo
echo "# Checking for required tools"
if ! type "systemd" "systemctl"; then
  echo "ERROR: systemd is not available"
  exit 1
fi



echo
echo "Continue? (y/n)"
read -r userinput </dev/tty
if [ ! "${userinput}" = "y" ]; then
  exit 0
fi

# Write service unit file
service_name="start-lurker.service"
service_file="/usr/lib/systemd/system/${start-lurker.service}"
echo "Writing service unit file to ${service_file}"

echo "# A systemd unit template that starts lurker on system startup.
# This file has been created in the process of running ${0}.
#
# ${script_version}

[Unit]
Description=Start lurker
After=default.target

[Service]
ExecStart=${LURKER_STARTUP_SCRIPT}

" >> "${service_file}"

# enable service
echo "# Enable service ${service_name}"
systemctl enable "${service_name}"
systemctl status "${service_name}"
