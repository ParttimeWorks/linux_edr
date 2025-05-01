import unittest
from datetime import datetime, timezone
from linux_edr.models import (
    CommandLine, ProcessEvents, SummaryReport, 
    Cell, Block, DailyReport, WeeklyReport, MonthlyReport
)


class TestModels(unittest.TestCase):
    """Tests for the data model classes."""

    def test_command_line(self):
        """Test CommandLine model."""
        # Basic initialization
        cmd = CommandLine(
            command="ls",
            args=["-la", "/tmp"],
            pid=1234,
            timestamp="123456.789"
        )
        
        # Test attributes
        self.assertEqual(cmd.command, "ls")
        self.assertEqual(cmd.args, ["-la", "/tmp"])
        self.assertEqual(cmd.pid, 1234)
        self.assertEqual(cmd.timestamp, "123456.789")
        
        # Test to_string method
        self.assertEqual(cmd.to_string(), "ls -la /tmp")
        
        # Test without args
        cmd_no_args = CommandLine(
            command="bash",
            pid=5678,
            timestamp="987654.321"
        )
        self.assertEqual(cmd_no_args.to_string(), "bash")

    def test_process_events(self):
        """Test ProcessEvents model."""
        # Create some command lines
        cmd1 = CommandLine(command="ls", args=["-la"], pid=1234, timestamp="123456")
        cmd2 = CommandLine(command="ls", args=["/tmp"], pid=1235, timestamp="123457")
        
        # Create process events
        proc_events = ProcessEvents(
            process_name="ls",
            executions=[cmd1, cmd2]
        )
        
        # Test attributes
        self.assertEqual(proc_events.process_name, "ls")
        self.assertEqual(len(proc_events.executions), 2)
        self.assertEqual(proc_events.executions[0].command, "ls")
        self.assertEqual(proc_events.executions[1].args, ["/tmp"])

    def test_summary_report(self):
        """Test SummaryReport model."""
        # Initialize with all required fields
        report = SummaryReport(
            report_id="test123",
            window_start="2023-01-01T00:00:00+00:00",
            window_end="2023-01-01T00:15:00+00:00",
            total=10,
            command_counts={"ls": 5, "cat": 3, "grep": 2}
        )
        
        # Test attributes
        self.assertEqual(report.report_id, "test123")
        self.assertEqual(report.total, 10)
        self.assertEqual(report.command_counts["ls"], 5)
        
        # Test timestamp validation
        with self.assertRaises(ValueError):
            SummaryReport(
                report_id="test",
                window_start="invalid-date",  # Invalid
                window_end="2023-01-01T00:15:00+00:00",
                total=10,
                command_counts={}
            )
        
        # Test total validation
        with self.assertRaises(ValueError):
            SummaryReport(
                report_id="test",
                window_start="2023-01-01T00:00:00+00:00",
                window_end="2023-01-01T00:15:00+00:00",
                total=-1,  # Invalid
                command_counts={}
            )
        
        # Test to_prompt method
        prompt = report.to_prompt()
        self.assertIn("Linux EDR Report", prompt)
        self.assertIn("test123", prompt)
        self.assertIn("10", prompt)
        self.assertIn("- ls: 5", prompt)
        self.assertIn("- cat: 3", prompt)
        self.assertIn("- grep: 2", prompt)
        
        # Test with process_events
        report.process_events = {
            "ls": ["ls -la", "ls /tmp"],
            "cat": ["cat /etc/passwd"]
        }
        prompt_with_processes = report.to_prompt()
        self.assertIn("Process Details", prompt_with_processes)
        self.assertIn("### ls", prompt_with_processes)
        self.assertIn("- `ls -la`", prompt_with_processes)
        
        # Test model_dump
        dump = report.model_dump()
        self.assertIn("report_id", dump)
        self.assertIn("command_counts", dump)
        self.assertIn("process_events", dump)
        
        # None values should be excluded
        self.assertNotIn("raw_events", dump)
        self.assertNotIn("analysis", dump)

    def test_cell(self):
        """Test Cell model (inherits from SummaryReport)."""
        # Initialize Cell
        cell = Cell(
            report_id="cell123",
            window_start="2023-01-01T00:00:00+00:00",
            window_end="2023-01-01T00:15:00+00:00",
            total=5,
            command_counts={"ls": 3, "cat": 2}
        )
        
        # Test attributes (inherits from SummaryReport)
        self.assertEqual(cell.report_id, "cell123")
        self.assertEqual(cell.total, 5)
        self.assertEqual(cell.command_counts["ls"], 3)
        
        # Test to_prompt (inherited)
        prompt = cell.to_prompt()
        self.assertIn("Linux EDR Report", prompt)
        self.assertIn("cell123", prompt)

    def test_block(self):
        """Test Block model."""
        # Initialize Block
        block = Block(
            report_id="block123",
            window_start="2023-01-01T00:00:00+00:00",
            window_end="2023-01-01T04:00:00+00:00",
            total_events=50,
            cells=["cell1", "cell2", "cell3"],
            command_counts={"ls": 20, "cat": 15, "grep": 10, "find": 5},
            top_processes={"bash": 25, "python": 15, "nginx": 10}
        )
        
        # Test attributes
        self.assertEqual(block.report_id, "block123")
        self.assertEqual(block.total_events, 50)
        self.assertEqual(len(block.cells), 3)
        self.assertEqual(block.command_counts["ls"], 20)
        self.assertEqual(block.top_processes["bash"], 25)
        
        # Test timestamp validation
        with self.assertRaises(ValueError):
            Block(
                report_id="test",
                window_start="2023-01-01T00:00:00+00:00",
                window_end="invalid-date",  # Invalid
                total_events=50,
                cells=[],
                command_counts={},
                top_processes={}
            )
        
        # Test to_prompt
        prompt = block.to_prompt()
        self.assertIn("Linux EDR Block Report", prompt)
        self.assertIn("block123", prompt)
        self.assertIn("50", prompt)
        self.assertIn("ls: 20", prompt)
        self.assertIn("bash: 25", prompt)

    def test_daily_report(self):
        """Test DailyReport model."""
        # Initialize DailyReport
        daily = DailyReport(
            report_id="daily123",
            date="2023-01-01",
            window_start="2023-01-01T00:00:00+00:00",
            window_end="2023-01-01T23:59:59+00:00",
            total_events=200,
            blocks=["block1", "block2", "block3"],
            command_counts={"ls": 80, "cat": 60, "grep": 40, "find": 20},
            top_processes={"bash": 100, "python": 60, "nginx": 40},
            unusual_activity=[{"type": "high_volume", "command": "ssh", "count": 50}]
        )
        
        # Test attributes
        self.assertEqual(daily.report_id, "daily123")
        self.assertEqual(daily.date, "2023-01-01")
        self.assertEqual(daily.total_events, 200)
        self.assertEqual(len(daily.blocks), 3)
        self.assertEqual(daily.command_counts["ls"], 80)
        self.assertEqual(daily.top_processes["bash"], 100)
        self.assertEqual(len(daily.unusual_activity), 1)
        
        # Test date validation
        with self.assertRaises(ValueError):
            DailyReport(
                report_id="test",
                date="01/01/2023",  # Invalid format
                window_start="2023-01-01T00:00:00+00:00",
                window_end="2023-01-01T23:59:59+00:00",
                total_events=200,
                blocks=[],
                command_counts={},
                top_processes={}
            )
        
        # Test to_prompt
        prompt = daily.to_prompt()
        self.assertIn("Linux EDR Daily Report", prompt)
        self.assertIn("2023-01-01", prompt)
        self.assertIn("200", prompt)
        self.assertIn("Unusual Activity Detected", prompt)

    def test_weekly_report(self):
        """Test WeeklyReport model."""
        # Initialize WeeklyReport
        weekly = WeeklyReport(
            report_id="weekly123",
            week_start_date="2023-01-01",
            week_end_date="2023-01-07",
            total_events=1000,
            daily_reports=["day1", "day2", "day3", "day4", "day5", "day6", "day7"],
            command_trends={"ls": [10, 15, 12, 18, 20, 5, 8], "cat": [5, 8, 10, 12, 15, 4, 6]},
            process_trends={"bash": [50, 60, 45, 70, 80, 30, 40], "python": [20, 25, 30, 35, 40, 15, 10]},
            security_incidents=[{"type": "brute_force", "source_ip": "192.168.1.10", "attempts": 50}],
            risk_score=65
        )
        
        # Test attributes
        self.assertEqual(weekly.report_id, "weekly123")
        self.assertEqual(weekly.week_start_date, "2023-01-01")
        self.assertEqual(weekly.week_end_date, "2023-01-07")
        self.assertEqual(weekly.total_events, 1000)
        self.assertEqual(len(weekly.daily_reports), 7)
        self.assertEqual(weekly.command_trends["ls"], [10, 15, 12, 18, 20, 5, 8])
        self.assertEqual(weekly.process_trends["bash"], [50, 60, 45, 70, 80, 30, 40])
        self.assertEqual(len(weekly.security_incidents), 1)
        self.assertEqual(weekly.risk_score, 65)

    def test_monthly_report(self):
        """Test MonthlyReport model."""
        # Initialize MonthlyReport
        monthly = MonthlyReport(
            report_id="monthly123",
            month="2023-01",
            start_date="2023-01-01",
            end_date="2023-01-31",
            total_events=5000,
            weekly_reports=["week1", "week2", "week3", "week4"],
            command_summary={"ls": 1200, "cat": 800, "grep": 600, "find": 400},
            process_summary={"bash": 2000, "python": 1500, "nginx": 1000, "apache": 500},
            security_summary={"total_incidents": 10, "high_risk": 2, "medium_risk": 3, "low_risk": 5},
            risk_score=75,
            recommendations=["Update system packages", "Review SSH configurations"]
        )
        
        # Test attributes
        self.assertEqual(monthly.report_id, "monthly123")
        self.assertEqual(monthly.month, "2023-01")
        self.assertEqual(monthly.start_date, "2023-01-01")
        self.assertEqual(monthly.end_date, "2023-01-31")
        self.assertEqual(monthly.total_events, 5000)
        self.assertEqual(len(monthly.weekly_reports), 4)
        self.assertEqual(monthly.command_summary["ls"], 1200)
        self.assertEqual(monthly.process_summary["bash"], 2000)
        self.assertEqual(monthly.security_summary["total_incidents"], 10)
        self.assertEqual(monthly.risk_score, 75)
        self.assertEqual(len(monthly.recommendations), 2)
        
        # Test month format validation
        with self.assertRaises(ValueError):
            MonthlyReport(
                report_id="test",
                month="Jan 2023",  # Invalid format
                start_date="2023-01-01",
                end_date="2023-01-31",
                total_events=5000,
                weekly_reports=[],
                command_summary={},
                process_summary={},
                security_summary={},
                risk_score=50
            )


if __name__ == "__main__":
    unittest.main() 