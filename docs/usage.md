# Usage

The Linux EDR tool can be run directly using the Python module.

## Running the Monitor

```bash
# Basic monitoring with default settings (requires root)
sudo uv run python -m linux_edr.cli run

# Custom 5-minute reporting interval and save reports to a file
sudo uv run python -m linux_edr.cli run --interval 5 --output /var/log/linux-edr-events.jsonl

# Use a specific configuration file
sudo uv run python -m linux_edr.cli run --config /etc/linux_edr/my_config.ini
```

## Viewing Configuration

To see the effective configuration (after loading defaults, file settings, and command-line overrides):

```bash
sudo uv run python -m linux_edr.cli show-config

# View configuration based on a specific file
sudo uv run python -m linux_edr.cli show-config --config /etc/linux_edr/my_config.ini
```

## Running as a Systemd Service

Linux EDR can be run as a systemd service for continuous background monitoring:

1.  **Copy the service file:**
    ```bash
    sudo cp linux-edr.service /etc/systemd/system/
    ```
    *(Note: The service file is configured to use `uv run python -m linux_edr.cli run` command)*

2.  **Create log directory** (if needed by your service configuration):
    ```bash
    sudo mkdir -p /var/log/linux-edr
    sudo chown <user>:<group> /var/log/linux-edr # Adjust user/group as needed
    ```

3.  **Ensure uv is installed system-wide and available at /usr/bin/uv:**
    ```bash
    sudo ln -sf $(which uv) /usr/bin/uv # Create symlink if necessary
    ```

4.  **Reload systemd, enable and start the service:**
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable linux-edr.service
    sudo systemctl start linux-edr.service
    ```

5.  **Check service status:**
    ```bash
    sudo systemctl status linux-edr.service
    ```

6.  **View service logs:**
    ```bash
    sudo journalctl -u linux-edr.service -f
    ``` 