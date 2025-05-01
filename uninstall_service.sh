#!/bin/bash
set -e

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root to uninstall the service"
  exit 1
fi

echo "Uninstalling Linux EDR service..."

# Stop and disable the service if it's running
if systemctl is-active --quiet linux-edr.service; then
  echo "Stopping Linux EDR service..."
  systemctl stop linux-edr.service
fi

if systemctl is-enabled --quiet linux-edr.service 2>/dev/null; then
  echo "Disabling Linux EDR service..."
  systemctl disable linux-edr.service
fi

# Remove the systemd service file
if [ -f /etc/systemd/system/linux-edr.service ]; then
  echo "Removing systemd service file..."
  rm -f /etc/systemd/system/linux-edr.service
  systemctl daemon-reload
fi

# Remove the virtual environment
if [ -d "/opt/linux-edr" ]; then
  echo "Removing virtual environment..."
  rm -rf /opt/linux-edr
fi

# Remove logs
if [ -d "/var/log/linux-edr" ]; then
  echo "Removing log directory and all logs..."
  rm -rf /var/log/linux-edr
fi

# Remove configuration
if [ -d "/etc/linux_edr" ]; then
  echo "Removing configuration directory..."
  rm -rf /etc/linux_edr
fi

# Remove the service user
if id "linux-edr" &>/dev/null; then
  echo "Removing service user..."
  userdel linux-edr
fi

echo "Linux EDR service has been completely uninstalled and all data has been removed."
echo "If you installed any dependencies specifically for this service, you may remove them manually." 