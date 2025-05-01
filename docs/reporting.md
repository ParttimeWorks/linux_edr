# Hierarchical Reporting System

Linux EDR implements a multi-level reporting architecture to provide security insights at various time scales, from real-time detection to long-term strategic analysis.

## Reporting Hierarchy

The reporting system is organized into five distinct levels, each building upon the previous one:

| Level | Coverage            | Name           | Storage Life     | Primary Purpose                            |
|:-----:|:--------------------|:---------------|:-----------------|:-------------------------------------------|
| 1     | 15 minutes          | **Cell**       | 4 hours          | Real-time detection and immediate response |
| 2     | 16 Cells = 4 hours  | **Block**      | 24 hours         | Short-term pattern recognition             |
| 3     | 6 Blocks = 24 hours | **DailyReport**| 7 days           | Daily security posture assessment          |
| 4     | 7 DailyReports      | **WeeklyReport**| 1 month         | Weekly trend analysis and incident tracking|
| 5     | ~4 WeeklyReports    | **MonthlyReport**| 1 year         | Strategic security review and planning     |

## Report Types in Detail

### Cell (Level 1)

Cells are the basic building blocks of the reporting system, generated every 15 minutes. Each Cell contains:

- Commands executed during the 15-minute window
- Process execution details
- Raw event data (optional, based on configuration)
- Analysis of immediate security concerns

#### Example Cell JSON Structure

```json
{
  "report_id": "2023-06-01T12:00:00+00:00",
  "window_start": "2023-06-01T11:45:00+00:00",
  "window_end": "2023-06-01T12:00:00+00:00",
  "total": 150,
  "command_counts": {"ls": 50, "cat": 30, "bash": 70},
  "process_events": {
    "ls": ["ls -la /tmp", "ls /home", "ls -l /var/log"],
    "cat": ["cat /etc/passwd", "cat /var/log/syslog"],
    "bash": ["bash -c 'whoami'", "bash /tmp/script.sh"]
  },
  "analysis": "No suspicious activity detected in this time window."
}
```

### Block (Level 2)

Blocks aggregate data from 16 Cells, providing a 4-hour view of system activity. This level helps identify patterns that may not be apparent in a single 15-minute window:

- Aggregated command statistics across 4 hours
- Top processes by execution frequency
- Identification of recurring patterns
- Analysis of potential security concerns over the 4-hour period

#### Example Block JSON Structure

```json
{
  "report_id": "block_20230601_120000",
  "window_start": "2023-06-01T08:00:00+00:00",
  "window_end": "2023-06-01T12:00:00+00:00",
  "total_events": 2400,
  "cells": ["2023-06-01T08:00:00+00:00", "2023-06-01T08:15:00+00:00", "..."],
  "command_counts": {"ls": 800, "cat": 450, "bash": 1150},
  "top_processes": {"bash": 1150, "ls": 800, "cat": 450},
  "analysis": "Elevated use of cat command for viewing sensitive files detected."
}
```

### DailyReport (Level 3)

Daily Reports consolidate 6 Blocks, providing a comprehensive view of activity over a 24-hour period:

- Day-level command and process statistics
- Unusual activity patterns identified
- Day-over-day comparison
- Daily security posture assessment

#### Example DailyReport JSON Structure

```json
{
  "report_id": "daily_20230601",
  "date": "2023-06-01",
  "window_start": "2023-06-01T00:00:00+00:00",
  "window_end": "2023-06-01T23:59:59+00:00",
  "total_events": 14500,
  "blocks": ["block_20230601_040000", "block_20230601_080000", "..."],
  "command_counts": {"ls": 4800, "cat": 2700, "bash": 7000},
  "top_processes": {"bash": 7000, "ls": 4800, "cat": 2700},
  "unusual_activity": [
    {
      "type": "credential_access",
      "commands": ["cat /etc/shadow", "cat /etc/passwd"],
      "timestamp": "2023-06-01T14:23:17+00:00",
      "severity": "high"
    }
  ],
  "analysis": "Potential credential access attempt detected at 14:23. User accessed /etc/shadow file."
}
```

### WeeklyReport (Level 4)

Weekly Reports analyze 7 consecutive Daily Reports, revealing longer-term patterns:

- Weekly command and process trends
- Security incident tracking
- Comparative analysis across days
- Weekly risk assessment score

