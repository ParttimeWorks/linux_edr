import unittest
import os
import errno
import time
from unittest.mock import patch, MagicMock, call
from linux_edr.trace import TraceReader


class TestTraceReaderErrors(unittest.TestCase):
    """Tests for error handling in the TraceReader class."""

    @patch("os.open")
    @patch("selectors.DefaultSelector")
    @patch("linux_edr.trace.logger")
    def test_open_retry_on_ebadf(self, mock_logger, mock_selector, mock_open):
        """Test that the reader attempts to reopen on EBADF error."""
        # Initial setup
        mock_fd = 42
        mock_open.return_value = mock_fd

        # Create selector mock that will raise EBADF on first read
        mock_selector_instance = MagicMock()
        mock_selector.return_value = mock_selector_instance

        # Set up mock_key for the selector
        mock_key = MagicMock()
        mock_key.fd = mock_fd

        # First call to select returns events, but read will raise EBADF
        # Second call to select returns events with successful read
        mock_selector_instance.select.side_effect = [
            [(mock_key, 1)],  # First call returns events
            [(mock_key, 1)],  # Second call after reopen
        ]

        # Set up os.read to raise EBADF on first call, then succeed
        with patch("os.read") as mock_read:
            mock_read.side_effect = [
                OSError(errno.EBADF, "Bad file descriptor"),  # First call fails
                b"data after reopen\n",  # Second call succeeds
                b"",  # EOF to end the loop
            ]

            # Create reader
            reader = TraceReader()

            # Use with _reopen_if_needed patched to verify it's called
            with patch.object(
                reader, "_reopen_if_needed", wraps=reader._reopen_if_needed
            ) as mock_reopen:
                # Collect lines from iterator
                lines = []
                for line in reader:
                    lines.append(line)
                    if len(lines) >= 1:
                        break

                # Verify reopen was called
                mock_reopen.assert_called_once()

                # Verify data after reopen was read
                self.assertEqual(lines, ["data after reopen"])

                # Verify warning was logged about bad descriptor
                mock_logger.warning.assert_any_call("Bad file descriptor, reopening trace pipe")

    @patch("os.open")
    @patch("os.path.exists")
    @patch("selectors.DefaultSelector")
    @patch("time.sleep")
    @patch("linux_edr.trace.logger")
    def test_file_unavailable_retry(
        self, mock_logger, mock_sleep, mock_selector, mock_exists, mock_open
    ):
        """Test retrying when trace file is unavailable."""
        # Make exists return False initially, then True
        mock_exists.side_effect = [False, True]

        # Set up open to succeed on second attempt
        mock_open.side_effect = [
            OSError(errno.ENOENT, "No such file or directory"),  # First attempt fails
            42,  # Second attempt succeeds
        ]

        # Set up selector
        mock_selector_instance = MagicMock()
        mock_selector.return_value = mock_selector_instance

        # Setup for a clean exit after testing retries
        def stop_after_setup():
            # The setup_fd will be called twice, then stop the test
            if mock_open.call_count >= 2:
                raise StopIteration()

        mock_selector_instance.register.side_effect = stop_after_setup

        # Create reader - should attempt to open, fail, then retry
        with self.assertRaises(StopIteration):
            reader = TraceReader()

        # Verify sleep was called (waiting between retries)
        mock_sleep.assert_called()

        # Verify appropriate warnings were logged
        mock_logger.warning.assert_any_call(mock.ANY)

        # Verify open was called twice
        self.assertEqual(mock_open.call_count, 2)

    @patch("os.open")
    @patch("selectors.DefaultSelector")
    @patch("os.read")
    @patch("linux_edr.trace.logger")
    def test_eof_handling(self, mock_logger, mock_read, mock_selector, mock_open):
        """Test handling of EOF (empty data) from trace pipe."""
        # Initial setup
        mock_fd = 42
        mock_open.return_value = mock_fd

        # Create selector mock
        mock_selector_instance = MagicMock()
        mock_selector.return_value = mock_selector_instance

        # Set up mock_key for the selector
        mock_key = MagicMock()
        mock_key.fd = mock_fd

        # Return events from select
        mock_selector_instance.select.return_value = [(mock_key, 1)]

        # Read returns empty data (EOF)
        mock_read.return_value = b""

        # Create the reader
        reader = TraceReader()

        # Use with _reopen_if_needed patched to verify it's called on EOF
        with patch.object(
            reader, "_reopen_if_needed", wraps=reader._reopen_if_needed
        ) as mock_reopen:
            # Reset mock to ignore the call during initialization
            mock_reopen.reset_mock()

            # Collect lines - should be empty since we only return EOF
            lines = []
            for line in reader:
                lines.append(line)
                # Break to prevent infinite loop
                break

            # There should be no lines (iterator exits on EOF)
            self.assertEqual(len(lines), 0)

            # Verify warning about EOF was logged
            mock_logger.warning.assert_any_call("Received EOF on trace pipe, will reopen")

            # Verify reopen was called again after EOF
            mock_reopen.assert_called_once()

    @patch("os.open")
    @patch("os.path.exists")
    @patch("selectors.DefaultSelector")
    @patch("linux_edr.trace.logger")
    def test_reopen_if_needed_with_exception(
        self, mock_logger, mock_selector, mock_exists, mock_open
    ):
        """Test _reopen_if_needed when an exception occurs during reopen."""
        # Initial setup - first open succeeds
        mock_fd = 42
        mock_open.side_effect = [
            mock_fd,  # Initial open succeeds
            OSError(errno.EPERM, "Operation not permitted"),  # Reopen fails
        ]

        # Set up path exists
        mock_exists.return_value = True

        # Create selector mock
        mock_selector_instance = MagicMock()
        mock_selector.return_value = mock_selector_instance

        # Create the reader
        reader = TraceReader()

        # Reset the mock to track new calls
        mock_open.reset_mock()
        mock_logger.reset_mock()

        # Set fd to None to force reopen
        reader.fd = None

        # Call _reopen_if_needed - should fail but handle the exception
        result = reader._reopen_if_needed()

        # Should return False because reopen failed
        self.assertFalse(result)

        # Verify open was called
        mock_open.assert_called_once()

        # Verify error was logged
        mock_logger.error.assert_called_once()
        self.assertIn("Failed to reopen trace pipe", mock_logger.error.call_args[0][0])

    @patch("os.open")
    @patch("selectors.DefaultSelector")
    @patch("os.read")
    def test_other_oserror_handling(self, mock_read, mock_selector, mock_open):
        """Test handling of other OSErrors during read."""
        # Initial setup
        mock_fd = 42
        mock_open.return_value = mock_fd

        # Create selector mock
        mock_selector_instance = MagicMock()
        mock_selector.return_value = mock_selector_instance

        # Set up mock_key for the selector
        mock_key = MagicMock()
        mock_key.fd = mock_fd

        # Return events from select
        mock_selector_instance.select.return_value = [(mock_key, 1)]

        # Read raises an unexpected OSError
        mock_read.side_effect = OSError(errno.EPERM, "Operation not permitted")

        # Create the reader
        reader = TraceReader()

        # Patch logger to check for error logging
        with patch("linux_edr.trace.logger") as mock_logger:
            # Start iteration - should log error and continue
            # We'll break after the first iteration to avoid infinite loops
            try:
                next(iter(reader))
            except StopIteration:
                pass

            # Verify error was logged
            mock_logger.error.assert_called_once()
            self.assertIn("OS Error reading", mock_logger.error.call_args[0][0])

    @patch("os.open")
    @patch("selectors.DefaultSelector")
    @patch("time.sleep")
    def test_retry_on_unexpected_exception(self, mock_sleep, mock_selector, mock_open):
        """Test that unexpected exceptions are caught and logged."""
        # Initial setup
        mock_fd = 42
        mock_open.return_value = mock_fd

        # Create selector mock that raises an unexpected exception
        mock_selector_instance = MagicMock()
        mock_selector.return_value = mock_selector_instance

        # Make select raise an unexpected exception
        mock_selector_instance.select.side_effect = Exception("Unexpected error")

        # Create the reader
        reader = TraceReader()

        # Patch logger to check error logging
        with patch("linux_edr.trace.logger") as mock_logger:
            # We only want to test one iteration to avoid infinite loops
            try:
                # Force StopIteration after checking the error handling
                mock_selector_instance.select.side_effect = [
                    Exception("Unexpected error"),
                    StopIteration(),
                ]

                # Start iteration - should log error and continue
                next(iter(reader))
            except StopIteration:
                pass

            # Verify error was logged
            mock_logger.error.assert_called_once()
            self.assertIn("Unexpected error in trace reader", mock_logger.error.call_args[0][0])

            # Verify sleep was called to avoid tight loops
            mock_sleep.assert_called_once()


if __name__ == "__main__":
    unittest.main()
