#!/bin/bash
set -e

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root to install the service"
  exit 1
fi

echo "Installing Linux EDR service..."

# Install the Python package if not already installed
pip show linux-edr > /dev/null 2>&1 || {
  echo "Installing Linux EDR Python package..."
  pip install .
}

# Create log directory
echo "Creating log directory..."
mkdir -p /var/log/linux-edr
chmod 750 /var/log/linux-edr

# Copy service file to systemd directory
echo "Installing systemd service..."
cp linux-edr.service /etc/systemd/system/

# Create default config directory if it doesn't exist
mkdir -p /etc/linux_edr

# Copy default config if it doesn't exist
if [ ! -f /etc/linux_edr/config.ini ]; then
  echo "Installing default configuration..."
  cp linux_edr/config.ini /etc/linux_edr/
fi

# Reload systemd
systemctl daemon-reload

echo "Service installed. To start and enable at boot:"
echo "  systemctl enable linux-edr.service"
echo "  systemctl start linux-edr.service"
echo ""
echo "To check status:"
echo "  systemctl status linux-edr.service"
echo ""
echo "Configuration file is at /etc/linux_edr/config.ini" 