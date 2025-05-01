# Linux EDR

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python Type Checked](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](https://github.com/python/mypy)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Monthly Build](https://github.com/yourusername/linux-edr/actions/workflows/test-and-publish.yml/badge.svg?event=schedule)](https://github.com/yourusername/linux-edr/actions/workflows/test-and-publish.yml)

A lightweight Endpoint Detection and Response (EDR) tool for Linux systems.

## Features

- Non-blocking trace reader for `/sys/kernel/tracing/trace_pipe`
- Thread-safe event aggregation with memory protection
- Process-focused event collection and grouping
- Scheduled summarization and reporting every 15 minutes
- OpenAI integration (gpt-4o-mini) for automated threat analysis
- Configurable output formats (JSON, console)
- Flexible configuration via config.ini
- Type-safe implementation with comprehensive error handling
- Privacy-respecting design (see [Privacy Policy](PRIVACY.md))

## Installation

```bash
# Install from GitHub release
uv pip install git+https://github.com/ParttimeWorks/linux_edr.git@latest

# Or install a specific version
uv pip install git+https://github.com/ParttimeWorks/linux_edr.git@v1.0.0
```

## Usage

```bash
# Basic monitoring with default settings
linux-edr run

# Custom interval and output file
linux-edr run --interval 5 --output events.jsonl

# Using a specific configuration file
linux-edr run --config /etc/linux_edr/custom.ini

# Show current configuration
linux-edr show-config
```

## Data Structure

Linux EDR groups execve events by process name and maintains the full command:

```json
{
  "report_id": "2023-01-01T12:00:00+00:00",
  "window_start": "2023-01-01T11:45:00+00:00",
  "window_end": "2023-01-01T12:00:00+00:00",
  "total": 150,
  "command_counts": {"ls": 50, "cat": 30, "bash": 70},
  "process_events": {
    "ls": ["ls -la /tmp", "ls /home", "ls -l /var/log"],
    "cat": ["cat /etc/passwd", "cat /var/log/syslog"],
    "bash": ["bash -c 'whoami'", "bash /tmp/script.sh"]
  }
}
```

## Configuration

Linux EDR can be configured using a `config.ini` file with the following options:

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

# Path to save JSON reports (empty for no file output)
output_file = 

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
```

## Hierarchical Reporting Architecture

Linux EDR uses a hierarchical reporting system to provide insights at different time scales:

| Level | Coverage            | Name           | Description                                          |
|:-----:|:--------------------|:---------------|:-----------------------------------------------------|
| 1     | 15 minutes          | **Cell**       | Base unit covering a 15-minute interval              |
| 2     | 16 Cells = 4 hours  | **Block**      | Aggregates 16 Cells (4 hours of activity)            |
| 3     | 6 Blocks = 24 hours | **DailyReport**| Consolidates 6 Blocks (full day of activity)         |
| 4     | 7 DailyReports      | **WeeklyReport**| Analyzes 7 daily reports (week-long patterns)       |
| 5     | ~4 WeeklyReports    | **MonthlyReport**| Long-term analysis of approximately 4 weeks        |

This multi-level approach enables:
- Immediate detection of suspicious activity (Cell level)
- Short-term pattern recognition (Block level)
- Daily security posture assessment (DailyReport)
- Weekly trend analysis (WeeklyReport)
- Monthly strategic security reviews (MonthlyReport)

All reports are stored in JSON format under the configured `reports_dir` with subdirectories for each level.

## Systemd Service

Linux EDR can be run as a systemd service:

1. Copy the service file to systemd directory:
   ```bash
   sudo cp linux-edr.service /etc/systemd/system/
   ```

2. Create log directory:
   ```bash
   sudo mkdir -p /var/log/linux-edr
   ```

3. Enable and start the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable linux-edr.service
   sudo systemctl start linux-edr.service
   ```

4. Check service status:
   ```bash
   sudo systemctl status linux-edr.service
   ```

## Automated Analysis

The tool sends process execution data to OpenAI's gpt-4o-mini model for analysis every 15 minutes (configurable). The AI looks for suspicious patterns like:

- Unusual command execution patterns
- Potential privilege escalation attempts
- Data exfiltration attempts
- Unusual network access
- Suspicious file operations

Analysis results are saved alongside the JSON reports with the `.analysis` extension.

## Privacy and System Impact

Linux EDR is designed to be non-invasive and privacy-respecting:

- Only monitors execve syscalls, not file contents or keystrokes
- Stores data locally by default
- Transmits data externally only with explicit configuration
- Uses minimal system resources
- Gracefully handles various error conditions
- See our full [Privacy Policy](PRIVACY.md)

## Error Handling

Linux EDR includes comprehensive error handling to ensure reliable operation:

- Graceful handling of missing trace_pipe (waits for it to become available)
- Proper permission error reporting
- Automatic reopening of trace files if they become unavailable
- Configurable logging levels and rotation
- Thread-safe operations with proper resource cleanup

## Requirements

- Python 3.11 or later
- [uv](https://github.com/astral-sh/uv) (required for all dependency management and installation)
- Linux kernel with ftrace support
- Appropriate permissions to read from trace_pipe (typically root)

## Project Structure

```text
linux-edr/
├── linux_edr/
│   ├── __init__.py
│   ├── cli.py            # Typer-based CLI entrypoint
│   ├── app.py            # Orchestration & lifecycle
│   ├── config.py         # Configuration management
│   ├── trace.py          # Non-blocking ftrace reader
│   ├── aggregator.py     # Event aggregation & buffering
│   ├── summary.py        # Summary & statistics builder
│   ├── reporter.py       # OpenAI + file/HTTP outputs
│   └── models.py         # Pydantic data models
├── tests/                # pytest unit & integration tests
├── docs/                 # MkDocs site
├── linux-edr.service     # Systemd service file
├── pyproject.toml        # Build metadata & entry point
├── PRIVACY.md            # Privacy policy
└── README.md             # Project overview & badges
```

## Development

### Setup

```bash
git clone https://github.com/ParttimeWorks/linux_edr.git
cd linux-edr
uv pip install -e .[dev]
```

### Testing

```bash
pytest
```

### Type Checking

```bash
mypy linux_edr
```

## License

MIT 