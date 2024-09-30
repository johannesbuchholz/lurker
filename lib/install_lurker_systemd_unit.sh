#!/bin/sh

# Script for creating a systemd unit file that starts lurker at system startup.

set -e

script_version="0.6.6"

echo
echo "---------------------------------------------------------------"
echo "Lurker installer script SYSTEMD UNIT ${script_version}"
echo "---------------------------------------------------------------"

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
user_systemd_unit_dir="${HOME}/.config/systemd/system/"
mkdir -p "${user_systemd_unit_dir}"
service_file="${user_systemd_unit_dir}/${start-lurker.service}"
echo
echo "# Writing service unit file to ${service_file}"

echo "# A systemd unit template that starts lurker on system startup.
# This file has been created in the process of running ${0}.
#
# ${script_version}

[Install]
WantedBy = multi-user.target

[Unit]
Description=Start lurker
After=multi-user.target

[Service]
ExecStart=${LURKER_STARTUP_SCRIPT}

" > "${service_file}"

# enable service
echo "# Enable service ${service_name}"
systemctl enable --user "${service_name}"
systemctl status "${service_name}"

echo "Installation of systemd unit is complete"
