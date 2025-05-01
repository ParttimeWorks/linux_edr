import unittest
from datetime import datetime, timedelta, timezone
from pydantic import ValidationError

from linux_edr.domain.models.reports import (
    SummaryReport, Cell, Block, DailyReport, WeeklyReport, MonthlyReport
)


class TestReportModels(unittest.TestCase):
    """Tests for the report model classes in domain/models/reports."""
    
    def test_summary_report_validation(self):
        """Test SummaryReport validation."""
        # Test valid summary report
        summary = SummaryReport(
            report_id="test_summary",
            window_start="2023-01-01T00:00:00+00:00",
            window_end="2023-01-01T00:15:00+00:00",
            total=5,
            command_counts={"ls": 3, "cat": 2},
            process_events={"bash": ["ls -la", "cat file.txt"]},
            severity=3
        )
        
        self.assertEqual(summary.report_id, "test_summary")
        self.assertEqual(summary.severity, 3)
        
        # Test invalid timestamp
        with self.assertRaises(ValidationError):
            SummaryReport(
                report_id="test_invalid",
                window_start="invalid_time",  # Invalid timestamp
                window_end="2023-01-01T00:15:00+00:00",
                total=5,
                command_counts={"ls": 3}
            )
            
        # Test invalid total (negative)
        with self.assertRaises(ValidationError):
            SummaryReport(
                report_id="test_invalid",
                window_start="2023-01-01T00:00:00+00:00",
                window_end="2023-01-01T00:15:00+00:00",
                total=-5,  # Negative total
                command_counts={"ls": 3}
            )
            
        # Test invalid severity (out of range)
        with self.assertRaises(ValidationError):
            SummaryReport(
                report_id="test_invalid",
                window_start="2023-01-01T00:00:00+00:00",
                window_end="2023-01-01T00:15:00+00:00",
                total=5,
                command_counts={"ls": 3},
                severity=6  # Out of range (1-5)
            )
    
    def test_summary_report_to_prompt(self):
        """Test SummaryReport to_prompt method."""
        # Create a summary report with process events
        summary = SummaryReport(
            report_id="test_summary",
            window_start="2023-01-01T00:00:00+00:00",
            window_end="2023-01-01T00:15:00+00:00",
            total=10,
            command_counts={"ls": 6, "cat": 4},
            process_events={"bash": ["ls -la", "cat file.txt"]}
        )
        
        # Generate prompt
        prompt = summary.to_prompt()
        
        # Verify prompt content
        self.assertIn("test_summary", prompt)
        self.assertIn("2023-01-01T00:00:00+00:00", prompt)
        self.assertIn("Total Events: 10", prompt)
        self.assertIn("ls: 6", prompt)
        self.assertIn("cat: 4", prompt)
        self.assertIn("Process Details", prompt)
        self.assertIn("bash", prompt)
        
        # Test with many process events (should limit to 10)
        many_commands = [f"cmd_{i}" for i in range(15)]
        summary.process_events = {"test_process": many_commands}
        prompt = summary.to_prompt()
        self.assertIn("more executions", prompt)
    
    def test_cell_inheritance(self):
        """Test Cell inherits correctly from SummaryReport."""
        # Create a Cell instance
        cell = Cell(
            report_id="test_cell",
            window_start="2023-01-01T00:00:00+00:00",
            window_end="2023-01-01T00:15:00+00:00",
            total=5,
            command_counts={"ls": 3, "cat": 2}
        )
        
        # Verify it has all SummaryReport attributes and methods
        self.assertEqual(cell.report_id, "test_cell")
        self.assertEqual(cell.total, 5)
        self.assertIsNotNone(cell.to_prompt())
        self.assertIsNotNone(cell.model_dump())
    
    def test_block_validation(self):
        """Test Block validation."""
        # Test valid block
        block = Block(
            report_id="test_block",
            window_start="2023-01-01T00:00:00+00:00",
            window_end="2023-01-01T04:00:00+00:00",
            total_events=100,
            cells=["cell_1", "cell_2", "cell_3"],
            command_counts={"ls": 50, "cat": 30, "grep": 20},
            top_processes={"bash": 60, "python": 40}
        )
        
        self.assertEqual(block.report_id, "test_block")
        self.assertEqual(len(block.cells), 3)
        
        # Test invalid timestamp
        with self.assertRaises(ValidationError):
            Block(
                report_id="test_invalid",
                window_start="invalid_time",  # Invalid timestamp
                window_end="2023-01-01T04:00:00+00:00",
                total_events=100,
                cells=["cell_1"],
                command_counts={"ls": 50},
                top_processes={"bash": 60}
            )
    
    def test_block_to_prompt(self):
        """Test Block to_prompt method."""
        block = Block(
            report_id="test_block",
            window_start="2023-01-01T00:00:00+00:00",
            window_end="2023-01-01T04:00:00+00:00",
            total_events=100,
            cells=["cell_1", "cell_2", "cell_3"],
            command_counts={"ls": 50, "cat": 30, "grep": 20},
            top_processes={"bash": 60, "python": 40}
        )
        
        # Generate prompt
        prompt = block.to_prompt()
        
        # Verify prompt content
        self.assertIn("test_block", prompt)
        self.assertIn("2023-01-01T00:00:00+00:00", prompt)
        self.assertIn("Total Events: 100", prompt)
        self.assertIn("Cells Included: 3", prompt)
        self.assertIn("ls: 50", prompt)
        self.assertIn("bash: 60", prompt)
    
    def test_daily_report_validation(self):
        """Test DailyReport validation."""
        # Test valid daily report
        daily = DailyReport(
            report_id="daily_20230101",
            date="2023-01-01",
            window_start="2023-01-01T00:00:00+00:00",
            window_end="2023-01-01T23:59:59+00:00",
            total_events=1000,
            blocks=["block_1", "block_2", "block_3"],
            command_counts={"ls": 500, "cat": 300, "grep": 200},
            top_processes={"bash": 600, "python": 400}
        )
        
        self.assertEqual(daily.report_id, "daily_20230101")
        self.assertEqual(daily.date, "2023-01-01")
        
        # Test invalid date format
        with self.assertRaises(ValidationError):
            DailyReport(
                report_id="daily_invalid",
                date="01/01/2023",  # Invalid date format (should be YYYY-MM-DD)
                window_start="2023-01-01T00:00:00+00:00",
                window_end="2023-01-01T23:59:59+00:00",
                total_events=1000,
                blocks=["block_1"],
                command_counts={"ls": 500},
                top_processes={"bash": 600}
            )
    
    def test_daily_report_to_prompt(self):
        """Test DailyReport to_prompt method."""
        # Create daily report with unusual activity
        daily = DailyReport(
            report_id="daily_20230101",
            date="2023-01-01",
            window_start="2023-01-01T00:00:00+00:00",
            window_end="2023-01-01T23:59:59+00:00",
            total_events=1000,
            blocks=["block_1", "block_2", "block_3"],
            command_counts={"ls": 500, "cat": 300, "grep": 200},
            top_processes={"bash": 600, "python": 400},
            unusual_activity=[
                {
                    "time_window": "2023-01-01T12:00:00+00:00 to 2023-01-01T16:00:00+00:00",
                    "severity": 4,
                    "summary": "Suspicious activity detected"
                }
            ]
        )
        
        # Generate prompt
        prompt = daily.to_prompt()
        
        # Verify prompt content
        self.assertIn("2023-01-01", prompt)
        self.assertIn("Total Events: 1000", prompt)
        self.assertIn("Blocks Included: 3", prompt)
        self.assertIn("ls: 500", prompt)
        self.assertIn("bash: 600", prompt)
        self.assertIn("Unusual Activity Detected", prompt)
        self.assertIn("Suspicious activity", prompt)
    
    def test_weekly_report_validation(self):
        """Test WeeklyReport validation."""
        # Test valid weekly report
        weekly = WeeklyReport(
            report_id="weekly_20230101_20230107",
            week_start_date="2023-01-01",
            week_end_date="2023-01-07",  # 7 days (0-6)
            total_events=7000,
            daily_reports=["daily_20230101", "daily_20230102", "daily_20230103", 
                          "daily_20230104", "daily_20230105", "daily_20230106", "daily_20230107"],
            command_trends={"ls": [50, 60, 40, 70, 80, 30, 55]},
            process_trends={"bash": [60, 70, 50, 80, 90, 40, 65]},
            risk_score=70
        )
        
        self.assertEqual(weekly.report_id, "weekly_20230101_20230107")
        self.assertEqual(weekly.week_start_date, "2023-01-01")
        self.assertEqual(weekly.week_end_date, "2023-01-07")
        
        # Test invalid date range (not 7 days)
        with self.assertRaises(ValidationError):
            WeeklyReport(
                report_id="weekly_invalid",
                week_start_date="2023-01-01",
                week_end_date="2023-01-10",  # 10 days (should be 7)
                total_events=7000,
                daily_reports=["daily_20230101"],
                command_trends={"ls": [50]},
                process_trends={"bash": [60]},
                risk_score=70
            )
    
    def test_weekly_report_to_prompt(self):
        """Test WeeklyReport to_prompt method."""
        # Create weekly report with security incidents
        weekly = WeeklyReport(
            report_id="weekly_20230101_20230107",
            week_start_date="2023-01-01",
            week_end_date="2023-01-07",
            total_events=7000,
            daily_reports=["daily_20230101", "daily_20230102", "daily_20230103", 
                          "daily_20230104", "daily_20230105", "daily_20230106", "daily_20230107"],
            command_trends={"ls": [50, 60, 40, 70, 80, 30, 55]},
            process_trends={"bash": [60, 70, 50, 80, 90, 40, 65]},
            security_incidents=[
                {
                    "date": "2023-01-03",
                    "details": {"severity": 4, "summary": "Suspicious login attempt"},
                    "risk_level": "high"
                }
            ],
            risk_score=70
        )
        
        # Generate prompt
        prompt = weekly.to_prompt()
        
        # Verify prompt content
        self.assertIn("2023-01-01 to 2023-01-07", prompt)
        self.assertIn("Total Events: 7000", prompt)
        self.assertIn("Risk Score: 70/100", prompt)
        self.assertIn("Security Incidents", prompt)
        self.assertIn("date: 2023-01-03", prompt)
        self.assertIn("risk_level: high", prompt)
    
    def test_monthly_report_validation(self):
        """Test MonthlyReport validation."""
        # Test valid monthly report
        monthly = MonthlyReport(
            report_id="monthly_202301",
            month="2023-01",
            start_date="2023-01-01",
            end_date="2023-01-31",
            total_events=30000,
            weekly_reports=["weekly_20230101_20230107", "weekly_20230108_20230114", 
                          "weekly_20230115_20230121", "weekly_20230122_20230128"],
            command_summary={"ls": 15000, "cat": 10000, "grep": 5000},
            process_summary={"bash": 18000, "python": 12000},
            security_summary={"total_incidents": 5, "high_risk_incidents": 2, 
                             "medium_risk_incidents": 2, "low_risk_incidents": 1},
            risk_score=75
        )
        
        self.assertEqual(monthly.report_id, "monthly_202301")
        self.assertEqual(monthly.month, "2023-01")
        
        # Test invalid month format
        with self.assertRaises(ValidationError):
            MonthlyReport(
                report_id="monthly_invalid",
                month="01/2023",  # Invalid month format (should be YYYY-MM)
                start_date="2023-01-01",
                end_date="2023-01-31",
                total_events=30000,
                weekly_reports=["weekly_20230101_20230107"],
                command_summary={"ls": 15000},
                process_summary={"bash": 18000},
                security_summary={"total_incidents": 5},
                risk_score=75
            )
            
        # Test start date doesn't match month
        with self.assertRaises(ValidationError):
            MonthlyReport(
                report_id="monthly_invalid",
                month="2023-01",
                start_date="2023-02-01",  # Different month
                end_date="2023-02-28",
                total_events=30000,
                weekly_reports=["weekly_20230101_20230107"],
                command_summary={"ls": 15000},
                process_summary={"bash": 18000},
                security_summary={"total_incidents": 5},
                risk_score=75
            )
            
        # Test end date before start date
        with self.assertRaises(ValidationError):
            MonthlyReport(
                report_id="monthly_invalid",
                month="2023-01",
                start_date="2023-01-15",
                end_date="2023-01-10",  # Before start date
                total_events=30000,
                weekly_reports=["weekly_20230101_20230107"],
                command_summary={"ls": 15000},
                process_summary={"bash": 18000},
                security_summary={"total_incidents": 5},
                risk_score=75
            )
    
    def test_monthly_report_to_prompt(self):
        """Test MonthlyReport to_prompt method."""
        # Create monthly report with recommendations
        monthly = MonthlyReport(
            report_id="monthly_202301",
            month="2023-01",
            start_date="2023-01-01",
            end_date="2023-01-31",
            total_events=30000,
            weekly_reports=["weekly_20230101_20230107", "weekly_20230108_20230114", 
                          "weekly_20230115_20230121", "weekly_20230122_20230128"],
            command_summary={"ls": 15000, "cat": 10000, "grep": 5000},
            process_summary={"bash": 18000, "python": 12000},
            security_summary={"total_incidents": 5, "high_risk_incidents": 2, 
                             "medium_risk_incidents": 2, "low_risk_incidents": 1},
            risk_score=75,
            recommendations=[
                "Update all system packages",
                "Implement stronger password policies", 
                "Enable 2FA for all accounts"
            ]
        )
        
        # Generate prompt
        prompt = monthly.to_prompt()
        
        # Verify prompt content
        self.assertIn("2023-01", prompt)
        self.assertIn("Date Range: 2023-01-01 to 2023-01-31", prompt)
        self.assertIn("Total Events: 30000", prompt)
        self.assertIn("Overall Risk Score: 75/100", prompt)
        self.assertIn("Security Recommendations", prompt)
        self.assertIn("Update all system packages", prompt)
        self.assertIn("Implement stronger password policies", prompt)
        self.assertIn("Enable 2FA for all accounts", prompt)


if __name__ == "__main__":
    unittest.main() 