import statistics
from typing import List, Dict, Any, Optional


class SeverityCalculator:
    """
    Service for calculating severity scores across report hierarchies.
    Provides methods to determine report severity levels based on lower-level reports.
    """

    @staticmethod
    def calculate_from_lower_reports(report_data_list: List[Dict[str, Any]]) -> Optional[int]:
        """
        Calculate a severity score based on lower-level reports.

        Uses a weighted calculation that favors high severity to avoid underestimating threats:
        - 70% from the median severity
        - 30% from the maximum severity

        Args:
            report_data_list: List of lower-level report data

        Returns:
            Calculated severity (1-5) or None if no severity data available
        """
        severities = []
        for report in report_data_list:
            if severity := report.get("severity"):
                severities.append(severity)

        if not severities:
            return None

        # Calculate the median and add a bias toward higher severity
        # This ensures we don't underestimate security threats
        median = statistics.median(severities)
        max_severity = max(severities)

        # Apply a bias formula: 70% median + 30% max to favor higher severities
        weighted_severity = round(0.7 * median + 0.3 * max_severity)

        # Ensure the result is between 1 and 5
        return max(1, min(5, weighted_severity))

    @staticmethod
    def calculate_risk_score(severity: Optional[int]) -> int:
        """
        Calculate a risk score (0-100) from a severity rating (1-5).

        Args:
            severity: Severity rating on a 1-5 scale

        Returns:
            Risk score on a 0-100 scale
        """
        if severity is None:
            return 40  # Default to moderate risk when severity is unknown

        # Linear transformation: severity 1-5 maps to risk score 20-100
        return min(20 * severity, 100)
