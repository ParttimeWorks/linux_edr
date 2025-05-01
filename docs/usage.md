# Usage

The `linux-edr` command provides the main interface for running and managing the EDR tool.

## Running the Monitor

```bash
# Basic monitoring with default settings (requires root)
sudo linux-edr run

# Custom 5-minute reporting interval and save reports to a file
sudo linux-edr run --interval 5 --output /var/log/linux-edr-events.jsonl

# Use a specific configuration file
sudo linux-edr run --config /etc/linux_edr/my_config.ini
```

## Viewing Configuration

To see the effective configuration (after loading defaults, file settings, and command-line overrides):

```bash
linux-edr show-config

# View configuration based on a specific file
linux-edr show-config --config /etc/linux_edr/my_config.ini
```

## Running as a Systemd Service

Linux EDR can be run as a systemd service for continuous background monitoring:

1.  **Copy the service file:**
    ```bash
    sudo cp linux-edr.service /etc/systemd/system/
    ```
    *(Note: Ensure the `linux-edr.service` file is present in your installation or repository.)*

2.  **Create log directory** (if needed by your service configuration):
    ```bash
    sudo mkdir -p /var/log/linux-edr
    sudo chown <user>:<group> /var/log/linux-edr # Adjust user/group as needed
    ```

3.  **Reload systemd, enable and start the service:**
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable linux-edr.service
    sudo systemctl start linux-edr.service
    ```

4.  **Check service status:**
    ```bash
    sudo systemctl status linux-edr.service
    ```

5.  **View service logs:**
    ```bash
    sudo journalctl -u linux-edr.service -f
    ``` 