#### Example WeeklyReport JSON Structure

```json
{
  "report_id": "weekly_20230601_20230607",
  "week_start_date": "2023-06-01",
  "week_end_date": "2023-06-07",
  "total_events": 102400,
  "daily_reports": ["daily_20230601", "daily_20230602", "..."],
  "command_trends": {
    "ls": [4800, 5200, 4900, 5100, 4700, 3200, 4600],
    "cat": [2700, 2500, 2600, 2800, 3100, 2100, 2700]
  },
  "process_trends": {
    "bash": [7000, 7200, 6900, 7100, 7400, 5100, 6800],
    "python": [1200, 1300, 1100, 1400, 1500, 900, 1300]
  },
  "security_incidents": [
    {
      "date": "2023-06-01",
      "type": "credential_access",
      "severity": "high",
      "resolution_status": "investigating"
    }
  ],
  "risk_score": 65,
  "analysis": "Overall elevated risk due to credential access attempt on Jun 1. Consistent usage patterns across the week with expected weekend reduction."
}
```

### MonthlyReport (Level 5)

Monthly Reports provide the highest level of analysis, aggregating approximately 4 Weekly Reports:

- Long-term system usage patterns
- Consolidated security incident summary
- Strategic security recommendations
- Month-over-month trend analysis

#### Example MonthlyReport JSON Structure

```json
{
  "report_id": "monthly_202306",
  "month": "2023-06",
  "start_date": "2023-06-01",
  "end_date": "2023-06-30",
  "total_events": 435000,
  "weekly_reports": ["weekly_20230601_20230607", "weekly_20230608_20230614", "..."],
  "command_summary": {"ls": 85000, "cat": 47000, "bash": 125000},
  "process_summary": {"bash": 125000, "ls": 85000, "python": 23000},
  "security_summary": {
    "total_incidents": 3,
    "high_risk_incidents": 1,
    "medium_risk_incidents": 2,
    "low_risk_incidents": 0
  },
  "risk_score": 45,
  "recommendations": [
    "Implement file access controls for sensitive system files",
    "Review user privileges for accounts accessing /etc/shadow",
    "Enable multi-factor authentication for privileged users"
  ],
  "analysis": "System shows generally consistent usage patterns with expected variations for weekends. One high-risk credential access incident requires attention."
}
```

## Report Generation Process

The reporting system automatically aggregates lower-level reports into higher-level ones:

1. **Cells** are generated every 15 minutes from raw system events
2. When 16 Cells accumulate, a **Block** is automatically created
3. When 6 Blocks are available, a **DailyReport** is generated
4. After 7 DailyReports, a **WeeklyReport** is created
5. Approximately every 4 weeks, a **MonthlyReport** is compiled

## LLM-Enhanced Analysis

Each report level includes AI-powered analysis tailored to the appropriate time scale:

- **Cell Analysis**: Focuses on immediate security concerns
- **Block Analysis**: Identifies short-term suspicious patterns
- **DailyReport Analysis**: Provides daily security posture assessment
- **WeeklyReport Analysis**: Identifies trends and recommends specific actions
- **MonthlyReport Analysis**: Delivers strategic security insights and recommendations

## Configuring the Reporting System

The reporting system is configured via the `config.ini` file:

```ini
[REPORTS]
# Directory to store hierarchical reports
reports_dir = reports
```

Each report type is stored in its own subdirectory:
- `reports/cells/` - Cell reports
- `reports/blocks/` - Block reports
- `reports/daily/` - Daily reports
- `reports/weekly/` - Weekly reports
- `reports/monthly/` - Monthly reports

## Accessing Reports

Reports can be accessed in several ways:

1. Directly from the `reports_dir` directory
2. Via the ReportManager API:
   ```python
   from linux_edr.report_manager import ReportManager
   
   # Initialize report manager
   manager = ReportManager("reports")
   
   # Get a specific report
   daily_report = manager.get_report("daily_20230601", "daily")
   ```

## Report Retention

The system automatically manages report retention, keeping:
- Cells: 4 hours (16 reports)
- Blocks: 24 hours (6 reports)
- Daily Reports: 7 days
- Weekly Reports: 1 month
- Monthly Reports: 1 year

This tiered approach provides both immediate security monitoring and long-term historical analysis while efficiently managing storage requirements. 