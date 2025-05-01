import json
import logging
import re
from typing import List, Dict, Any, Optional, Union, Tuple
from openai import OpenAI
from .models import SummaryReport, Cell, Block, DailyReport, WeeklyReport, MonthlyReport

logger = logging.getLogger(__name__)


class Reporter:
    def __init__(self, api_key: str = None, model: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=api_key) if api_key else None
        self.model = model

    def send_llm(
        self, report: Union[SummaryReport, Cell, Block, DailyReport, WeeklyReport, MonthlyReport]
    ) -> Tuple[Optional[str], Optional[int]]:
        """
        Send report to LLM for analysis.

        Args:
            report: Report to analyze

        Returns:
            Tuple of (analysis text, severity score) or (None, None) if error
        """
        if not self.client:
            logger.warning("OpenAI client not configured, skipping LLM analysis")
            return None, None

        prompt = report.to_prompt()
        try:
            logger.debug(f"Sending prompt to {self.model}")
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a security analyst specializing in Linux system activity. Analyze command execution patterns to identify potential security concerns. Format your response with a summary, severity score (1-5), and key findings.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=500,
            )
            analysis = resp.choices[0].message.content
            severity = self.extract_severity(analysis)

            logger.info(f"LLM analysis complete (severity: {severity if severity else 'unknown'})")

            return analysis, severity

        except Exception as e:
            logger.error(f"LLM error: {e}")
            return None, None

    def extract_severity(self, analysis: str) -> Optional[int]:
        """
        Extract severity score from analysis text.

        Args:
            analysis: The analysis text from LLM

        Returns:
            Severity score (1-5) or None if not found
        """
        # Look for patterns like "Security Score: 3" or "Severity: 4/5" or "severity level: 2"
        patterns = [
            r"Security Score:\s*(\d+)",
            r"Severity:?\s*(\d+)(?:/5)?",
            r"severity level:?\s*(\d+)",
            r"severity rating(?:\s+is)?:?\s*(\d+)",  # Modified to better match "severity rating is X"
            r"severity score:?\s*(\d+)",
            r"security score is\s*(\d+)",
            r"rate the severity as\s*(\d+)",
        ]

        for pattern in patterns:
            if match := re.search(pattern, analysis, re.IGNORECASE):
                try:
                    score = int(match.group(1))
                    if 1 <= score <= 5:
                        return score
                except ValueError:
                    continue

        return None

    def analyze_report(
        self, report: Union[SummaryReport, Cell, Block, DailyReport, WeeklyReport, MonthlyReport]
    ) -> None:
        """
        Send a report to LLM for analysis and update it with the results.

        Args:
            report: The report to analyze
        """
        analysis, severity = self.send_llm(report)
        if analysis:
            # Update the report with the analysis and severity
            report.analysis = analysis
            if severity:
                report.severity = severity
            logger.debug(
                f"Updated {type(report).__name__} {report.report_id} with analysis (severity: {severity if severity else 'unknown'})"
            )
