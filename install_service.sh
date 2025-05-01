#!/bin/bash
set -e

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root to install the service"
  exit 1
fi

echo "Installing Linux EDR service..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
  echo "Error: 'uv' is required but not found. Please install uv first."
  echo "Visit: https://github.com/astral-sh/uv"
  exit 1
fi

# Create symlink to uv in /usr/bin if it doesn't exist
if [ ! -f /usr/bin/uv ]; then
  echo "Creating symlink for uv in /usr/bin..."
  ln -sf $(which uv) /usr/bin/uv
fi

# Install the Python package in development mode
echo "Installing Linux EDR Python package..."
uv pip install -e .

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