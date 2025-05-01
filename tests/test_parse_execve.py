import unittest
from linux_edr.app import parse_execve, ExecveEvent


class TestParseExecve(unittest.TestCase):
    """Unit tests for the parse_execve helper in linux_edr.app."""

    def test_valid_execve_parsing(self):
        """A well-formed trace line should yield a populated ExecveEvent."""
        line = (
            "1618921738.123456 [1234] some-process-1234  D  0.000000: sys_enter_execve: "
            '("ls" "-la" "/tmp")'
        )
        evt = parse_execve(line)
        self.assertIsInstance(evt, ExecveEvent)
        self.assertEqual(evt.timestamp, "1618921738.123456")
        self.assertEqual(evt.pid, 1234)
        self.assertEqual(evt.command, "ls")
        # Implementation leaves quotes on any argument after the first
        self.assertEqual(evt.args, ['"-la"', '"/tmp"'])

    def test_no_execve_returns_none(self):
        """Lines that do not include an execve call should return None."""
        line = (
            "1618921738.123456 [1234] some-process-1234  D  0.000000: sys_enter_openat: "
            '("/etc/passwd")'
        )
        self.assertIsNone(parse_execve(line))

    def test_invalid_pid_returns_none(self):
        """If the PID cannot be parsed as an int, parse_execve should return None."""
        line = (
            "1618921738.123456 [notanint] some-process  D  0.000000: sys_enter_execve: "
            '("bash" "-c" "echo test")'
        )
        self.assertIsNone(parse_execve(line))

    def test_empty_line(self):
        """Empty or non-string inputs should return None without raising."""
        self.assertIsNone(parse_execve(""))
        self.assertIsNone(parse_execve(None))  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
