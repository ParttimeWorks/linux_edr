import unittest
import tempfile
import os
import json
from unittest.mock import patch, MagicMock
from linux_edr.reporter import Reporter
from linux_edr.models import SummaryReport, Cell, Block, DailyReport, WeeklyReport, MonthlyReport


class TestReporterAdvanced(unittest.TestCase):
    """Additional tests for the Reporter class focused on more complex functionality."""

    @patch("linux_edr.reporter.OpenAI")
    def test_analyze_report_block(self, mock_openai):
        """Test analyze_report method with a Block report."""
        # Mock OpenAI client setup
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Block analysis result\nSecurity Score: 2"

        mock_client.chat.completions.create.return_value = mock_response

        # Create a reporter with API key
        reporter = Reporter(api_key="test_key")

        # Create a Block report
        block = Block(
            report_id="block123",
            window_start="2023-01-01T00:00:00+00:00",
            window_end="2023-01-01T04:00:00+00:00",
            total_events=50,
            cells=["cell1", "cell2", "cell3"],
            command_counts={"ls": 20, "cat": 15, "grep": 10, "find": 5},
            top_processes={"bash": 25, "python": 15, "nginx": 10},
        )

        # Call analyze_report
        reporter.analyze_report(block)

        # Verify LLM was called with the block's prompt
        mock_client.chat.completions.create.assert_called_once()

        # Verify block was updated with analysis and severity
        self.assertEqual(block.analysis, "Block analysis result\nSecurity Score: 2")
        self.assertEqual(block.severity, 2)

    @patch("linux_edr.reporter.OpenAI")
    def test_analyze_report_daily(self, mock_openai):
        """Test analyze_report method with a DailyReport."""
        # Mock OpenAI client setup
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Daily report analysis\nSeverity: 3"

        mock_client.chat.completions.create.return_value = mock_response

        # Create a reporter with API key
        reporter = Reporter(api_key="test_key")

        # Create a DailyReport
        daily = DailyReport(
            report_id="daily123",
            date="2023-01-01",
            window_start="2023-01-01T00:00:00+00:00",
            window_end="2023-01-01T23:59:59+00:00",
            total_events=200,
            blocks=["block1", "block2", "block3"],
            command_counts={"ls": 80, "cat": 60, "grep": 40, "find": 20},
            top_processes={"bash": 100, "python": 60, "nginx": 40},
            unusual_activity=[{"type": "high_volume", "command": "ssh", "count": 50}],
        )

        # Call analyze_report
        reporter.analyze_report(daily)

        # Verify LLM was called with the daily report's prompt
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args[1]
        self.assertIn("messages", call_args)
        self.assertEqual(len(call_args["messages"]), 2)
        self.assertIn("Daily Report", call_args["messages"][1]["content"])

        # Verify daily report was updated with analysis and severity
        self.assertEqual(daily.analysis, "Daily report analysis\nSeverity: 3")
        self.assertEqual(daily.severity, 3)

    @patch("linux_edr.reporter.OpenAI")
    def test_analyze_report_weekly(self, mock_openai):
        """Test analyze_report method with a WeeklyReport."""
        # Mock OpenAI client setup
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Weekly report analysis\nSecurity Score: 4"

        mock_client.chat.completions.create.return_value = mock_response

        # Create a reporter with API key
        reporter = Reporter(api_key="test_key")

        # Create a WeeklyReport
        weekly = WeeklyReport(
            report_id="weekly123",
            week_start_date="2023-01-01",
            week_end_date="2023-01-07",
            total_events=1000,
            daily_reports=["day1", "day2", "day3", "day4", "day5", "day6", "day7"],
            command_trends={"ls": [10, 15, 12, 18, 20, 5, 8], "cat": [5, 8, 10, 12, 15, 4, 6]},
            process_trends={
                "bash": [50, 60, 45, 70, 80, 30, 40],
                "python": [20, 25, 30, 35, 40, 15, 10],
            },
            security_incidents=[
                {"type": "brute_force", "source_ip": "192.168.1.10", "attempts": 50}
            ],
            risk_score=65,
        )

        # Call analyze_report
        reporter.analyze_report(weekly)

        # Verify LLM was called
        mock_client.chat.completions.create.assert_called_once()

        # Verify report was updated with analysis and severity
        self.assertEqual(weekly.analysis, "Weekly report analysis\nSecurity Score: 4")
        self.assertEqual(weekly.severity, 4)

    @patch("linux_edr.reporter.OpenAI")
    def test_analyze_report_monthly(self, mock_openai):
        """Test analyze_report method with a MonthlyReport."""
        # Mock OpenAI client setup
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Monthly report analysis\nSeverity: 5"

        mock_client.chat.completions.create.return_value = mock_response

        # Create a reporter with API key
        reporter = Reporter(api_key="test_key")

        # Create a MonthlyReport
        monthly = MonthlyReport(
            report_id="monthly123",
            month="2023-01",
            start_date="2023-01-01",
            end_date="2023-01-31",
            total_events=5000,
            weekly_reports=["week1", "week2", "week3", "week4"],
            command_summary={"ls": 1200, "cat": 800, "grep": 600, "find": 400},
            process_summary={"bash": 2000, "python": 1500, "nginx": 1000, "apache": 500},
            security_summary={
                "total_incidents": 10,
                "high_risk": 2,
                "medium_risk": 3,
                "low_risk": 5,
            },
            risk_score=75,
            recommendations=["Update system packages", "Review SSH configurations"],
        )

        # Call analyze_report
        reporter.analyze_report(monthly)

        # Verify LLM was called
        mock_client.chat.completions.create.assert_called_once()

        # Verify report was updated with analysis and severity
        self.assertEqual(monthly.analysis, "Monthly report analysis\nSeverity: 5")
        self.assertEqual(monthly.severity, 5)

    @patch("linux_edr.reporter.OpenAI")
    def test_analyze_report_no_api_key(self, mock_openai):
        """Test analyze_report without an API key."""
        # Create a reporter without API key
        reporter = Reporter(api_key=None)

        # Create a Block report
        block = Block(
            report_id="block123",
            window_start="2023-01-01T00:00:00+00:00",
            window_end="2023-01-01T04:00:00+00:00",
            total_events=50,
            cells=["cell1", "cell2", "cell3"],
            command_counts={"ls": 20, "cat": 15, "grep": 10, "find": 5},
            top_processes={"bash": 25, "python": 15, "nginx": 10},
        )

        # Mock the logger
        with patch("linux_edr.reporter.logger") as mock_logger:
            # Call analyze_report
            reporter.analyze_report(block)

            # Verify warning was logged
            mock_logger.warning.assert_called_once()

        # OpenAI client should not be created
        mock_openai.assert_not_called()

        # Block should not have an analysis or severity
        self.assertIsNone(block.analysis)
        self.assertIsNone(block.severity)

    @patch("linux_edr.reporter.OpenAI")
    def test_send_llm_error_handling(self, mock_openai):
        """Test error handling in send_llm."""
        # Mock OpenAI client to raise an exception
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        mock_client.chat.completions.create.side_effect = Exception("API error")

        # Create a reporter with API key
        reporter = Reporter(api_key="test_key")

        # Create a summary report
        summary = SummaryReport(
            report_id="test123",
            window_start="2023-01-01T00:00:00+00:00",
            window_end="2023-01-01T00:15:00+00:00",
            total=5,
            command_counts={"ls": 2, "cat": 3},
        )

        # Mock the logger
        with patch("linux_edr.reporter.logger") as mock_logger:
            # Call send_llm - should handle the exception
            analysis, severity = reporter.send_llm(summary)

            # Verify error was logged
            mock_logger.error.assert_called_once()
            self.assertIn("LLM error", mock_logger.error.call_args[0][0])

        # Method should return None on error for both return values
        self.assertIsNone(analysis)
        self.assertIsNone(severity)

    @patch("builtins.open", new_callable=MagicMock)
    @patch("linux_edr.reporter.OpenAI")
    def test_send_llm_save_analysis(self, mock_openai, mock_open):
        """Test that send_llm saves analysis to file when output_file is set."""
        # Mock OpenAI client
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Analysis result\nSeverity: 3"

        mock_client.chat.completions.create.return_value = mock_response

        # Create a reporter with output file
        reporter = Reporter(api_key="test_key", output_file="test.json")

        # Create a summary report
        summary = SummaryReport(
            report_id="test123",
            window_start="2023-01-01T00:00:00+00:00",
            window_end="2023-01-01T00:15:00+00:00",
            total=5,
            command_counts={"ls": 2, "cat": 3},
        )

        # Set up the mock_open manager to handle context manager protocol
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        # Call send_llm
        analysis, severity = reporter.send_llm(summary)

        # Verify result
        self.assertEqual(analysis, "Analysis result\nSeverity: 3")
        self.assertEqual(severity, 3)

        # Verify file was opened for analysis output
        mock_open.assert_called_once_with("test.json.analysis", "a")

        # Verify content was written to file
        mock_file.write.assert_any_call(f"--- Analysis for report test123 (Severity: 3) ---\n")
        mock_file.write.assert_any_call("Analysis result\nSeverity: 3")
        mock_file.write.assert_any_call("\n\n")


if __name__ == "__main__":
    unittest.main()
