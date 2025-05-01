from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator

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
    command_counts: Dict[str, int] = Field(..., description="Aggregated count of each command executed")
    top_processes: Dict[str, int] = Field(..., description="Top processes by execution count")
    analysis: Optional[str] = Field(None, description="AI analysis of the block")
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
    
    def to_prompt(self) -> str:
        """Convert block to a prompt for LLM analysis."""
        # Format the command counts section
        commands = "\n".join([f"- {cmd}: {count}" for cmd, count in self.command_counts.items()])
        
        # Format the top processes section
        processes = "\n".join([f"- {proc}: {count}" for proc, count in self.top_processes.items()])
        
        return f"""
# Linux EDR Block Report ({self.report_id})

Time Window: {self.window_start} to {self.window_end}
Total Events: {self.total_events}
Cells Included: {len(self.cells)}

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

    def model_dump(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation of the report
        """
        data = super().model_dump()
        # Remove None values for cleaner output
        return {k: v for k, v in data.items() if v is not None} 