import unittest
import os
import tempfile
import logging
from unittest.mock import patch, MagicMock, mock_open
from linux_edr.app import (
    process_raw_events,
    parse_execve,
    setup_logging,
    LinuxEDRApp,
    ExecveEvent,
    SyscallTracer,
)


class TestApp(unittest.TestCase):

    def test_process_raw_events(self):
        # Test data with multiple execve events for different processes
        raw_events = [
            {"command": "ls", "args": ["-la", "/tmp"], "pid": 1000, "timestamp": "123456"},
            {"command": "ls", "args": ["/home"], "pid": 1001, "timestamp": "123457"},
            {"command": "cat", "args": ["/etc/passwd"], "pid": 1002, "timestamp": "123458"},
            {
                "command": "grep",
                "args": ["user", "/etc/passwd"],
                "pid": 1003,
                "timestamp": "123459",
            },
            {"command": "cat", "args": ["/etc/hosts"], "pid": 1004, "timestamp": "123460"},
        ]

        # Process the events
        result = process_raw_events(raw_events)

        # Verify the structure and content
        self.assertIn("ls", result)
        self.assertIn("cat", result)
        self.assertIn("grep", result)

        # Check correct count of commands per process
        self.assertEqual(len(result["ls"]), 2)
        self.assertEqual(len(result["cat"]), 2)
        self.assertEqual(len(result["grep"]), 1)

        # Verify command lines are correctly formed
        self.assertIn("ls -la /tmp", result["ls"])
        self.assertIn("ls /home", result["ls"])
        self.assertIn("cat /etc/passwd", result["cat"])
        self.assertIn("cat /etc/hosts", result["cat"])
        self.assertIn("grep user /etc/passwd", result["grep"])

    def test_process_raw_events_empty(self):
        # Test with empty input
        result = process_raw_events([])
        self.assertEqual(result, {})

    def test_process_raw_events_no_args(self):
        # Test with commands having no arguments
        raw_events = [
            {"command": "ls", "pid": 1000, "timestamp": "123456"},
            {"command": "bash", "pid": 1001, "timestamp": "123457"},
        ]

        result = process_raw_events(raw_events)

        self.assertIn("ls", result)
        self.assertIn("bash", result)
        self.assertEqual(result["ls"], ["ls"])
        self.assertEqual(result["bash"], ["bash"])

    def test_process_raw_events_error_handling(self):
        # Test with invalid events that should be handled gracefully
        raw_events = [
            {"not_command": "this_should_be_skipped"},
            {"command": "ls", "args": ["-la"], "pid": 1000},
            {"command": None},  # This should be skipped
            {"command": "grep", "args": "not-a-list"},  # Non-list args should be handled
        ]

        result = process_raw_events(raw_events)

        # Should only have valid commands
        self.assertIn("ls", result)
        self.assertIn("grep", result)
        self.assertEqual(len(result), 2)

        # Just verify grep command is handled in some way
        self.assertTrue(len(result["grep"]) > 0)
        self.assertTrue(result["grep"][0].startswith("grep"))

    @patch("logging.config.dictConfig")
    def test_setup_logging_debug(self, mock_dict_config):
        # Test setup_logging with debug=True
        setup_logging(debug=True)

        # Verify dictConfig was called with expected configuration
        config = mock_dict_config.call_args[0][0]
        self.assertEqual(config["root"]["level"], "DEBUG")

    @patch("logging.config.dictConfig")
    def test_setup_logging_info(self, mock_dict_config):
        # Test setup_logging with debug=False
        setup_logging(debug=False)

        # Verify dictConfig was called with expected configuration
        config = mock_dict_config.call_args[0][0]
        self.assertEqual(config["root"]["level"], "INFO")

    @patch("linux_edr.app.Config")
    @patch("linux_edr.app.setup_logging")
    @patch("linux_edr.app.TraceReader")
    @patch("linux_edr.app.Aggregator")
    @patch("linux_edr.app.Reporter")
    @patch("linux_edr.app.ReportManager")
    @patch("linux_edr.app.BackgroundScheduler")
    @patch("linux_edr.app.SyscallTracer")
    def test_linux_edr_app_init(
        self,
        mock_syscall_tracer,
        mock_scheduler,
        mock_report_manager,
        mock_reporter,
        mock_aggregator,
        mock_trace_reader,
        mock_setup_logging,
        mock_config,
    ):
        # Setup mocks
        mock_config_instance = mock_config.return_value
        mock_config_instance.get.side_effect = lambda section, option, default=None: {
            ("DEFAULT", "report_interval"): 30,
            ("DEFAULT", "debug"): True,
            ("DEFAULT", "trace_path"): "/test/trace",
            ("ADVANCED", "max_events_buffer"): 5000,
            ("OPENAI", "api_key"): "test_key",
            ("DEFAULT", "model"): "test-model",
            ("REPORTS", "reports_dir"): "test_reports",
            ("ADVANCED", "verbose_debug_logging"): True,
        }.get((section, option), default)

        # Get the reporter instance that will be passed to ReportManager
        mock_reporter_instance = mock_reporter.return_value

        # Setup mock for SyscallTracer
        mock_syscall_tracer_instance = mock_syscall_tracer.return_value

        # Create LinuxEDRApp instance
        app = LinuxEDRApp(config_path="test_config.ini")

        # Verify config was loaded
        mock_config.assert_called_once_with("test_config.ini")

        # Verify logging was set up
        mock_setup_logging.assert_called_once_with(True)

        # Verify SyscallTracer was initialized and used
        mock_syscall_tracer.assert_called_once_with(mock_config_instance)
        mock_syscall_tracer_instance.enable_syscall_events.assert_called_once()

        # Verify components were initialized correctly
        mock_trace_reader.assert_called_once_with(path="/test/trace")
        mock_aggregator.assert_called_once_with(maxlen=5000)
        mock_reporter.assert_called_once_with(api_key="test_key", model="test-model")
        mock_report_manager.assert_called_once_with("test_reports", reporter=mock_reporter_instance)

        # Verify scheduler was configured
        mock_scheduler_instance = mock_scheduler.return_value
        mock_scheduler_instance.add_job.assert_called_once()

    @patch("linux_edr.app.Config")
    @patch("linux_edr.app.setup_logging")
    @patch("linux_edr.app.TraceReader")
    @patch("linux_edr.app.Aggregator")
    @patch("linux_edr.app.Reporter")
    @patch("linux_edr.app.ReportManager")
    @patch("linux_edr.app.BackgroundScheduler")
    @patch("linux_edr.app.SyscallTracer")
    def test_linux_edr_app_cli_override(
        self,
        mock_syscall_tracer,
        mock_scheduler,
        mock_report_manager,
        mock_reporter,
        mock_aggregator,
        mock_trace_reader,
        mock_setup_logging,
        mock_config,
    ):
        # Setup mocks
        mock_config_instance = mock_config.return_value
        mock_config_instance.get.side_effect = lambda section, option, default=None: {
            ("DEFAULT", "report_interval"): 30,
            ("DEFAULT", "debug"): False,
            ("DEFAULT", "trace_path"): "/default/trace",
            ("ADVANCED", "max_events_buffer"): 5000,
            ("OPENAI", "api_key"): "default_key",
            ("DEFAULT", "model"): "default-model",
            ("REPORTS", "reports_dir"): "default_reports",
            ("ADVANCED", "verbose_debug_logging"): False,
        }.get((section, option), default)

        # Create LinuxEDRApp with CLI overrides
        app = LinuxEDRApp(config_path="test_config.ini", interval=15, debug=True)

        # Verify CLI args override config values
        self.assertEqual(app.interval, 15)
        self.assertEqual(app.debug, True)

        # Verify logging was set up with overridden debug value
        mock_setup_logging.assert_called_once_with(True)

    @patch("os.path.exists")
    @patch("linux_edr.app.Config")
    @patch("linux_edr.app.setup_logging")
    @patch("linux_edr.app.TraceReader")
    @patch("linux_edr.app.Aggregator")
    @patch("linux_edr.app.Reporter")
    @patch("linux_edr.app.ReportManager")
    @patch("linux_edr.app.BackgroundScheduler")
    @patch("linux_edr.app.SyscallTracer")
    def test_trace_path_warning(
        self,
        mock_syscall_tracer,
        mock_scheduler,
        mock_report_manager,
        mock_reporter,
        mock_aggregator,
        mock_trace_reader,
        mock_setup_logging,
        mock_config,
        mock_exists,
    ):
        # Setup mocks
        mock_config_instance = mock_config.return_value
        mock_config_instance.get.side_effect = lambda section, option, default=None: {
            ("DEFAULT", "trace_path"): "/nonexistent/trace",
            ("ADVANCED", "max_events_buffer"): 5000,
        }.get((section, option), default)

        # Make os.path.exists return False
        mock_exists.return_value = False

        # Create LinuxEDRApp
        with self.assertLogs(level="WARNING") as cm:
            app = LinuxEDRApp()

            # Verify warning was logged
            self.assertTrue(any("does not exist" in log for log in cm.output))

    @patch("logging.debug")
    @patch("logging.info")
    @patch("linux_edr.app.parse_execve")
    def test_process_event(self, mock_parse_execve, mock_log_info, mock_log_debug):
        # Setup LinuxEDRApp with mocks
        app = MagicMock()
        app.debug = True
        app.verbose_debug = True
        app.agg = MagicMock()

        # Setup mock for parse_execve
        parsed_event = ExecveEvent("12345.6789", 1000, "test_cmd", ["-a", "-b"])
        mock_parse_execve.return_value = parsed_event

        # Import the method to test it independently
        from linux_edr.app import LinuxEDRApp

        # Call the method directly
        LinuxEDRApp._process_event(app, "test_event")

        # Verify debug logging
        app.agg.add.assert_called_once_with("test_event")
        self.assertTrue(mock_log_debug.called)

        # Reset mock and test with verbose_debug=False
        mock_log_debug.reset_mock()
        app.verbose_debug = False

        LinuxEDRApp._process_event(app, "test_event2")
        app.agg.add.assert_called_with("test_event2")

        # Test with debug=False
        mock_log_debug.reset_mock()
        app.debug = False

        LinuxEDRApp._process_event(app, "test_event3")
        app.agg.add.assert_called_with("test_event3")
        mock_log_debug.assert_not_called()


