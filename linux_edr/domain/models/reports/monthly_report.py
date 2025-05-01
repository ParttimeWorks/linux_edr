from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, model_validator


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

Date Range: {self.start_date} to {self.end_date}
Total Events: {self.total_events}
Overall Risk Score: {self.risk_score}/100
Weekly Reports Included: {len(self.weekly_reports)}
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

    def model_dump(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.

        Returns:
            Dictionary representation of the report
        """
        data = super().model_dump()
        # Remove None values for cleaner output
        return {k: v for k, v in data.items() if v is not None}
