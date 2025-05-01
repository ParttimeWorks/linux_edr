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

# Copy default config and update with OpenAI API key
echo "Installing configuration..."
cp linux_edr/config.ini /etc/linux_edr/

# Prompt for OpenAI API key
echo ""
echo "Please enter your OpenAI API key (press Enter to skip):"
read -r api_key

if [ ! -z "$api_key" ]; then
  # Update the config file with the API key
  echo "Setting OpenAI API key in config file..."
  sed -i "s/^api_key =.*/api_key = $api_key/" /etc/linux_edr/config.ini
  chmod 600 /etc/linux_edr/config.ini
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
echo "Note: The config file permissions are set to 600 to protect the API key" 