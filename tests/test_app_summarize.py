import unittest
from unittest.mock import patch, MagicMock, PropertyMock
from linux_edr.app import LinuxEDRApp


class TestAppSummarize(unittest.TestCase):
    """Tests for the _summarize method of LinuxEDRApp."""

    @patch("linux_edr.app.Config")
    @patch("linux_edr.app.TraceReader")
    @patch("linux_edr.app.Aggregator")
    @patch("linux_edr.app.Reporter")
    @patch("linux_edr.app.ReportManager")
    @patch("linux_edr.app.BackgroundScheduler")
    @patch("linux_edr.app.build_summary")
    @patch("linux_edr.app.process_raw_events")
    @patch("linux_edr.app.SyscallTracer")
    def test_summarize_with_events(
        self,
        mock_syscall_tracer,
        mock_process_raw_events,
        mock_build_summary,
        mock_scheduler,
        mock_report_manager,
        mock_reporter,
        mock_aggregator,
        mock_trace_reader,
        mock_config,
    ):
        """Test _summarize method with events."""
        # Setup mocks
        mock_agg_instance = mock_aggregator.return_value
        mock_rep_instance = mock_reporter.return_value
        mock_rm_instance = mock_report_manager.return_value
        mock_scheduler_instance = mock_scheduler.return_value

        # Setup mock data
        events = [
            {"command": "ls", "args": ["-la"], "pid": 1000},
            {"command": "cat", "args": ["/etc/passwd"], "pid": 1001},
        ]

        # Mock snapshot_and_clear to return our events
        mock_agg_instance.snapshot_and_clear.return_value = events

        # Mock process_raw_events
        processed_events = {"ls": ["ls -la"], "cat": ["cat /etc/passwd"]}
        mock_process_raw_events.return_value = processed_events

        # Mock build_summary
        mock_cell = MagicMock()
        mock_build_summary.return_value = mock_cell

        # Mock scheduler.get_job().trigger.interval.seconds
        mock_job = MagicMock()
        mock_trigger = MagicMock()
        mock_interval = MagicMock()
        mock_interval.seconds = 900  # 15 minutes
        mock_trigger.interval = mock_interval
        mock_job.trigger = mock_trigger
        mock_scheduler_instance.get_job.return_value = mock_job

        # Create app instance with necessary mocks
        app = MagicMock()
        app.agg = mock_agg_instance
        app.rep = mock_rep_instance
        app.report_manager = mock_rm_instance
        app.scheduler = mock_scheduler_instance

        # Call _summarize directly to avoid initializing TraceReader
        from linux_edr.app import LinuxEDRApp

        LinuxEDRApp._summarize(app)

        # Verify events were retrieved from aggregator
        mock_agg_instance.snapshot_and_clear.assert_called_once()

        # Verify events were processed
        mock_process_raw_events.assert_called_once_with(events)

        # Verify build_summary was called
        mock_build_summary.assert_called_once_with(events, window_minutes=15, as_cell=True)

        # Verify process_events were set
        self.assertEqual(mock_cell.process_events, processed_events)

        # Verify cell was added to report manager
        mock_rm_instance.create_cell.assert_called_once_with(mock_cell)

    @patch("linux_edr.app.Config")
    @patch("linux_edr.app.TraceReader")
    @patch("linux_edr.app.Aggregator")
    @patch("linux_edr.app.Reporter")
    @patch("linux_edr.app.ReportManager")
    @patch("linux_edr.app.BackgroundScheduler")
    @patch("linux_edr.app.logging")
    @patch("linux_edr.app.SyscallTracer")
    def test_summarize_no_events(
        self,
        mock_syscall_tracer,
        mock_logging,
        mock_scheduler,
        mock_report_manager,
        mock_reporter,
        mock_aggregator,
        mock_trace_reader,
        mock_config,
    ):
        """Test _summarize method with no events."""
        # Setup mocks
        mock_agg_instance = mock_aggregator.return_value
        mock_rep_instance = mock_reporter.return_value
        mock_rm_instance = mock_report_manager.return_value

        # Mock snapshot_and_clear to return empty list
        mock_agg_instance.snapshot_and_clear.return_value = []

        # Create app instance with necessary mocks
        app = MagicMock()
        app.agg = mock_agg_instance

        # Call _summarize directly
        from linux_edr.app import LinuxEDRApp

        LinuxEDRApp._summarize(app)

        # Verify events were retrieved from aggregator
        mock_agg_instance.snapshot_and_clear.assert_called_once()

        # Verify report manager methods were not called (no events)
        mock_rm_instance.create_cell.assert_not_called()

        # Verify info was logged
        mock_logging.info.assert_any_call("No events to summarize")

    @patch("linux_edr.app.Config")
    @patch("linux_edr.app.TraceReader")
    @patch("linux_edr.app.Aggregator")
    @patch("linux_edr.app.Reporter")
    @patch("linux_edr.app.ReportManager")
    @patch("linux_edr.app.BackgroundScheduler")
    @patch("linux_edr.app.build_summary")
    @patch("linux_edr.app.process_raw_events")
    @patch("linux_edr.app.SyscallTracer")
    def test_summarize_large_event_count(
        self,
        mock_syscall_tracer,
        mock_process_raw_events,
        mock_build_summary,
        mock_scheduler,
        mock_report_manager,
        mock_reporter,
        mock_aggregator,
        mock_trace_reader,
        mock_config,
    ):
        """Test _summarize method with large event count."""
        # Setup mocks
        mock_agg_instance = mock_aggregator.return_value
        mock_rm_instance = mock_report_manager.return_value
        mock_scheduler_instance = mock_scheduler.return_value

        # Create a large number of events
        events = [{"command": f"cmd{i}", "pid": i} for i in range(200)]

        # Mock snapshot_and_clear to return our events
        mock_agg_instance.snapshot_and_clear.return_value = events

        # Mock process_raw_events
        processed_events = {"cmd0": ["cmd0"], "cmd1": ["cmd1"]}  # Simplified for test
        mock_process_raw_events.return_value = processed_events

        # Mock build_summary
        mock_cell = MagicMock()
        mock_build_summary.return_value = mock_cell

        # Mock scheduler.get_job().trigger.interval.seconds
        mock_job = MagicMock()
        mock_trigger = MagicMock()
        mock_interval = MagicMock()
        mock_interval.seconds = 900  # 15 minutes
        mock_trigger.interval = mock_interval
        mock_job.trigger = mock_trigger
        mock_scheduler_instance.get_job.return_value = mock_job

        # Create app instance with necessary mocks
        app = MagicMock()
        app.agg = mock_agg_instance
        app.report_manager = mock_rm_instance
        app.scheduler = mock_scheduler_instance

        # Call _summarize directly
        from linux_edr.app import LinuxEDRApp

        LinuxEDRApp._summarize(app)

        # Verify cell was created and added to report manager
        mock_rm_instance.create_cell.assert_called_once_with(mock_cell)


if __name__ == "__main__":
    unittest.main()
