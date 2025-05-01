from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, model_validator

class WeeklyReport(BaseModel):
    """
    Level 4 report covering a 7-day window of system activity.
    Composed of 7 DailyReports.
    """
    report_id: str = Field(..., description="Unique identifier for this weekly report")
    week_start_date: str = Field(..., description="Start date of the week (YYYY-MM-DD)")
    week_end_date: str = Field(..., description="End date of the week (YYYY-MM-DD)")
    total_events: int = Field(..., description="Total number of events across all days")
    daily_reports: List[str] = Field(..., description="List of DailyReport IDs included in this report")
    command_trends: Dict[str, List[int]] = Field(..., description="Daily trends of top commands")
    process_trends: Dict[str, List[int]] = Field(..., description="Daily trends of top processes")
    security_incidents: List[Dict[str, Any]] = Field(default_factory=list, description="Security incidents detected")
    risk_score: int = Field(..., description="Overall security risk score (0-100)", ge=0, le=100)
    analysis: Optional[str] = Field(None, description="AI analysis of the weekly activity")
    severity: Optional[int] = Field(None, description="Severity rating (1-5, where 5 is most severe)", ge=1, le=5)
    
    @model_validator(mode='after')
    def validate_date_range(self) -> 'WeeklyReport':
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

Total Events: {self.total_events}
Risk Score: {self.risk_score}/100
Daily Reports Included: {len(self.daily_reports)}
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

    def model_dump(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation of the report
        """
        data = super().model_dump()
        # Remove None values for cleaner output
        return {k: v for k, v in data.items() if v is not None} 