# Architecture Overview

Linux EDR is designed with a modular and robust architecture to handle real-time event processing and reporting efficiently.

## Core Components

-   **Trace Reader (`trace.py`)**: Uses non-blocking I/O (`selectors`) to read from the kernel's `trace_pipe` without impacting system performance. Includes robust error handling and automatic reconnection logic.
-   **Aggregator (`aggregator.py`)**: A thread-safe buffer (`deque`) that collects events from the trace reader. Implements backpressure using a maximum length and optional event age limits.
-   **Report Manager (`report_manager.py`)**: Orchestrates the creation, storage, and aggregation of hierarchical reports (Cells, Blocks, Daily, Weekly, Monthly). Manages the lifecycle of reports based on time and event counts.
-   **Models (`models.py`)**: Defines the structure of events and reports using Pydantic, ensuring data consistency and validation.
-   **Reporter (`reporter.py`)**: Handles the output of reports, including saving to JSON files and sending data to OpenAI for analysis.
-   **Summary (`summary.py`)**: Contains logic for building the initial summary reports (Cells) from aggregated events.
-   **Application (`app.py`)**: The main application class that initializes components, manages the scheduler (using `APScheduler`), and orchestrates the event processing pipeline.
-   **Configuration (`config.py`)**: Loads and provides access to configuration settings from `config.ini` files.
-   **CLI (`cli.py`)**: Provides the command-line interface using Typer.

## Data Flow

1.  The `TraceReader` continuously reads `execve` events from the kernel trace pipe.
2.  Events are passed to the `Aggregator`, which buffers them in a thread-safe manner.
3.  A background scheduler triggers the `_summarize` method in `app.py` at the configured interval (`report_interval`).
4.  `_summarize` retrieves a snapshot of events from the `Aggregator`.
5.  `build_summary` creates a Level 1 `Cell` report from the event snapshot.
6.  The `Cell` is passed to the `ReportManager`.
7.  The `ReportManager` saves the `Cell` and checks if enough Cells exist to create a Level 2 `Block`. This process continues up the hierarchy (Daily, Weekly, Monthly).
8.  The `Reporter` can optionally save the initial `Cell` report to a JSON file (`output_file`) and send it to OpenAI for analysis.
9.  Higher-level reports (Blocks, etc.) can also be configured for AI analysis via the `ReportManager` interacting with the `Reporter`.

## Project Structure

```text
linux-edr/
├── linux_edr/            # Main source code package
│   ├── __init__.py
│   ├── cli.py            # Typer-based CLI interface
│   ├── app.py            # Core application logic
│   ├── config.py         # Configuration management
│   ├── trace.py          # Non-blocking trace reader
│   ├── aggregator.py     # Thread-safe event buffering
│   ├── summary.py        # Initial report generation (Cells)
│   ├── reporter.py       # OpenAI integration and output handling
│   ├── report_manager.py # Hierarchical report management
│   └── models.py         # Pydantic data models
├── tests/                # Comprehensive test suite
├── docs/                 # Documentation source files
├── .github/              # GitHub Actions workflows
│   └── workflows/
│       └── docs.yml      # Documentation deployment workflow
├── linux-edr.service     # Systemd service definition
├── pyproject.toml        # Project metadata and dependencies
├── mkdocs.yml            # MkDocs configuration
├── PRIVACY.md            # Privacy policy
└── README.md             # Repository README
``` 