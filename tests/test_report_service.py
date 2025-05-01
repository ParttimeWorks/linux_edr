import unittest
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock, ANY
from datetime import datetime, timezone, timedelta
import json

from linux_edr.application.services.report_service import ReportService
from linux_edr.application.services.severity_calculator import SeverityCalculator
from linux_edr.infrastructure.repositories.report_repository import FileSystemReportRepository
from linux_edr.domain.models.reports import (
    Cell, Block, DailyReport, WeeklyReport, MonthlyReport
)


class TestReportService(unittest.TestCase):
    """Comprehensive tests for the ReportService class."""

    def setUp(self):
        # Create a temporary directory for test reports
        self.test_dir = tempfile.mkdtemp()
        
        # Create the repositories
        self.cell_repo = FileSystemReportRepository(self.test_dir, "cells")
        self.block_repo = FileSystemReportRepository(self.test_dir, "blocks")
        self.daily_repo = FileSystemReportRepository(self.test_dir, "daily")
        self.weekly_repo = FileSystemReportRepository(self.test_dir, "weekly")
        self.monthly_repo = FileSystemReportRepository(self.test_dir, "monthly")
        
        # Create the mock reporter
        self.mock_reporter = MagicMock()
        
        # Create the service
        self.service = ReportService(
            cell_repository=self.cell_repo,
            block_repository=self.block_repo,
            daily_repository=self.daily_repo,
            weekly_repository=self.weekly_repo,
            monthly_repository=self.monthly_repo,
            reporter=self.mock_reporter
        )

    def tearDown(self):
        # Clean up the temporary directory
        shutil.rmtree(self.test_dir)

    def create_test_cell(self, index=1):
        """Helper to create a test cell."""
        return Cell(
            report_id=f"test_cell_{index}",
            window_start="2023-01-01T00:00:00+00:00",
            window_end="2023-01-01T00:15:00+00:00",
            total=5 * index,
            command_counts={"ls": 3 * index, "cat": 2 * index},
            process_events={"bash": [f"command_{i}" for i in range(3)]}
        )

    def create_test_block(self, index=1):
        """Helper to create a test block."""
        cell_ids = [f"test_cell_{i}" for i in range(16)]
        
        return Block(
            report_id=f"test_block_{index}",
            window_start="2023-01-01T00:00:00+00:00",
            window_end="2023-01-01T04:00:00+00:00",
            total_events=100 * index,
            cells=cell_ids,
            command_counts={"ls": 50 * index, "cat": 30 * index, "grep": 20 * index},
            top_processes={"bash": 60 * index, "python": 40 * index}
        )
    
    def create_test_daily_report(self, index=1, date="2023-01-01"):
        """Helper to create a test daily report."""
        block_ids = [f"test_block_{i}" for i in range(6)]
        
        return DailyReport(
            report_id=f"daily_{date.replace('-', '')}",
            date=date,
            window_start=f"{date}T00:00:00+00:00",
            window_end=f"{date}T23:59:59+00:00",
            total_events=1000 * index,
            blocks=block_ids,
            command_counts={"ls": 500 * index, "cat": 300 * index, "grep": 200 * index},
            top_processes={"bash": 600 * index, "python": 400 * index},
            unusual_activity=[]
        )
    
    def create_test_weekly_report(self, index=1, start_date="2023-01-01"):
        """Helper to create a test weekly report."""
        start_dt = datetime.fromisoformat(f"{start_date}T00:00:00+00:00")
        end_dt = start_dt + timedelta(days=6)
        end_date = end_dt.strftime("%Y-%m-%d")
        
        daily_ids = [
            f"daily_{(start_dt + timedelta(days=i)).strftime('%Y%m%d')}" 
            for i in range(7)
        ]
        
        command_trends = {
            "ls": [50, 60, 40, 70, 80, 30, 55],
            "cat": [30, 35, 25, 40, 45, 20, 30],
            "grep": [20, 25, 15, 30, 35, 10, 20]
        }
        
        process_trends = {
            "bash": [60, 70, 50, 80, 90, 40, 65],
            "python": [40, 45, 30, 50, 55, 25, 35]
        }
        
        return WeeklyReport(
            report_id=f"weekly_{start_date.replace('-', '')}_{end_date.replace('-', '')}",
            week_start_date=start_date,
            week_end_date=end_date,
            total_events=7000 * index,
            daily_reports=daily_ids,
            command_trends=command_trends,
            process_trends=process_trends,
            security_incidents=[],
            risk_score=70 * index if 70 * index <= 100 else 100,
            severity=min(index, 5)
        )

    def test_add_cell(self):
        """Test adding a cell to the service."""
        # Create a cell
        cell = self.create_test_cell()
        
        # Add the cell
        self.service.add_cell(cell)
        
        # Verify that analyze_report was called
        self.mock_reporter.analyze_report.assert_called_once_with(cell)
        
        # Verify cell was saved
        saved_cell = self.cell_repo.load("test_cell_1")
        self.assertIsNotNone(saved_cell)
        self.assertEqual(saved_cell["report_id"], "test_cell_1")
        
        # Verify cell was added to recent_cells
        self.assertEqual(self.service.recent_cells[0], "test_cell_1")

    @patch('linux_edr.application.services.report_service.ReportService._create_block')
    def test_add_cell_triggers_block_creation(self, mock_create_block):
        """Test that adding the 16th cell triggers block creation."""
        # Add 15 cells
        for i in range(1, 16):
            cell = self.create_test_cell(i)
            self.service.add_cell(cell)
        
        # Mock has not been called yet
        mock_create_block.assert_not_called()
        
        # Add the 16th cell
        cell = self.create_test_cell(16)
        self.service.add_cell(cell)
        
        # Verify _create_block was called
        mock_create_block.assert_called_once()

    def test_create_block(self):
        """Test creating a block from cells."""
        # Create and add 16 cells
        for i in range(1, 17):
            cell = self.create_test_cell(i)
            self.cell_repo.save(cell)
            self.service.recent_cells.append(cell.report_id)
        
        # Mock the _create_daily_report method to avoid it being called
        with patch.object(self.service, '_create_daily_report'):
            # Create the block
            self.service._create_block()
            
            # Verify a block was created and saved
            self.assertEqual(len(self.service.recent_blocks), 1)
            
            # Load the block
            block_id = self.service.recent_blocks[0]
            block_data = self.block_repo.load(block_id)
            
            # Verify block content
            self.assertIsNotNone(block_data)
            self.assertEqual(len(block_data["cells"]), 16)
            self.assertIn("command_counts", block_data)
            
            # Verify that reporter.analyze_report was called
            self.mock_reporter.analyze_report.assert_called()

    def test_create_daily_report(self):
        """Test creating a daily report from blocks."""
        # Create and add 6 blocks
        for i in range(1, 7):
            block = self.create_test_block(i)
            self.block_repo.save(block)
            self.service.recent_blocks.append(block.report_id)
        
        # Mock the _create_weekly_report method to avoid it being called
        with patch.object(self.service, '_create_weekly_report'):
            # Create the daily report
            self.service._create_daily_report()
            
            # Verify a daily report was created and saved
            self.assertEqual(len(self.service.recent_daily_reports), 1)
            
            # Load the daily report
            daily_id = self.service.recent_daily_reports[0]
            daily_data = self.daily_repo.load(daily_id)
            
            # Verify daily report content
            self.assertIsNotNone(daily_data)
            self.assertEqual(len(daily_data["blocks"]), 6)
            self.assertIn("command_counts", daily_data)
            
            # Verify that reporter.analyze_report was called
            self.mock_reporter.analyze_report.assert_called()

    @patch('linux_edr.application.services.severity_calculator.SeverityCalculator.calculate_from_lower_reports')
    def test_daily_report_uses_severity_calculator(self, mock_calculate_severity):
        """Test that daily report creation uses the SeverityCalculator."""
        # Set up mock return value
        mock_calculate_severity.return_value = 3
        
        # Create and add 6 blocks
        for i in range(1, 7):
            block = self.create_test_block(i)
            self.block_repo.save(block)
            self.service.recent_blocks.append(block.report_id)
        
        # Mock the _create_weekly_report method to avoid it being called
        with patch.object(self.service, '_create_weekly_report'):
            # Create the daily report
            self.service._create_daily_report()
            
            # Verify SeverityCalculator was called
            mock_calculate_severity.assert_called_once()
            
            # Load the daily report and verify severity was set
            daily_id = self.service.recent_daily_reports[0]
            daily_data = self.daily_repo.load(daily_id)
            self.assertEqual(daily_data["severity"], 3)

    def test_create_weekly_report(self):
        """Test creating a weekly report from daily reports."""
        # Create and add 7 daily reports (one for each day of the week)
        base_date = datetime(2023, 1, 1)
        for i in range(7):
            date = (base_date + timedelta(days=i)).strftime("%Y-%m-%d")
            daily = self.create_test_daily_report(i+1, date)
            self.daily_repo.save(daily)
            self.service.recent_daily_reports.append(daily.report_id)
        
        # Mock the _create_monthly_report method to avoid it being called
        with patch.object(self.service, '_create_monthly_report'):
            # Create the weekly report
            self.service._create_weekly_report()
            
            # Verify a weekly report was created and saved
            self.assertEqual(len(self.service.recent_weekly_reports), 1)
            
            # Load the weekly report
            weekly_id = self.service.recent_weekly_reports[0]
            weekly_data = self.weekly_repo.load(weekly_id)
            
            # Verify weekly report content
            self.assertIsNotNone(weekly_data)
            self.assertEqual(len(weekly_data["daily_reports"]), 7)
            self.assertIn("command_trends", weekly_data)
            self.assertIn("process_trends", weekly_data)
            
            # Verify that reporter.analyze_report was called
            self.mock_reporter.analyze_report.assert_called()

    @patch('linux_edr.application.services.severity_calculator.SeverityCalculator.calculate_risk_score')
    def test_weekly_report_uses_risk_score_calculator(self, mock_risk_score):
        """Test that weekly report creation uses the risk score calculator."""
        # Set up mock return value
        mock_risk_score.return_value = 60
        
        # Create and add 7 daily reports
        base_date = datetime(2023, 1, 1)
        for i in range(7):
            date = (base_date + timedelta(days=i)).strftime("%Y-%m-%d")
            daily = self.create_test_daily_report(i+1, date)
            self.daily_repo.save(daily)
            self.service.recent_daily_reports.append(daily.report_id)
        
        # Mock the _create_monthly_report method to avoid it being called
        with patch.object(self.service, '_create_monthly_report'):
            # Create the weekly report
            self.service._create_weekly_report()
            
            # Verify risk_score calculator was called
            mock_risk_score.assert_called_once()
            
            # Load the weekly report and verify risk_score was set
            weekly_id = self.service.recent_weekly_reports[0]
            weekly_data = self.weekly_repo.load(weekly_id)
            self.assertEqual(weekly_data["risk_score"], 60)

    def test_create_monthly_report(self):
        """Test creating a monthly report from weekly reports."""
        # Create and add 4 weekly reports
        base_date = datetime(2023, 1, 1)
        for i in range(4):
            date = (base_date + timedelta(weeks=i)).strftime("%Y-%m-%d")
            weekly = self.create_test_weekly_report(i+1, date)
            self.weekly_repo.save(weekly)
            self.service.recent_weekly_reports.append(weekly.report_id)
        
        # Create the monthly report
        self.service._create_monthly_report()
        
        # Verify a monthly report was created
        monthly_files = os.listdir(os.path.join(self.test_dir, "monthly"))
        self.assertEqual(len(monthly_files), 1)
        
        # Load the monthly report
        with open(os.path.join(self.test_dir, "monthly", monthly_files[0]), "r") as f:
            monthly_data = json.load(f)
        
        # Verify monthly report content
        self.assertEqual(len(monthly_data["weekly_reports"]), 4)
        self.assertIn("command_summary", monthly_data)
        self.assertIn("process_summary", monthly_data)
        self.assertIn("security_summary", monthly_data)
        self.assertIn("recommendations", monthly_data)
        
        # Verify that reporter.analyze_report was called
        self.mock_reporter.analyze_report.assert_called()

    def test_monthly_report_extract_recommendations(self):
        """Test that monthly report extracts recommendations from analysis."""
        # Create and add 4 weekly reports
        base_date = datetime(2023, 1, 1)
        for i in range(4):
            date = (base_date + timedelta(weeks=i)).strftime("%Y-%m-%d")
            weekly = self.create_test_weekly_report(i+1, date)
            self.weekly_repo.save(weekly)
            self.service.recent_weekly_reports.append(weekly.report_id)
        
        # Mock the analysis return value with recommendations
        analysis_with_recommendations = """
        Monthly Security Analysis
        
        Overall, the system security posture is concerning.
        
        Recommendations:
        - Update all system packages
        - Implement stronger password policies
        - Enable 2FA for all accounts
        
        Other recommendations include regular backups.
        """
        
        # Configure mock to add the analysis to the monthly report
        def analyze_side_effect(report):
            report.analysis = analysis_with_recommendations
            report.severity = 4
        
        self.mock_reporter.analyze_report.side_effect = analyze_side_effect
        
        # Create the monthly report
        self.service._create_monthly_report()
        
        # Load the monthly report
        monthly_files = os.listdir(os.path.join(self.test_dir, "monthly"))
        with open(os.path.join(self.test_dir, "monthly", monthly_files[0]), "r") as f:
            monthly_data = json.load(f)
        
        # Verify recommendations were extracted
        self.assertIn("recommendations", monthly_data)
        self.assertGreaterEqual(len(monthly_data["recommendations"]), 3)
        self.assertIn("Update all system packages", monthly_data["recommendations"])
        self.assertIn("Implement stronger password policies", monthly_data["recommendations"])
        self.assertIn("Enable 2FA for all accounts", monthly_data["recommendations"])

    def test_get_report(self):
        """Test getting reports of different types."""
        # Create and save reports of each type
        cell = self.create_test_cell()
        block = self.create_test_block()
        daily = self.create_test_daily_report()
        weekly = self.create_test_weekly_report()
        
        self.cell_repo.save(cell)
        self.block_repo.save(block)
        self.daily_repo.save(daily)
        self.weekly_repo.save(weekly)
        
        # Test getting each type of report
        cell_data = self.service.get_report(cell.report_id, "cells")
        block_data = self.service.get_report(block.report_id, "blocks")
        daily_data = self.service.get_report(daily.report_id, "daily")
        weekly_data = self.service.get_report(weekly.report_id, "weekly")
        
        # Verify the reports were retrieved correctly
        self.assertEqual(cell_data["report_id"], cell.report_id)
        self.assertEqual(block_data["report_id"], block.report_id)
        self.assertEqual(daily_data["report_id"], daily.report_id)
        self.assertEqual(weekly_data["report_id"], weekly.report_id)
        
        # Test with invalid report type
        invalid_data = self.service.get_report("test", "invalid_type")
        self.assertIsNone(invalid_data)

    def test_unusual_activity_detection(self):
        """Test detection of unusual activity in block reports."""
        # Create blocks with varying severity levels
        for i in range(6):
            block = self.create_test_block(i+1)
            # Set severity to match index (blocks 4-6 will have high severity)
            block.severity = i+1 if i+1 <= 5 else 5
            if i >= 3:  # Blocks 4-6 have high severity
                block.analysis = f"Suspicious activity detected in block {i+1}"
            self.block_repo.save(block)
            self.service.recent_blocks.append(block.report_id)
        
        # Create the daily report
        with patch.object(self.service, '_create_weekly_report'):
            self.service._create_daily_report()
        
        # Load the daily report
        daily_id = self.service.recent_daily_reports[0]
        daily_data = self.daily_repo.load(daily_id)
        
        # Verify unusual activity was detected
        self.assertIn("unusual_activity", daily_data)
        self.assertGreaterEqual(len(daily_data["unusual_activity"]), 3)  # Blocks 4-6 should be flagged


if __name__ == "__main__":
    unittest.main() 