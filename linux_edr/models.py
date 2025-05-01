from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator


class CommandLine(BaseModel):
    """A command line execution with arguments."""

    command: str = Field(..., description="Command name")
    args: List[str] = Field(default_factory=list, description="Command arguments")
    pid: int = Field(..., description="Process ID")
    timestamp: str = Field(..., description="Timestamp of execution")

    def to_string(self) -> str:
        """Convert to full command line string representation."""
        if not self.args:
            return self.command
        return f"{self.command} {' '.join(self.args)}"


class ProcessEvents(BaseModel):
    """Collection of command executions grouped by process name."""

    process_name: str = Field(..., description="Process name")
    executions: List[CommandLine] = Field(default_factory=list, description="Command executions")


class SummaryReport(BaseModel):
    """
    Summary report of system activity within a time window.

    Attributes:
        report_id: Unique ID for the report (usually a timestamp)
        window_start: Start time of the monitoring window (ISO format)
        window_end: End time of the monitoring window (ISO format)
        total: Total number of events in the window
        command_counts: Dictionary of command names and their counts
        process_events: Dictionary of process names and their command lines
        raw_events: Optional list of raw event data
    """

    report_id: str = Field(..., description="Unique identifier for this report")
    window_start: str = Field(..., description="Start time of the monitoring window (ISO format)")
    window_end: str = Field(..., description="End time of the monitoring window (ISO format)")
    total: int = Field(..., description="Total number of events captured")
    command_counts: Dict[str, int] = Field(..., description="Count of each command executed")
    process_events: Optional[Dict[str, List[str]]] = Field(
        None, description="Grouped events by process name"
    )
    raw_events: Optional[List[Dict[str, Any]]] = Field(None, description="Raw event data")
    analysis: Optional[str] = Field(None, description="AI analysis of the events")
    severity: Optional[int] = Field(
        None, description="Severity rating (1-5, where 5 is most severe)", ge=1, le=5
    )

    @field_validator("window_start", "window_end")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """Validate that timestamps are in ISO format."""
        try:
            datetime.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError(f"Invalid ISO format timestamp: {v}")

    @field_validator("total")
    @classmethod
    def validate_total(cls, v: int) -> int:
        """Validate that total is non-negative."""
        if v < 0:
            raise ValueError(f"Total events cannot be negative: {v}")
        return v

    def to_prompt(self) -> str:
        """
        Convert report to a prompt for LLM analysis.

        Returns:
            A formatted prompt string for the LLM to analyze
        """
        # Format the command counts section
        commands = "\n".join([f"- {cmd}: {count}" for cmd, count in self.command_counts.items()])

        # Format the process events section if available
        process_section = ""
        if self.process_events:
            sections = []
            for proc_name, cmd_lines in self.process_events.items():
                # Limit to no more than 10 examples per process
                examples = cmd_lines[:10]
                if len(cmd_lines) > 10:
                    examples.append(f"... ({len(cmd_lines) - 10} more executions)")

                proc_details = f"### {proc_name}\n" + "\n".join([f"- `{cmd}`" for cmd in examples])
                sections.append(proc_details)

            # Join all process sections with appropriate spacing
            process_section = "\n\n## Process Details (Sample Commands)\n\n" + "\n\n".join(sections)

        return f"""
# Linux EDR Report ({self.report_id})

**Time Window:** {self.window_start} to {self.window_end}
**Total Events:** {self.total}

## Command Execution Counts
{commands}
{process_section}

---
Analyze the above system activity for security concerns. Identify any suspicious or unusual patterns in command execution. Explain why specific commands might represent security risks.

Your response should be formatted as follows:
1. Summary: A concise summary of the overall security posture during this time period.
2. Security Score: Assign a severity level from 1-5 (where 1 is secure/normal and 5 is critical/severe).
3. Key Findings: List specific suspicious activities or security concerns found.

Include clear reasoning for your severity score.
"""

    def model_dump(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.

        Returns:
            Dictionary representation of the report
        """
        data = super().model_dump()
        # Remove None values for cleaner output
        return {k: v for k, v in data.items() if v is not None}


# New hierarchical report models based on the revised architecture
class Cell(SummaryReport):
    """
    Level 1 report covering a 15-minute window of system activity.
    This is the base unit of the reporting hierarchy.
    """

    pass  # Inherits all attributes from SummaryReport


class Block(BaseModel):
    """
    Level 2 report covering a 4-hour window of system activity.
    Composed of 16 Cells (15-minute intervals).
    """

    report_id: str = Field(..., description="Unique identifier for this block report")
    window_start: str = Field(..., description="Start time of the block window (ISO format)")
    window_end: str = Field(..., description="End time of the block window (ISO format)")
    total_events: int = Field(..., description="Total number of events across all cells")
    cells: List[str] = Field(..., description="List of Cell report IDs included in this block")
    command_counts: Dict[str, int] = Field(
        ..., description="Aggregated count of each command executed"
    )
    top_processes: Dict[str, int] = Field(..., description="Top processes by execution count")
    analysis: Optional[str] = Field(None, description="AI analysis of the block")
    severity: Optional[int] = Field(
        None, description="Severity rating (1-5, where 5 is most severe)", ge=1, le=5
    )

    @field_validator("window_start", "window_end")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """Validate that timestamps are in ISO format."""
        try:
            datetime.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError(f"Invalid ISO format timestamp: {v}")

    def to_prompt(self) -> str:
        """Convert block to a prompt for LLM analysis."""
        # Format the command counts section
        commands = "\n".join([f"- {cmd}: {count}" for cmd, count in self.command_counts.items()])

        # Format the top processes section
        processes = "\n".join([f"- {proc}: {count}" for proc, count in self.top_processes.items()])

        return f"""
# Linux EDR Block Report ({self.report_id})

**Time Window:** {self.window_start} to {self.window_end}
**Total Events:** {self.total_events}
**Cells Included:** {len(self.cells)}

## Top Command Execution Counts
{commands}

## Top Processes
{processes}

---
Analyze the aggregated system activity for security concerns over this 4-hour period. Identify any suspicious or unusual patterns in command execution trends. Explain why specific patterns might represent security risks.

Your response should be formatted as follows:
1. Summary: A concise summary of the overall security posture during this 4-hour period.
2. Security Score: Assign a severity level from 1-5 (where 1 is secure/normal and 5 is critical/severe).
3. Key Findings: List specific suspicious activities or security concerns found.

Include clear reasoning for your severity score.
"""


class DailyReport(BaseModel):
    """
    Level 3 report covering a 24-hour window of system activity.
    Composed of 6 Blocks (4-hour intervals).
    """

    report_id: str = Field(..., description="Unique identifier for this daily report")
    date: str = Field(..., description="Date of the report (YYYY-MM-DD)")
    window_start: str = Field(..., description="Start time of the daily window (ISO format)")
    window_end: str = Field(..., description="End time of the daily window (ISO format)")
    total_events: int = Field(..., description="Total number of events across all blocks")
    blocks: List[str] = Field(..., description="List of Block report IDs included in this report")
    command_counts: Dict[str, int] = Field(
        ..., description="Aggregated count of each command executed"
    )
    top_processes: Dict[str, int] = Field(..., description="Top processes by execution count")
    unusual_activity: List[Dict[str, Any]] = Field(
        default_factory=list, description="Unusual activity patterns detected"
    )
    analysis: Optional[str] = Field(None, description="AI analysis of the daily activity")
    severity: Optional[int] = Field(
        None, description="Severity rating (1-5, where 5 is most severe)", ge=1, le=5
    )

    @model_validator(mode="after")
    def validate_date_format(self) -> "DailyReport":
        """Validate date is in YYYY-MM-DD format."""
        try:
            datetime.strptime(self.date, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Invalid date format: {self.date}. Expected YYYY-MM-DD")
        return self

    def to_prompt(self) -> str:
        """Convert daily report to a prompt for LLM analysis."""
        # Format the command counts section
        commands = "\n".join([f"- {cmd}: {count}" for cmd, count in self.command_counts.items()])

        # Format the top processes section
        processes = "\n".join([f"- {proc}: {count}" for proc, count in self.top_processes.items()])

        # Format unusual activity if any
        unusual = ""
        if self.unusual_activity:
            unusual_items = []
            for item in self.unusual_activity:
                details = "\n".join([f"  - {k}: {v}" for k, v in item.items()])
                unusual_items.append(f"- Unusual pattern:\n{details}")
            unusual = "\n\n## Unusual Activity Detected\n" + "\n\n".join(unusual_items)

        return f"""
# Linux EDR Daily Report ({self.date})

**Time Window:** {self.window_start} to {self.window_end}
**Total Events:** {self.total_events}
**Blocks Included:** {len(self.blocks)}

## Top Command Execution Counts
{commands}

## Top Processes
{processes}
{unusual}

---
Analyze the system activity over this 24-hour period. Identify any suspicious or unusual patterns in command execution. Explain why specific commands or patterns might represent security risks. Compare with typical baseline activity for this system.

Your response should be formatted as follows:
1. Summary: A concise summary of the overall security posture during this 24-hour period.
2. Security Score: Assign a severity level from 1-5 (where 1 is secure/normal and 5 is critical/severe).
3. Key Findings: List specific suspicious activities or security concerns found.

Include clear reasoning for your severity score.
"""


class WeeklyReport(BaseModel):
    """
    Level 4 report covering a 7-day window of system activity.
    Composed of 7 DailyReports.
    """

    report_id: str = Field(..., description="Unique identifier for this weekly report")
    week_start_date: str = Field(..., description="Start date of the week (YYYY-MM-DD)")
    week_end_date: str = Field(..., description="End date of the week (YYYY-MM-DD)")
    total_events: int = Field(..., description="Total number of events across all days")
    daily_reports: List[str] = Field(
        ..., description="List of DailyReport IDs included in this report"
    )
    command_trends: Dict[str, List[int]] = Field(..., description="Daily trends of top commands")
    process_trends: Dict[str, List[int]] = Field(..., description="Daily trends of top processes")
    security_incidents: List[Dict[str, Any]] = Field(
        default_factory=list, description="Security incidents detected"
    )
    risk_score: int = Field(..., description="Overall security risk score (0-100)", ge=0, le=100)
    analysis: Optional[str] = Field(None, description="AI analysis of the weekly activity")
    severity: Optional[int] = Field(
        None, description="Severity rating (1-5, where 5 is most severe)", ge=1, le=5
    )

    @model_validator(mode="after")
    def validate_date_range(self) -> "WeeklyReport":
        """Validate date range is valid and spans 7 days."""
        try:
            start = datetime.strptime(self.week_start_date, "%Y-%m-%d")
            end = datetime.strptime(self.week_end_date, "%Y-%m-%d")
            delta = (end - start).days
            if delta != 6:  # 7 days total (0-6)
                raise ValueError(f"Weekly report should cover 7 days, but spans {delta+1} days")
        except ValueError as e:
            raise ValueError(f"Invalid date format or range: {e}")
        return self

    def to_prompt(self) -> str:
        """Convert weekly report to a prompt for LLM analysis."""
        # Format basic info
        basic_info = f"""
# Linux EDR Weekly Report ({self.week_start_date} to {self.week_end_date})

**Total Events:** {self.total_events}
**Risk Score:** {self.risk_score}/100
**Daily Reports Included:** {len(self.daily_reports)}
"""

        # Format security incidents if any
        incidents = ""
        if self.security_incidents:
            incident_items = []
            for item in self.security_incidents:
                details = "\n".join([f"  - {k}: {v}" for k, v in item.items()])
                incident_items.append(f"- Incident:\n{details}")
            incidents = "\n\n## Security Incidents\n" + "\n\n".join(incident_items)

        return f"""{basic_info}{incidents}

---
Analyze the system activity over this week. Identify trends in command execution patterns and potential security issues. Compare with previous weeks if available.

Your response should be formatted as follows:
1. Summary: A concise summary of the overall security posture during this week.
2. Security Score: Assign a severity level from 1-5 (where 1 is secure/normal and 5 is critical/severe).
3. Key Findings: List specific suspicious activities or security concerns found.
4. Recommendations: Suggest actions to mitigate detected risks.

Include clear reasoning for your severity score.
"""


class MonthlyReport(BaseModel):
    """
    Level 5 report covering approximately a month of system activity.
    Composed of approximately 4 WeeklyReports.
    """

    report_id: str = Field(..., description="Unique identifier for this monthly report")
    month: str = Field(..., description="Month of the report (YYYY-MM)")
    start_date: str = Field(..., description="Start date of the month (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date of the month (YYYY-MM-DD)")
    total_events: int = Field(..., description="Total number of events across all weeks")
    weekly_reports: List[str] = Field(
        ..., description="List of WeeklyReport IDs included in this report"
    )
    command_summary: Dict[str, int] = Field(..., description="Summary of command executions")
    process_summary: Dict[str, int] = Field(..., description="Summary of process executions")
    security_summary: Dict[str, Any] = Field(
        ..., description="Summary of security incidents and risks"
    )
    risk_score: int = Field(..., description="Overall security risk score (0-100)", ge=0, le=100)
    recommendations: List[str] = Field(default_factory=list, description="Security recommendations")
    analysis: Optional[str] = Field(None, description="AI analysis of the monthly activity")
    severity: Optional[int] = Field(
        None, description="Severity rating (1-5, where 5 is most severe)", ge=1, le=5
    )

    @model_validator(mode="after")
    def validate_month_format(self) -> "MonthlyReport":
        """Validate month is in YYYY-MM format and dates are consistent."""
        try:
            month_date = datetime.strptime(self.month, "%Y-%m")
            start = datetime.strptime(self.start_date, "%Y-%m-%d")
            end = datetime.strptime(self.end_date, "%Y-%m-%d")

            # Check that start/end dates are in the correct month
            if start.year != month_date.year or start.month != month_date.month:
                raise ValueError(f"Start date {self.start_date} does not match month {self.month}")

            # Check that end date is after start date
            if end <= start:
                raise ValueError(
                    f"End date {self.end_date} must be after start date {self.start_date}"
                )

        except ValueError as e:
            raise ValueError(f"Invalid date format or range: {e}")
        return self

    def to_prompt(self) -> str:
        """Convert monthly report to a prompt for LLM analysis."""
        # Format basic info
        basic_info = f"""
# Linux EDR Monthly Report ({self.month})

**Date Range:** {self.start_date} to {self.end_date}
**Total Events:** {self.total_events}
**Overall Risk Score:** {self.risk_score}/100
**Weekly Reports Included:** {len(self.weekly_reports)}
"""

        # Format the recommendations if any
        recommendations = ""
        if self.recommendations:
            recommendations = "\n\n## Security Recommendations\n" + "\n".join(
                [f"- {rec}" for rec in self.recommendations]
            )

        return f"""{basic_info}{recommendations}

---
Provide a comprehensive monthly security analysis based on the collected data. Identify long-term trends, recurring patterns, and fundamental security posture issues.

Your response should be formatted as follows:
1. Summary: A concise summary of the overall security posture during this month.
2. Security Score: Assign a severity level from 1-5 (where 1 is secure/normal and 5 is critical/severe).
3. Key Findings: List the most significant security observations from the month.
4. Strategic Recommendations: Suggest long-term improvements to enhance the system's security.

Include clear reasoning for your severity score.
"""
