import unittest
import os
from unittest.mock import patch, MagicMock
from linux_edr.reporter import Reporter
from linux_edr.models import SummaryReport, Cell


class TestReporter(unittest.TestCase):
    """Tests for the Reporter class that handles sending reports to OpenAI."""

    def test_extract_severity(self):
        """Test extract_severity method with different input formats."""
        reporter = Reporter(api_key=None)

        # Test various formats
        test_cases = [
            ("Security Score: 3", 3),
            ("The security score is 4", 4),
            ("I'd rate the severity as 5/5", 5),
            ("Severity: 2", 2),
            ("severity level: 1", 1),
            ("The severity rating is 3 because...", 3),
            ("No severity here", None),
            ("Invalid severity: 6", None),  # Out of range
            ("Invalid severity: 0", None),  # Out of range
        ]

        for analysis_text, expected_severity in test_cases:
            severity = reporter.extract_severity(analysis_text)
            self.assertEqual(severity, expected_severity, f"Failed on '{analysis_text}'")

    @patch("linux_edr.reporter.OpenAI")
    def test_send_llm_no_api_key(self, mock_openai):
        """Test send_llm when no API key is provided."""
        # Create reporter without API key
        reporter = Reporter(api_key=None)

        # Create a simple report
        summary = SummaryReport(
            report_id="test123",
            window_start="2023-01-01T00:00:00+00:00",
            window_end="2023-01-01T00:15:00+00:00",
            total=5,
            command_counts={"ls": 2, "cat": 3},
        )

        # Mock the logger to test the warning is logged
        with patch("linux_edr.reporter.logger") as mock_logger:
            # Call method being tested
            analysis, severity = reporter.send_llm(summary)

            # Verify result is None for both values
            self.assertIsNone(analysis)
            self.assertIsNone(severity)

            # Verify warning was logged
            mock_logger.warning.assert_called_once()
            # Check warning message contains 'not configured'
            self.assertIn("not configured", mock_logger.warning.call_args[0][0])

        # Should not have created an OpenAI client
        mock_openai.assert_not_called()

    @patch("linux_edr.reporter.OpenAI")
    def test_send_llm_with_api_key(self, mock_openai):
        """Test send_llm with a valid API key."""
        # Mock the OpenAI client and completion
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test analysis result\nSecurity Score: 3"

        mock_client.chat.completions.create.return_value = mock_response

        # Create reporter with API key
        reporter = Reporter(api_key="test_key")

        # Create a simple report
        summary = SummaryReport(
            report_id="test123",
            window_start="2023-01-01T00:00:00+00:00",
            window_end="2023-01-01T00:15:00+00:00",
            total=5,
            command_counts={"ls": 2, "cat": 3},
        )

        # Send to LLM
        analysis, severity = reporter.send_llm(summary)

        # Verify response
        self.assertEqual(analysis, "Test analysis result\nSecurity Score: 3")
        self.assertEqual(severity, 3)

        # Verify OpenAI client was created and called correctly
        mock_openai.assert_called_once_with(api_key="test_key")
        mock_client.chat.completions.create.assert_called_once()

        # Verify the correct model and prompt were used
        call_args = mock_client.chat.completions.create.call_args[1]
        self.assertEqual(call_args["model"], "gpt-4o-mini")  # Default model
        self.assertEqual(len(call_args["messages"]), 2)
        self.assertEqual(call_args["messages"][0]["role"], "system")
        self.assertEqual(call_args["messages"][1]["role"], "user")

    @patch("linux_edr.reporter.OpenAI")
    def test_analyze_report(self, mock_openai):
        """Test analyze_report method."""
        # Mock the OpenAI client and completion
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Analysis result\nSeverity: 4"

        mock_client.chat.completions.create.return_value = mock_response

        # Create reporter with API key
        reporter = Reporter(api_key="test_key")

        # Create a simple report
        summary = SummaryReport(
            report_id="test123",
            window_start="2023-01-01T00:00:00+00:00",
            window_end="2023-01-01T00:15:00+00:00",
            total=5,
            command_counts={"ls": 2, "cat": 3},
        )

        # Call analyze_report
        reporter.analyze_report(summary)

        # Verify report was updated with analysis and severity
        self.assertEqual(summary.analysis, "Analysis result\nSeverity: 4")
        self.assertEqual(summary.severity, 4)


if __name__ == "__main__":
    unittest.main()
