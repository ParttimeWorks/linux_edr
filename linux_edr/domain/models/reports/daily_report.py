from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, model_validator

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
    command_counts: Dict[str, int] = Field(..., description="Aggregated count of each command executed")
    top_processes: Dict[str, int] = Field(..., description="Top processes by execution count")
    unusual_activity: List[Dict[str, Any]] = Field(default_factory=list, description="Unusual activity patterns detected")
    analysis: Optional[str] = Field(None, description="AI analysis of the daily activity")
    severity: Optional[int] = Field(None, description="Severity rating (1-5, where 5 is most severe)", ge=1, le=5)
    
    @model_validator(mode='after')
    def validate_date_format(self) -> 'DailyReport':
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

Time Window: {self.window_start} to {self.window_end}
Total Events: {self.total_events}
Blocks Included: {len(self.blocks)}

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

    def model_dump(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation of the report
        """
        data = super().model_dump()
        # Remove None values for cleaner output
        return {k: v for k, v in data.items() if v is not None} 