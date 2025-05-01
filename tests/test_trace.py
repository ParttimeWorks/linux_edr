import unittest
import os
import io
import time
import tempfile
from unittest.mock import patch, MagicMock, mock_open
from linux_edr.trace import TraceReader


class TestTraceReader(unittest.TestCase):
    """Tests for the TraceReader class that reads from the kernel trace pipe."""

    @patch('os.open')
    @patch('os.path.exists')
    @patch('selectors.DefaultSelector')
    def test_init_success(self, mock_selector, mock_exists, mock_open):
        """Test successful initialization of TraceReader."""
        mock_exists.return_value = True
        mock_fd = 42
        mock_open.return_value = mock_fd
        mock_selector_instance = MagicMock()
        mock_selector.return_value = mock_selector_instance

        reader = TraceReader(path="/test/trace_path")

        # Verify the file was opened correctly
        mock_open.assert_called_once()
        self.assertEqual(reader.fd, mock_fd)
        
        # Verify the selector was set up correctly
        mock_selector_instance.register.assert_called_once_with(mock_fd, unittest.mock.ANY)

    @patch('os.open')
    @patch('os.path.exists')
    def test_init_path_not_exists(self, mock_exists, mock_open):
        """Test initialization with a path that doesn't exist but should still try to open."""
        mock_exists.return_value = False
        mock_fd = 42
        mock_open.return_value = mock_fd
        
        # Mock selectors to prevent the error
        with patch('selectors.DefaultSelector') as mock_selector:
            mock_selector_instance = MagicMock()
            mock_selector.return_value = mock_selector_instance
            
            # Need to prevent the OSError in the test
            with patch('linux_edr.trace.logger') as mock_logger:
                reader = TraceReader(path="/nonexistent/path")
                
                # Verify warning was logged correctly
                mock_logger.warning.assert_called_once()
                # Check the warning message content
                self.assertIn("does not exist", mock_logger.warning.call_args[0][0])

        # Should still try to open the file
        mock_open.assert_called_once()

    @patch('os.open')
    @patch('selectors.DefaultSelector')
    def test_init_permission_denied(self, mock_selector, mock_open):
        """Test initialization with permission denied error."""
        mock_open.side_effect = PermissionError("Permission denied")
        
        with self.assertRaises(PermissionError):
            reader = TraceReader()

    @patch('os.open')
    @patch('os.close')
    @patch('selectors.DefaultSelector')
    def test_close(self, mock_selector, mock_close, mock_open):
        """Test close method properly cleans up resources."""
        mock_fd = 42
        mock_open.return_value = mock_fd
        mock_selector_instance = MagicMock()
        mock_selector.return_value = mock_selector_instance
        
        reader = TraceReader()
        reader.close()
        
        # Verify resources were cleaned up
        mock_selector_instance.unregister.assert_called_once_with(mock_fd)
        mock_close.assert_called_once_with(mock_fd)
        self.assertIsNone(reader.fd)
        
        # Second close should not raise
        reader.close()

    @patch('os.open')
    @patch('os.read')
    @patch('selectors.DefaultSelector')
    def test_iteration(self, mock_selector, mock_read, mock_open):
        """Test iteration over trace lines."""
        mock_fd = 42
        mock_open.return_value = mock_fd
        
        # Set up selector to return events when select is called
        mock_selector_instance = MagicMock()
        mock_selector.return_value = mock_selector_instance
        
        # Mock the select method to return some events
        mock_key = MagicMock()
        mock_key.fd = mock_fd
        mock_selector_instance.select.return_value = [(mock_key, 1)]
        
        # Mock the read method to return some data then EOF
        mock_read.side_effect = [
            b"line1\nline2\n",
            b"line3\n",
            b""  # EOF
        ]
        
        reader = TraceReader()
        
        # Use a list to collect lines from the iterator
        lines = []
        for line in reader:
            lines.append(line)
            if len(lines) >= 3:
                break
        
        # Verify lines were read correctly
        self.assertEqual(lines, ["line1", "line2", "line3"])

    @patch('os.open')
    @patch('os.read')
    @patch('selectors.DefaultSelector')
    def test_unicode_decode_error(self, mock_selector, mock_read, mock_open):
        """Test handling of Unicode decode errors."""
        mock_fd = 42
        mock_open.return_value = mock_fd
        
        # Set up selector
        mock_selector_instance = MagicMock()
        mock_selector.return_value = mock_selector_instance
        mock_key = MagicMock()
        mock_key.fd = mock_fd
        mock_selector_instance.select.return_value = [(mock_key, 1)]
        
        # Mock read to return invalid UTF-8
        mock_read.return_value = b"\xff\xfe Invalid UTF-8 \xfe\xff"
        
        reader = TraceReader()
        
        # Should not raise but replace invalid chars
        lines = []
        for line in reader:
            lines.append(line)
            break
        
        # Verify line was read and invalid characters were replaced
        self.assertEqual(len(lines), 1)
        self.assertIn("Invalid UTF-8", lines[0])

    @patch('os.open')
    @patch('os.read')
    @patch('selectors.DefaultSelector')
    def test_eagain_handling(self, mock_selector, mock_read, mock_open):
        """Test handling of EAGAIN errors."""
        mock_fd = 42
        mock_open.return_value = mock_fd
        
        # Set up selector
        mock_selector_instance = MagicMock()
        mock_selector.return_value = mock_selector_instance
        mock_key = MagicMock()
        mock_key.fd = mock_fd
        mock_selector_instance.select.return_value = [(mock_key, 1)]
        
        # Mock read to raise EAGAIN once then return data
        import errno
        mock_read.side_effect = [
            OSError(errno.EAGAIN, "Resource temporarily unavailable"),
            b"line1\n",
            b""  # EOF to end the loop
        ]
        
        reader = TraceReader()
        
        # Should handle EAGAIN and continue
        lines = []
        for line in reader:
            lines.append(line)
            break
        
        # Verify line was read after EAGAIN
        self.assertEqual(lines, ["line1"])
    
    @patch('os.open')
    @patch('os.read')
    @patch('selectors.DefaultSelector')
    def test_reopen_if_needed(self, mock_selector, mock_read, mock_open):
        """Test that _reopen_if_needed works correctly."""
        # Initial setup
        mock_fd = 42
        mock_open.return_value = mock_fd
        mock_selector_instance = MagicMock()
        mock_selector.return_value = mock_selector_instance
        
        reader = TraceReader()
        
        # Reset mocks for _reopen_if_needed test
        mock_open.reset_mock()
        mock_selector_instance.reset_mock()
        
        # Simulate closed file descriptor
        reader.fd = None
        
        # Call _reopen_if_needed
        result = reader._reopen_if_needed()
        
        # Verify file was reopened
        self.assertTrue(result)
        mock_open.assert_called_once()
        mock_selector_instance.register.assert_called_once()


if __name__ == "__main__":
    unittest.main() 