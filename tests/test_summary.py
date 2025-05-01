import unittest
from datetime import datetime, timezone, timedelta
from linux_edr.summary import build_summary
from linux_edr.models import Cell, SummaryReport


class TestSummary(unittest.TestCase):
    def test_build_summary_summaryreport(self):
        # Sample events
        events = [
            {"timestamp": "123456", "pid": 1000, "command": "ls", "args": ["-la"]},
            {"timestamp": "123457", "pid": 1001, "command": "cat", "args": ["/etc/passwd"]},
            {"timestamp": "123458", "pid": 1002, "command": "ls", "args": ["/tmp"]},
        ]

        # Build summary with 5-minute window (default: SummaryReport)
        summary = build_summary(events, window_minutes=5, as_cell=False)
        self.assertIsInstance(summary, SummaryReport)

        # Basic validations
        self.assertEqual(summary.total, 3)
        self.assertEqual(summary.command_counts["ls"], 2)
        self.assertEqual(summary.command_counts["cat"], 1)

        # Validate timestamps
        now = datetime.now(timezone.utc)
        summary_end = datetime.fromisoformat(summary.window_end)
        summary_start = datetime.fromisoformat(summary.window_start)

        # Time window should be 5 minutes
        self.assertAlmostEqual((summary_end - summary_start).total_seconds(), 5 * 60, delta=2)

    def test_build_summary_cell(self):
        # Sample events
        events = [
            {"timestamp": "123456", "pid": 1000, "command": "ls", "args": ["-la"]},
            {"timestamp": "123457", "pid": 1001, "command": "cat", "args": ["/etc/passwd"]},
            {"timestamp": "123458", "pid": 1002, "command": "ls", "args": ["/tmp"]},
        ]

        # Build summary as Cell
        cell = build_summary(events, window_minutes=5, as_cell=True)
        self.assertIsInstance(cell, Cell)

        # Basic validations
        self.assertEqual(cell.total, 3)
        self.assertEqual(cell.command_counts["ls"], 2)
        self.assertEqual(cell.command_counts["cat"], 1)

        # Validate timestamps
        now = datetime.now(timezone.utc)
        cell_end = datetime.fromisoformat(cell.window_end)
        cell_start = datetime.fromisoformat(cell.window_start)

        # Time window should be 5 minutes
        self.assertAlmostEqual((cell_end - cell_start).total_seconds(), 5 * 60, delta=2)

    def test_build_summary_empty(self):
        # Test with empty events list
        events = []
        window_minutes = 15

        # Build summary
        summary = build_summary(events, window_minutes, as_cell=False)

        # Verify structure and content
        self.assertIsInstance(summary, SummaryReport)
        self.assertEqual(summary.total, 0)
        self.assertEqual(summary.command_counts, {})

        # Time window should be reasonable
        now = datetime.now(timezone.utc)
        summary_end = datetime.fromisoformat(summary.window_end)
        summary_start = datetime.fromisoformat(summary.window_start)
        self.assertLess(abs((now - summary_end).total_seconds()), 10)  # Within 10 seconds
        self.assertAlmostEqual(
            (summary_end - summary_start).total_seconds(),
            window_minutes * 60,
            delta=10,  # Allow 10 seconds tolerance
        )

    def test_build_summary_with_events(self):
        # Test with some events
        events = [
            {"command": "ls", "args": ["-la"], "pid": 1000, "timestamp": "123456"},
            {"command": "ls", "args": ["/tmp"], "pid": 1001, "timestamp": "123457"},
            {"command": "cat", "args": ["/etc/passwd"], "pid": 1002, "timestamp": "123458"},
            {"command": "cat", "args": ["/etc/hosts"], "pid": 1003, "timestamp": "123459"},
            {
                "command": "grep",
                "args": ["user", "/etc/passwd"],
                "pid": 1004,
                "timestamp": "123460",
            },
        ]
        window_minutes = 15

        # Build summary
        summary = build_summary(events, window_minutes, as_cell=False)

        # Verify structure and content
        self.assertIsInstance(summary, SummaryReport)
        self.assertEqual(summary.total, 5)
        self.assertEqual(summary.command_counts["ls"], 2)
        self.assertEqual(summary.command_counts["cat"], 2)
        self.assertEqual(summary.command_counts["grep"], 1)

    def test_build_summary_as_cell(self):
        # Test with as_cell=True
        events = [
            {"command": "ls", "args": ["-la"], "pid": 1000, "timestamp": "123456"},
            {"command": "cat", "args": ["/etc/passwd"], "pid": 1002, "timestamp": "123458"},
        ]
        window_minutes = 30

        # Build summary as cell
        cell = build_summary(events, window_minutes, as_cell=True)

        # Verify it's a Cell instance
        self.assertIsInstance(cell, Cell)
        self.assertEqual(cell.total, 2)

        # Verify window is 30 minutes
        cell_end = datetime.fromisoformat(cell.window_end)
        cell_start = datetime.fromisoformat(cell.window_start)
        self.assertAlmostEqual(
            (cell_end - cell_start).total_seconds(), window_minutes * 60, delta=10
        )

    def test_build_summary_command_counts(self):
        # Test with multiple events from the same command to check counting
        events = [
            {"command": "ls", "args": ["-la"], "pid": 1000},
            {"command": "ls", "args": ["/tmp"], "pid": 1001},
            {"command": "ls", "args": ["/home"], "pid": 1002},
            {"command": "cat", "args": ["/etc/passwd"], "pid": 1003},
            {"command": "cat", "args": ["/etc/hosts"], "pid": 1004},
            {"command": "grep", "args": ["user", "/etc/passwd"], "pid": 1005},
            {"command": "ls", "args": ["-la", "/var"], "pid": 1006},
        ]

        # Build summary
        summary = build_summary(events, window_minutes=15, as_cell=False)

        # Verify command counts
        self.assertEqual(summary.command_counts["ls"], 4)
        self.assertEqual(summary.command_counts["cat"], 2)
        self.assertEqual(summary.command_counts["grep"], 1)
        self.assertEqual(len(summary.command_counts), 3)  # Only these 3 commands

    def test_build_summary_with_missing_command(self):
        # Test with events missing 'command' field
        events = [
            {"command": "ls", "args": ["-la"], "pid": 1000},
            {"command": "cat", "args": ["/etc/hosts"], "pid": 1004},
        ]

        # Build summary
        summary = build_summary(events, window_minutes=15, as_cell=False)

        # Verify structure and content - should skip invalid events
        self.assertEqual(summary.total, 2)  # Total valid events
        self.assertEqual(len(summary.command_counts), 2)  # ls and cat
        self.assertEqual(summary.command_counts["ls"], 1)
        self.assertEqual(summary.command_counts["cat"], 1)


if __name__ == "__main__":
    unittest.main()
