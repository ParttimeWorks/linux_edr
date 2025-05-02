# Architecture Overview

Linux EDR is designed with a modular and robust architecture to handle real-time event processing and reporting efficiently. The system follows Clean Architecture principles to ensure maintainability, testability, and separation of concerns.

## Clean Architecture

The system is organized into four primary layers:

- **Domain**: Core business logic and entities
- **Application**: Application-specific business rules and use cases
- **Infrastructure**: External systems implementations
- **Interfaces**: Entry points to the system

For more details, see the [Clean Architecture](clean-architecture.md) page.

## Core Components

### Domain Layer

- **Models**: Defines the structure of events and reports using Pydantic, ensuring data consistency and validation. Includes a base `BaseSyscallEvent` and specific models for traced syscalls (e.g., `ExecveEvent`, `ForkEvent`).

### Application Layer

- **Services**: Stateless services that implement business rules
- **Use Cases**: Orchestrates business processes and workflows

### Infrastructure Layer

- **Repositories**: Data access implementations
- **Trace Reader**: Uses non-blocking I/O (`selectors`) to read from the kernel's `trace_pipe` without impacting system performance. Includes robust error handling and automatic reconnection logic.
- **Aggregator**: A thread-safe buffer (`deque`) that collects events from the trace reader. Implements backpressure using a maximum length and optional event age limits.
- **Reporter**: Handles the output of reports, including saving to JSON files and sending data to OpenAI for analysis.

### Interfaces Layer

- **Controllers**: Handle incoming requests from CLI or other interfaces
- **CLI**: Provides the command-line interface using Typer.

### Legacy Components

- **Report Manager (`report_manager.py`)**: Orchestrates the creation, storage, and aggregation of hierarchical reports (Cells, Blocks, Daily, Weekly, Monthly). Manages the lifecycle of reports based on time and event counts.
- **Summary (`summary.py`)**: Contains logic for building the initial summary reports (Cells) from aggregated events.
- **Application (`app.py`)**: The main application class that initializes components, manages the scheduler (using `APScheduler`), and orchestrates the event processing pipeline.
- **Configuration (`config.py`)**: Loads and provides access to configuration settings from `config.ini` files.

## Data Flow

1. The `TraceReader` continuously reads raw event strings from the kernel trace pipe.
2. The `TraceReader` attempts to parse known syscall event lines (e.g., execve, fork, connect) into corresponding Pydantic models (`ExecveEvent`, `ForkEvent`, etc.). Unparsed lines are yielded as raw strings.
3. Parsed event models (or raw strings if parsing fails) are passed to the `Aggregator`, which buffers them.
4. A background scheduler triggers the report generation process at the configured interval.
5. The reporting process retrieves a snapshot of buffered events (now structured models) from the `Aggregator`.
6. A Level 1 `Cell` report is created from the event snapshot.
7. The `Cell` is passed to the `ReportManager`.
8. The `ReportManager` saves the `Cell` and checks if enough Cells exist to create a Level 2 `Block`. This process continues up the hierarchy (Daily, Weekly, Monthly).
9. The `Reporter` can optionally save the initial `Cell` report to a JSON file and send it to OpenAI for analysis.
10. Higher-level reports (Blocks, etc.) can also be configured for AI analysis via the `ReportManager` interacting with the `Reporter`.

## Project Structure

```text
linux-edr/
├── linux_edr/                   # Main source code package
│   ├── domain/                  # Core business logic
│   │   └── models/              # Domain entities and value objects
│   │       └── events/          # Pydantic models for specific syscall events
│   ├── application/             # Application-specific business rules
│   │   ├── services/            # Stateless operations
│   │   └── use_cases/           # Business processes
│   ├── infrastructure/          # External systems implementations
│   │   └── repositories/        # Data access implementations
│   ├── interfaces/              # Entry points to the system
│   │   └── controllers/         # Input adapters (CLI, API controllers)
│   ├── app.py                   # Core application logic (legacy)
│   ├── config.py                # Configuration management (legacy)
│   ├── trace.py                 # Non-blocking trace reader & parser
│   ├── aggregator.py            # Thread-safe event buffering
│   ├── summary.py               # Initial report generation (legacy)
│   ├── reporter.py              # OpenAI integration & report output
│   ├── report_manager.py        # Report management (legacy)
│   ├── models.py                # Pydantic data models (legacy - to be removed/merged)
│   └── cli.py                   # CLI interface (legacy)
├── tests/                       # Comprehensive test suite
├── docs/                        # Documentation source files
├── .github/                     # GitHub Actions workflows
│   └── workflows/
│       └── docs.yml             # Documentation deployment workflow
├── linux-edr.service            # Systemd service definition
├── pyproject.toml               # Project metadata and dependencies
├── mkdocs.yml                   # MkDocs configuration
├── PRIVACY.md                   # Privacy policy
└── README.md                    # Repository README
``` 