#!/bin/sh

# Script for removing the systemd unit file that starts lurker at system startup.

set -e

script_version="0.7.2"

echo
echo "---------------------------------------------------------------"
echo "Lurker uninstaller script ${script_version}: SYSTEMD UNIT"
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

service_name="lurker.service"
user_systemd_unit_dir="${HOME}/.local/share/systemd/user"
service_file="${user_systemd_unit_dir}/${service_name}"

# disable service
echo
echo "# Stopping and removing systemd unit ${service_name}"
systemctl kill --user "${service_name}" || true
systemctl disable --user "${service_name}" || true

# delete service unit file
echo "# Removing service unit file at ${service_file}"
if [ -f "${service_file}" ]; then
  rm "${service_file}"
else
  echo "Could not find service unit file"
fi

echo
echo "Removal of of systemd unit is complete"
