from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator


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
    process_events: Optional[Dict[str, List[str]]] = Field(None, description="Grouped events by process name")
    raw_events: Optional[List[Dict[str, Any]]] = Field(None, description="Raw event data")
    analysis: Optional[str] = Field(None, description="AI analysis of the events")
    severity: Optional[int] = Field(None, description="Severity rating (1-5, where 5 is most severe)", ge=1, le=5)

    @field_validator('window_start', 'window_end')
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """Validate that timestamps are in ISO format."""
        try:
            datetime.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError(f"Invalid ISO format timestamp: {v}")

    @field_validator('total')
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

Time Window: {self.window_start} to {self.window_end}
Total Events: {self.total}

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