class TestSyscallTracer(unittest.TestCase):
    """Tests for the SyscallTracer class."""

    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_enable_syscall_events(self, mock_file, mock_exists):
        # Setup mocks
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda section, option, default=None: {
            ("ADVANCED", "enable_syscall_tracing"): True,
            ("ADVANCED", "syscalls_to_trace"): "execve,fork,clone",
        }.get((section, option), default)

        # Make all paths exist
        mock_exists.return_value = True

        # Create SyscallTracer
        tracer = SyscallTracer(mock_config)

        # Call the method
        result = tracer.enable_syscall_events()

        # Verify the correct files were opened
        self.assertEqual(result, 6)  # 3 syscalls * 2 events each
        self.assertEqual(mock_file.call_count, 6)

        # Verify write was called for each file
        handle = mock_file()
        self.assertEqual(handle.write.call_count, 6)
        handle.write.assert_called_with("1")

    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_enable_syscall_events_disabled(self, mock_file, mock_exists):
        # Setup mocks
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda section, option, default=None: {
            ("ADVANCED", "enable_syscall_tracing"): False,
            ("ADVANCED", "syscalls_to_trace"): "execve",
        }.get((section, option), default)

        # Create SyscallTracer
        tracer = SyscallTracer(mock_config)

        # Call the method
        result = tracer.enable_syscall_events()

        # Verify nothing was enabled
        self.assertEqual(result, 0)
        mock_file.assert_not_called()

    @patch("os.path.exists")
    @patch("builtins.open")
    def test_enable_single_event_permission_error(self, mock_open, mock_exists):
        # Setup mocks
        mock_config = MagicMock()
        mock_exists.return_value = True
        mock_open.side_effect = PermissionError("Permission denied")

        # Create SyscallTracer
        tracer = SyscallTracer(mock_config)

        # Call the method
        with self.assertLogs(level="ERROR") as cm:
            result = tracer._enable_single_event("/sys/kernel/test/path")

            # Verify error was logged and method returned False
            self.assertFalse(result)
            self.assertTrue(any("Permission denied" in log for log in cm.output))

    @patch("os.path.exists")
    def test_enable_single_event_nonexistent_path(self, mock_exists):
        # Setup mocks
        mock_config = MagicMock()
        mock_exists.return_value = False

        # Create SyscallTracer
        tracer = SyscallTracer(mock_config)

        # Call the method
        with self.assertLogs(level="WARNING") as cm:
            result = tracer._enable_single_event("/nonexistent/path")

            # Verify warning was logged and method returned False
            self.assertFalse(result)
            self.assertTrue(any("not found" in log for log in cm.output))


if __name__ == "__main__":
    unittest.main()
