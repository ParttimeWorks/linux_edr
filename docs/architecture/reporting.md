# Hierarchical Reporting Architecture

Linux EDR implements a sophisticated multi-tiered reporting system that provides security visibility across different time scales. This allows for analysis ranging from immediate, granular events to long-term strategic trends.

## Reporting Levels

The system aggregates data progressively through the following levels:

| Level | Coverage            | Name           | Source Components         | Description                                          |
|:-----:|:--------------------|:---------------|:--------------------------|:-----------------------------------------------------|
| 1     | 15 minutes          | **Cell**       | 1 Event Snapshot          | Base unit capturing immediate system activity        |
| 2     | 16 Cells = 4 hours  | **Block**      | 16 Cells                  | Short-term patterns across multiple Cells            |
| 3     | 6 Blocks = 24 hours | **DailyReport**| 6 Blocks                  | Consolidated view of a full day's activity           |
| 4     | 7 DailyReports      | **WeeklyReport**| 7 DailyReports            | Week-long trends with daily breakdowns              |
| 5     | ~4 WeeklyReports    | **MonthlyReport**| Approx. 4 WeeklyReports   | Strategic view of monthly security posture         |

*(Default intervals and aggregation counts are configurable in `config.ini`)*

## Benefits

This hierarchical architecture enables:

-   **Immediate Threat Detection**: The `Cell` level provides a near real-time view (default 15 mins) of command executions, allowing for rapid identification of obviously malicious or unusual commands.
-   **Contextual Pattern Recognition**: The `Block` level (default 4 hours) aggregates data to reveal short-term patterns, such as repeated failed login attempts followed by a suspicious command, or unusual process behavior within a limited timeframe.
-   **Daily Security Posture Assessment**: The `DailyReport` consolidates a full day's activity, highlighting the most active processes and commands, and serving as a basis for identifying significant deviations from normal daily operations.
-   **Trend Identification**: The `WeeklyReport` analyzes trends over seven days, making it possible to spot recurring suspicious activities, track the evolution of potential incidents, and calculate weekly risk scores.
-   **Strategic Security Planning**: The `MonthlyReport` offers a high-level, long-term view of the system's security posture, summarizing key activities, risks, and incidents, suitable for strategic reviews and planning security improvements.

## Storage

All generated reports are automatically stored as individual JSON files within the directory specified by `reports_dir` in the configuration. They are organized into subdirectories corresponding to their level (e.g., `reports/cells/`, `reports/blocks/`, etc.). 