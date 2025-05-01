# Linux EDR Documentation

A lightweight Endpoint Detection and Response (EDR) tool for Linux systems.

## Overview

Linux EDR monitors system activity by reading ftrace events and detecting suspicious patterns. It uses:

- Non-blocking I/O for efficient trace reading
- Thread-safe event aggregation
- Scheduled reporting and summarization
- Optional AI-powered analysis via OpenAI

## Installation

```bash
pip install linux-edr
```

## Quick Start

```bash
# Run with default settings (requires root permissions)
sudo linux-edr run

# Monitor with 5-minute report interval
sudo linux-edr run --interval 5

# Save reports to file
sudo linux-edr run --output /var/log/linux-edr.jsonl
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