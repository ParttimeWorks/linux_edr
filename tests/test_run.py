import unittest
from unittest.mock import patch, MagicMock, call
import time
from linux_edr.app import LinuxEDRApp


class TestAppRun(unittest.TestCase):
    """Tests for the run method of LinuxEDRApp."""

    @patch("linux_edr.app.Config")
    @patch("linux_edr.app.TraceReader")
    @patch("linux_edr.app.Aggregator")
    @patch("linux_edr.app.Reporter")
    @patch("linux_edr.app.ReportManager")
    @patch("linux_edr.app.BackgroundScheduler")
    @patch("linux_edr.app.logging")
    def test_run_normal_operation(
        self,
        mock_logging,
        mock_scheduler,
        mock_report_manager,
        mock_reporter,
        mock_aggregator,
        mock_trace_reader,
        mock_config,
    ):
        """Test normal operation of the run method."""
        # Setup mocks
        mock_scheduler_instance = mock_scheduler.return_value
        mock_reader_instance = mock_trace_reader.return_value
        mock_agg_instance = mock_aggregator.return_value

        # Prepare trace reader to return two events then raise KeyboardInterrupt
        event1 = {"command": "ls", "args": ["-la"], "pid": 1000}
        event2 = {"command": "cat", "args": ["/etc/passwd"], "pid": 1001}

        # Set up the iterable to yield two events then stop
        mock_reader_instance.__iter__.return_value = iter([event1, event2, None])

        # Create app instance
        app = LinuxEDRApp()

        # Call run
        app.run()

        # Verify scheduler was started
        mock_scheduler_instance.start.assert_called_once()

        # Verify events were added to aggregator
        mock_agg_instance.add.assert_has_calls([call(event1), call(event2)])

        # Verify logging
        mock_logging.info.assert_any_call("Scheduler started")
        mock_logging.info.assert_any_call("Application stopped")

        # Verify scheduler was shut down
        mock_scheduler_instance.shutdown.assert_called_once()

    @patch("linux_edr.app.Config")
    @patch("linux_edr.app.TraceReader")
    @patch("linux_edr.app.Aggregator")
    @patch("linux_edr.app.Reporter")
    @patch("linux_edr.app.ReportManager")
    @patch("linux_edr.app.BackgroundScheduler")
    @patch("linux_edr.app.logging")
    def test_run_keyboard_interrupt(
        self,
        mock_logging,
        mock_scheduler,
        mock_report_manager,
        mock_reporter,
        mock_aggregator,
        mock_trace_reader,
        mock_config,
    ):
        """Test run method with KeyboardInterrupt."""
        # Setup mocks
        mock_scheduler_instance = mock_scheduler.return_value
        mock_reader_instance = mock_trace_reader.return_value

        # Make reader iterator raise KeyboardInterrupt
        def iter_side_effect():
            yield {"command": "ls", "args": ["-la"], "pid": 1000}
            raise KeyboardInterrupt()

        mock_reader_instance.__iter__.return_value = iter_side_effect()

        # Create app instance
        app = LinuxEDRApp()

        # Call run
        app.run()

        # Verify scheduler was started
        mock_scheduler_instance.start.assert_called_once()

        # Verify logging
        mock_logging.info.assert_any_call("Scheduler started")
        mock_logging.info.assert_any_call("Application interrupted")
        mock_logging.info.assert_any_call("Application stopped")

        # Verify scheduler was shut down
        mock_scheduler_instance.shutdown.assert_called_once()


if __name__ == "__main__":
    unittest.main()
