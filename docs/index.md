# Welcome to Linux EDR

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
- **Privacy-Focused**: Collects only necessary command execution data (see [Privacy Policy](privacy.md))

## Quick Start

```bash
# Basic monitoring with default settings (requires root permissions)
sudo uv run python -m linux_edr.cli run

# Run in debug mode to see detailed event logs
sudo uv run python -m linux_edr.cli run --debug

# Monitor with custom interval and output file
sudo uv run python -m linux_edr.cli run --interval 5 --output events.jsonl

# Using a specific configuration file
sudo uv run python -m linux_edr.cli run --config /etc/linux_edr/custom.ini

# Show current configuration
sudo uv run python -m linux_edr.cli show-config
```

## Architecture

Linux EDR is built with a modular architecture:

- **trace.py**: Non-blocking trace reader
- **aggregator.py**: Thread-safe event buffer
- **summary.py**: Event summarization
- **reporter.py**: Output generation
- **report_manager.py**: Hierarchical report management
- **app.py**: Application orchestration
- **cli.py**: Command-line interface

### Hierarchical Reporting

Linux EDR implements a sophisticated hierarchical reporting system to analyze system activity at different time scales:

| Level | Coverage            | Name           | Description                                          |
|:-----:|:--------------------|:---------------|:-----------------------------------------------------|
| 1     | 15 minutes          | **Cell**       | Base unit covering a 15-minute interval              |
| 2     | 16 Cells = 4 hours  | **Block**      | Aggregates 16 Cells (4 hours of activity)            |
| 3     | 6 Blocks = 24 hours | **DailyReport**| Consolidates 6 Blocks (full day of activity)         |
| 4     | 7 DailyReports      | **WeeklyReport**| Analyzes 7 daily reports (week-long patterns)       |
| 5     | ~4 WeeklyReports    | **MonthlyReport**| Long-term analysis of approximately 4 weeks        |

#### Benefits of Hierarchical Reporting

1. **Multi-scale Analysis**: Detect both immediate threats and long-term suspicious trends
2. **Reduced Data Storage**: Higher-level reports store aggregated data rather than raw events
3. **Progressive Insights**: Security analysis becomes more strategic at higher levels
4. **Efficient Analysis**: LLM-based analysis is tailored to the appropriate time scale

Each level provides increasingly sophisticated security insights:

- **Cells** (15 min): Immediate detection of suspicious commands
- **Blocks** (4 hours): Short-term patterns and process behavior
- **DailyReports**: Daily security posture and unusual activity detection
- **WeeklyReports**: Weekly trends, incident tracking, and risk scoring
- **MonthlyReports**: Strategic security assessment and recommendations

Reports are stored as JSON files in a hierarchical directory structure in the configured `reports_dir`. 