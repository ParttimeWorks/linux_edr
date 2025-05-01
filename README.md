# Linux EDR

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python Type Checked](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](https://github.com/python/mypy)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Documentation](https://github.com/ParttimeWorks/linux_edr/actions/workflows/docs.yml/badge.svg)](https://github.com/ParttimeWorks/linux_edr/actions/workflows/docs.yml)

A lightweight yet comprehensive Endpoint Detection and Response (EDR) solution for Linux systems that monitors command execution, analyzes system behavior, and provides actionable security insights with minimal performance impact.

## Overview

Linux EDR captures process execution data through Linux's kernel tracing capabilities and builds a multi-tiered reporting structure that allows for both real-time threat detection and long-term security trend analysis. By focusing on command execution patterns, it provides valuable security insights without the overhead of traditional EDR solutions.

## Key Features

- **Efficient Monitoring**: Non-blocking trace reader for `/sys/kernel/tracing/trace_pipe` with automatic recovery
- **Scalable Architecture**: Thread-safe event buffer with configurable capacity and age limits
- **Smart Data Organization**: Process-focused event collection and intelligent command grouping
- **Hierarchical Reporting**: Tiered reports from 15-minute snapshots to monthly trend analysis
- **AI-Enhanced Security**: OpenAI integration with gpt-4o-mini for automated threat detection
- **Flexible Output**: Configurable reporting to JSON files or console
- **Production-Ready**: Comprehensive error handling with graceful recovery from failures
- **Privacy-Focused**: Collects only necessary command execution data (see [Privacy Policy](PRIVACY.md))

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

Linux EDR groups execve events by process name and maintains the full command line for context:

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

Linux EDR implements a sophisticated multi-tiered reporting system that provides security visibility across different time scales:

| Level | Coverage            | Name           | Description                                          |
|:-----:|:--------------------|:---------------|:-----------------------------------------------------|
| 1     | 15 minutes          | **Cell**       | Base unit capturing immediate system activity        |
| 2     | 16 Cells = 4 hours  | **Block**      | Short-term patterns across multiple Cells            |
| 3     | 6 Blocks = 24 hours | **DailyReport**| Consolidated view of a full day's activity           |
| 4     | 7 DailyReports      | **WeeklyReport**| Week-long trends with daily breakdowns              |
| 5     | ~4 WeeklyReports    | **MonthlyReport**| Strategic view of monthly security posture         |

This architecture enables:
- **Immediate threat detection** at the Cell level
- **Context-rich pattern recognition** at the Block level
- **Daily security posture assessment** in DailyReports
- **Trend identification** in WeeklyReports
- **Strategic security planning** with MonthlyReports

All reports are automatically stored in JSON format in the configured `reports_dir` with appropriate subdirectories for each level.

## Systemd Service

Linux EDR can be deployed as a systemd service for continuous monitoring:

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

## Automated Security Analysis

Linux EDR leverages OpenAI's gpt-4o-mini model to analyze process execution patterns and identify potential security threats. The analysis focuses on:

- Unusual command execution patterns and frequencies
- Potential privilege escalation attempts
- Command sequences indicating data exfiltration
- Anomalous network access patterns
- Suspicious file operations or permission changes

Analysis results are saved alongside JSON reports with the `.analysis` extension, providing actionable insights without requiring manual review of raw data.

## Privacy and System Impact

Linux EDR is designed with privacy and performance in mind:

- Collects only process execution data, not file contents or user input
- Stores data locally by default with configurable retention
- Transmits data externally only when explicitly configured
- Uses non-blocking I/O and efficient buffering to minimize CPU usage
- Implements backpressure mechanisms to handle high-volume events
- See the full [Privacy Policy](PRIVACY.md) for details

## Advanced Error Handling

To ensure reliable operation in production environments, Linux EDR includes:

- Smart retry logic for trace pipe access with configurable backoff
- Graceful handling of permission errors with clear guidance
- Automatic reconnection if trace sources become unavailable
- Thread-safe operations with proper resource management
- Comprehensive logging with configurable verbosity
- Clean shutdown mechanisms that preserve data integrity

## Requirements

- Python 3.11 or later
- [uv](https://github.com/astral-sh/uv) for dependency management
- Linux kernel with ftrace support
- Appropriate permissions to read from trace_pipe (typically requires root)

## Project Structure

```text
linux-edr/
├── linux_edr/
│   ├── __init__.py
│   ├── cli.py            # Typer-based CLI interface
│   ├── app.py            # Core application logic
│   ├── config.py         # Configuration management
│   ├── trace.py          # Non-blocking trace reader
│   ├── aggregator.py     # Thread-safe event buffering
│   ├── summary.py        # Report generation
│   ├── reporter.py       # OpenAI integration and output
│   ├── report_manager.py # Hierarchical report handling
│   └── models.py         # Pydantic data models
├── tests/                # Comprehensive test suite
├── docs/                 # Documentation
├── linux-edr.service     # Systemd service definition
├── pyproject.toml        # Project metadata
├── PRIVACY.md            # Privacy policy
└── README.md             # This file
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