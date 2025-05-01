import unittest
import tempfile
import os
import json
from unittest.mock import patch, MagicMock
from linux_edr.reporter import Reporter
from linux_edr.models import SummaryReport, Cell


class TestReporter(unittest.TestCase):
    """Tests for the Reporter class that handles saving reports and sending them to OpenAI."""

    def test_save_json_no_output_file(self):
        """Test save_json with no output file specified."""
        reporter = Reporter(api_key=None, output_file=None)
        
        # Create a simple report
        summary = SummaryReport(
            report_id="test123",
            window_start="2023-01-01T00:00:00+00:00",
            window_end="2023-01-01T00:15:00+00:00",
            total=5,
            command_counts={"ls": 2, "cat": 3}
        )
        
        # Should not raise any exceptions
        reporter.save_json(summary)
        # No assertions needed as it should just return without action

    def test_save_json_with_output_file(self):
        """Test save_json with an output file specified."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            output_path = temp_file.name
        
        try:
            reporter = Reporter(api_key=None, output_file=output_path)
            
            # Create a simple report
            summary = SummaryReport(
                report_id="test123",
                window_start="2023-01-01T00:00:00+00:00",
                window_end="2023-01-01T00:15:00+00:00",
                total=5,
                command_counts={"ls": 2, "cat": 3}
            )
            
            # Save the report
            reporter.save_json(summary)
            
            # Verify the file was written correctly
            with open(output_path, "r") as f:
                content = f.read()
                data = json.loads(content)
                
                self.assertEqual(data["report_id"], "test123")
                self.assertEqual(data["total"], 5)
                self.assertEqual(data["command_counts"]["ls"], 2)
                self.assertEqual(data["command_counts"]["cat"], 3)
        finally:
            # Clean up
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_save_json_with_raw_events(self):
        """Test save_json with raw events included."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            output_path = temp_file.name
        
        try:
            reporter = Reporter(api_key=None, output_file=output_path)
            
            # Create a simple report
            summary = SummaryReport(
                report_id="test123",
                window_start="2023-01-01T00:00:00+00:00",
                window_end="2023-01-01T00:15:00+00:00",
                total=2,
                command_counts={"ls": 1, "cat": 1}
            )
            
            # Raw events to include
            raw_events = [
                {"command": "ls", "args": ["-la"], "pid": 1000},
                {"command": "cat", "args": ["/etc/passwd"], "pid": 1001}
            ]
            
            # Save the report with raw events
            reporter.save_json(summary, include_raw_events=True, raw_events=raw_events)
            
            # Verify the file was written correctly
            with open(output_path, "r") as f:
                content = f.read()
                data = json.loads(content)
                
                self.assertEqual(data["report_id"], "test123")
                self.assertEqual(len(data["raw_events"]), 2)
                self.assertEqual(data["raw_events"][0]["command"], "ls")
                self.assertEqual(data["raw_events"][1]["command"], "cat")
        finally:
            # Clean up
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_save_json_with_process_events(self):
        """Test save_json with process_events added to the report."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            output_path = temp_file.name
        
        try:
            reporter = Reporter(api_key=None, output_file=output_path)
            
            # Create a simple report with process_events attribute
            summary = SummaryReport(
                report_id="test123",
                window_start="2023-01-01T00:00:00+00:00",
                window_end="2023-01-01T00:15:00+00:00",
                total=2,
                command_counts={"ls": 1, "cat": 1}
            )
            
            # Set process_events attribute manually
            summary.process_events = {
                "ls": ["ls -la /tmp"],
                "cat": ["cat /etc/passwd"]
            }
            
            # Save the report
            reporter.save_json(summary)
            
            # Verify the file was written correctly
            with open(output_path, "r") as f:
                content = f.read()
                data = json.loads(content)
                
                self.assertEqual(data["report_id"], "test123")
                self.assertIn("process_events", data)
                self.assertEqual(data["process_events"]["ls"], ["ls -la /tmp"])
                self.assertEqual(data["process_events"]["cat"], ["cat /etc/passwd"])
        finally:
            # Clean up
            if os.path.exists(output_path):
                os.unlink(output_path)

    @patch('linux_edr.reporter.OpenAI')
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
            command_counts={"ls": 2, "cat": 3}
        )
        
        # Mock the logger to test the warning is logged
        with patch('linux_edr.reporter.logger') as mock_logger:
            # Call method being tested
            result = reporter.send_llm(summary)
            
            # Verify result is None
            self.assertIsNone(result)
            
            # Verify warning was logged 
            mock_logger.warning.assert_called_once()
            # Check warning message contains 'not configured'
            self.assertIn("not configured", mock_logger.warning.call_args[0][0])
        
        # Should not have created an OpenAI client
        mock_openai.assert_not_called()

    @patch('linux_edr.reporter.OpenAI')
    def test_send_llm_with_api_key(self, mock_openai):
        """Test send_llm with a valid API key."""
        # Mock the OpenAI client and completion
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test analysis result"
        
        mock_client.chat.completions.create.return_value = mock_response
        
        # Create reporter with API key
        reporter = Reporter(api_key="test_key")
        
        # Create a simple report
        summary = SummaryReport(
            report_id="test123",
            window_start="2023-01-01T00:00:00+00:00",
            window_end="2023-01-01T00:15:00+00:00",
            total=5,
            command_counts={"ls": 2, "cat": 3}
        )
        
        # Send to LLM
        result = reporter.send_llm(summary)
        
        # Verify response
        self.assertEqual(result, "Test analysis result")
        
        # Verify OpenAI client was created and called correctly
        mock_openai.assert_called_once_with(api_key="test_key")
        mock_client.chat.completions.create.assert_called_once()
        
        # Verify the correct model and prompt were used
        call_args = mock_client.chat.completions.create.call_args[1]
        self.assertEqual(call_args["model"], "gpt-4o-mini")  # Default model
        self.assertEqual(len(call_args["messages"]), 2)
        self.assertEqual(call_args["messages"][0]["role"], "system")
        self.assertEqual(call_args["messages"][1]["role"], "user")


if __name__ == "__main__":
    unittest.main() 