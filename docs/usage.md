# Usage

The Linux EDR tool can be run directly using the Python module.

## Running the Monitor

```bash
# Basic monitoring with default settings (requires root)
sudo uv run python -m linux_edr.cli run

# Run in debug mode to see detailed event logs
sudo uv run python -m linux_edr.cli run --debug

# Custom 5-minute reporting interval and save reports to a file
sudo uv run python -m linux_edr.cli run --interval 5 --output /var/log/linux-edr-events.jsonl

# Use a specific configuration file
sudo uv run python -m linux_edr.cli run --config /etc/linux_edr/my_config.ini
```

### Standard Run Mode

When run in standard mode, the tool will:
1. Enable syscall tracing for configured events (execve, fork, clone, connect by default)
2. Initialize the scheduler with the configured interval
3. Start monitoring in the background
4. Display minimal output

Example output:
```
Enabling ftrace event: /sys/kernel/tracing/events/syscalls/sys_enter_execve/enable
Enabling ftrace event: /sys/kernel/tracing/events/syscalls/sys_exit_execve/enable
Enabling ftrace event: /sys/kernel/tracing/events/syscalls/sys_enter_fork/enable
Enabling ftrace event: /sys/kernel/tracing/events/syscalls/sys_exit_fork/enable
Enabling ftrace event: /sys/kernel/tracing/events/syscalls/sys_enter_clone/enable
Enabling ftrace event: /sys/kernel/tracing/events/syscalls/sys_exit_clone/enable
Enabling ftrace event: /sys/kernel/tracing/events/syscalls/sys_enter_connect/enable
Enabling ftrace event: /sys/kernel/tracing/events/syscalls/sys_exit_connect/enable
Successfully enabled 8 syscall trace events
Adding job tentatively -- it will be properly scheduled when the scheduler starts
Linux EDR initialized with interval=15m
Added job "LinuxEDRApp._summarize" to job store "default"
Scheduler started
```

### Debug Run Mode

In debug mode, the tool will:
1. Provide more detailed output during initialization
2. Show each raw event as it's captured
3. Display more information about scheduler operations

This is useful for troubleshooting or understanding what data is being collected.

## Configuration File

Linux EDR uses a `config.ini` file with the following sections and options:

```ini
[DEFAULT]
# Path to the kernel trace_pipe
trace_path = /sys/kernel/tracing/trace_pipe

# Report generation interval in minutes
report_interval = 15

# LLM model to use
model = gpt-4o-mini

# Enable debug logging (true/false)
debug = false

[OPENAI]
# Your OpenAI API key (or leave empty to use environment variable)
api_key = 

[REPORTS]
# Directory to store hierarchical reports
reports_dir = reports

[ADVANCED]
# Maximum number of events to store before generating an interim report
max_events_buffer = 10000

# Maximum number of summary lines to include in LLM prompt
max_summary_lines = 50

# Whether to include raw event data in reports (true/false)
include_raw_events = true 

# Whether to include security findings in reports (true/false)
include_security_findings = true

# Whether to log verbose raw event data in debug mode (true/false)
verbose_debug_logging = true

# Whether to enable syscall tracing (true/false)
enable_syscall_tracing = true

# Comma-separated list of syscalls to trace (enter and exit events will be enabled)
syscalls_to_trace = execve,fork,clone,connect
```

You can customize this file and specify its location using the `--config` parameter when running the tool.

## Viewing Configuration

To see the effective configuration (after loading defaults, file settings, and command-line overrides):

```bash
sudo uv run python -m linux_edr.cli show-config

# View configuration based on a specific file
sudo uv run python -m linux_edr.cli show-config --config /etc/linux_edr/my_config.ini
```

## Running as a Systemd Service

Linux EDR can be run as a systemd service for continuous background monitoring:

### Automated Installation

The easiest way to install Linux EDR as a systemd service is to use the provided installation script:

```bash
# Install Linux EDR as a systemd service (requires root)
sudo ./install_service.sh
```

The script will:
- Create the linux-edr service user
- Set up a virtual environment in /opt/linux-edr
- Create necessary log and configuration directories with proper permissions
- Install the Linux EDR Python package
- Copy and configure the systemd service file
- Prompt for an OpenAI API key (optional)

After installation, start and enable the service:

```bash
sudo systemctl enable linux-edr.service
sudo systemctl start linux-edr.service
```

### Uninstalling the Service

To completely remove Linux EDR, use the uninstallation script:

```bash
# Uninstall Linux EDR and clean up all related files (requires root)
sudo ./uninstall_service.sh
```

The script will:
- Stop and disable the service
- Remove the systemd service file
- Delete the virtual environment
- Clean up log directories and configuration files
- Remove the service user

### Manual Installation (Alternative)

If you prefer to install the service manually:

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