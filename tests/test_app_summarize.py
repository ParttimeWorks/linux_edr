import unittest
from unittest.mock import patch, MagicMock, PropertyMock
from linux_edr.app import LinuxEDRApp


class TestAppSummarize(unittest.TestCase):
    """Tests for the _summarize method of LinuxEDRApp."""

    @patch('linux_edr.app.Config')
    @patch('linux_edr.app.TraceReader')
    @patch('linux_edr.app.Aggregator')
    @patch('linux_edr.app.Reporter')
    @patch('linux_edr.app.ReportManager')
    @patch('linux_edr.app.BackgroundScheduler')
    @patch('linux_edr.app.build_summary')
    @patch('linux_edr.app.process_raw_events')
    def test_summarize_with_events(self, mock_process_raw_events, mock_build_summary, 
                               mock_scheduler, mock_report_manager, mock_reporter, 
                               mock_aggregator, mock_trace_reader, mock_config):
        """Test _summarize method with events."""
        # Setup mocks
        mock_agg_instance = mock_aggregator.return_value
        mock_rep_instance = mock_reporter.return_value
        mock_rm_instance = mock_report_manager.return_value
        mock_scheduler_instance = mock_scheduler.return_value
        
        # Setup mock data
        events = [
            {"command": "ls", "args": ["-la"], "pid": 1000},
            {"command": "cat", "args": ["/etc/passwd"], "pid": 1001}
        ]
        
        # Mock snapshot_and_clear to return our events
        mock_agg_instance.snapshot_and_clear.return_value = events
        
        # Mock process_raw_events
        processed_events = {
            "ls": ["ls -la"],
            "cat": ["cat /etc/passwd"]
        }
        mock_process_raw_events.return_value = processed_events
        
        # Mock build_summary
        mock_summary = MagicMock()
        mock_cell = MagicMock()
        mock_build_summary.side_effect = [mock_summary, mock_cell]
        
        # Mock scheduler.get_job().trigger.interval.seconds
        mock_job = MagicMock()
        mock_trigger = MagicMock()
        mock_interval = MagicMock()
        mock_interval.seconds = 900  # 15 minutes
        mock_trigger.interval = mock_interval
        mock_job.trigger = mock_trigger
        mock_scheduler_instance.get_job.return_value = mock_job
        
        # Create app instance
        app = LinuxEDRApp()
        app.output_file = "test.json"  # Set output file to trigger save_json
        app.config.get.side_effect = lambda section, option, default=None: {
            ("ADVANCED", "include_raw_events"): True,
            ("ADVANCED", "max_summary_lines"): 100
        }.get((section, option), default)
        
        # Call _summarize
        app._summarize()
        
        # Verify events were retrieved from aggregator
        mock_agg_instance.snapshot_and_clear.assert_called_once()
        
        # Verify events were processed
        mock_process_raw_events.assert_called_once_with(events)
        
        # Verify build_summary was called twice (once for SummaryReport and once for Cell)
        self.assertEqual(mock_build_summary.call_count, 2)
        
        # Verify summary and cell were created
        mock_build_summary.assert_any_call(events, window_minutes=15, as_cell=False)
        mock_build_summary.assert_any_call(events, window_minutes=15, as_cell=True)
        
        # Verify process_events were set
        self.assertEqual(mock_summary.process_events, processed_events)
        self.assertEqual(mock_cell.process_events, processed_events)
        
        # Verify save_json was called
        mock_rep_instance.save_json.assert_called_once_with(
            mock_summary,
            include_raw_events=True,
            raw_events=events
        )
        
        # Verify send_llm was called
        mock_rep_instance.send_llm.assert_called_once_with(mock_summary)
        
        # Verify cell was added to report manager
        mock_rm_instance.create_cell.assert_called_once_with(mock_cell)

    @patch('linux_edr.app.Config')
    @patch('linux_edr.app.TraceReader')
    @patch('linux_edr.app.Aggregator')
    @patch('linux_edr.app.Reporter')
    @patch('linux_edr.app.ReportManager')
    @patch('linux_edr.app.BackgroundScheduler')
    @patch('linux_edr.app.logging')
    def test_summarize_no_events(self, mock_logging, mock_scheduler, mock_report_manager, 
                             mock_reporter, mock_aggregator, mock_trace_reader, mock_config):
        """Test _summarize method with no events."""
        # Setup mocks
        mock_agg_instance = mock_aggregator.return_value
        mock_rep_instance = mock_reporter.return_value
        mock_rm_instance = mock_report_manager.return_value
        
        # Mock snapshot_and_clear to return empty list
        mock_agg_instance.snapshot_and_clear.return_value = []
        
        # Create app instance
        app = LinuxEDRApp()
        
        # Call _summarize
        app._summarize()
        
        # Verify events were retrieved from aggregator
        mock_agg_instance.snapshot_and_clear.assert_called_once()
        
        # Verify build_summary was not called (no events)
        mock_rep_instance.save_json.assert_not_called()
        mock_rep_instance.send_llm.assert_not_called()
        mock_rm_instance.create_cell.assert_not_called()
        
        # Verify info was logged
        mock_logging.info.assert_any_call("No events to summarize")

    @patch('linux_edr.app.Config')
    @patch('linux_edr.app.TraceReader')
    @patch('linux_edr.app.Aggregator')
    @patch('linux_edr.app.Reporter')
    @patch('linux_edr.app.ReportManager')
    @patch('linux_edr.app.BackgroundScheduler')
    @patch('linux_edr.app.build_summary')
    @patch('linux_edr.app.process_raw_events')
    def test_summarize_large_event_count(self, mock_process_raw_events, mock_build_summary, 
                                      mock_scheduler, mock_report_manager, mock_reporter, 
                                      mock_aggregator, mock_trace_reader, mock_config):
        """Test _summarize method with more events than max_summary_lines."""
        # Setup mocks
        mock_agg_instance = mock_aggregator.return_value
        mock_rep_instance = mock_reporter.return_value
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
        mock_summary = MagicMock()
        mock_cell = MagicMock()
        mock_build_summary.side_effect = [mock_summary, mock_cell]
        
        # Mock scheduler.get_job().trigger.interval.seconds
        mock_job = MagicMock()
        mock_trigger = MagicMock()
        mock_interval = MagicMock()
        mock_interval.seconds = 900  # 15 minutes
        mock_trigger.interval = mock_interval
        mock_job.trigger = mock_trigger
        mock_scheduler_instance.get_job.return_value = mock_job
        
        # Create app instance
        app = LinuxEDRApp()
        app.output_file = "test.json"  # Set output file to trigger save_json
        app.config.get.side_effect = lambda section, option, default=None: {
            ("ADVANCED", "include_raw_events"): True,
            ("ADVANCED", "max_summary_lines"): 100  # Set max lines to 100
        }.get((section, option), default)
        
        # Call _summarize
        app._summarize()
        
        # Verify save_json was called, but raw_events should be None because event count > max_lines
        mock_rep_instance.save_json.assert_called_once_with(
            mock_summary,
            include_raw_events=False,
            raw_events=None
        )


if __name__ == "__main__":
    unittest.main() 