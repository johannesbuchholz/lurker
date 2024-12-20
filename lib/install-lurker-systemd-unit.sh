#!/bin/sh

# Script for creating a systemd unit file that starts lurker at system startup.

set -e

script_version="0.18.0"

echo
echo "---------------------------------------------------------------"
echo "Lurker installer script ${script_version}: SYSTEMD UNIT"
echo "---------------------------------------------------------------"
echo

if [ -z "${LURKER_STARTUP_CMD}" ]; then
  echo "Missing required variable LURKER_STARTUP_CMD"
  exit 1
fi

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
service_name="lurker.service"
user_systemd_unit_dir="${HOME}/.config/systemd/user"
mkdir -p "${user_systemd_unit_dir}"
service_file="${user_systemd_unit_dir}/${service_name}"
echo
echo "# Writing service unit file to ${service_file}"
echo "
# A systemd unit template that starts lurker on system startup.
# This file has been created in the process of running ${0}.
#
# ${script_version}

[Install]
WantedBy=default.target

[Unit]
Description=Offline natural speech instruction handler
After=default.target

[Service]
Restart=on-failure
RestartSec=5
ExecStart=${LURKER_STARTUP_CMD}
SuccessExitStatus=SIGKILL
TimeoutStopSec=3
# Wait until eventually installed media-mounting services have mounted device that could contain lurker configuration.
# For better control, remove this line and add a dedicated dependency to the particular service under WantedBy and After.
ExecStartPre=/bin/sleep 5

" > "${service_file}"

# enable service
echo
echo "# Enable service ${service_name}"
systemctl enable --user "${service_name}"

echo
echo "Installation of systemd unit is complete"
