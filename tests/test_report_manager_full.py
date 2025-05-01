import unittest
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
import json
import time

from linux_edr.report_manager import ReportManager
from linux_edr.domain.models.reports import Cell, Block, DailyReport, WeeklyReport, MonthlyReport
from linux_edr.application.services.report_service import ReportService
from linux_edr.application.services.severity_calculator import SeverityCalculator
from linux_edr.infrastructure.repositories.report_repository import FileSystemReportRepository


class TestReportManagerFull(unittest.TestCase):
    """Comprehensive tests for the ReportManager class with clean architecture."""

    def setUp(self):
        # Create a temporary directory for test reports
        self.test_dir = tempfile.mkdtemp()

        # Create the ReportManager
        self.manager = ReportManager(self.test_dir)

    def tearDown(self):
        # Clean up the temporary directory
        shutil.rmtree(self.test_dir)

    def _create_test_cell_file(self, index, timestamp=None, with_process_events=True):
        """Helper to create a cell file for testing."""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        start_time = timestamp.replace(minute=0, second=0, microsecond=0)
        end_time = start_time.replace(minute=15)

        cell_data = {
            "report_id": f"cell_{index}",
            "window_start": start_time.isoformat(),
            "window_end": end_time.isoformat(),
            "total": 5 * index,
            "command_counts": {"ls": 3 * index, "cat": 2 * index},
        }

        if with_process_events:
            cell_data["process_events"] = {
                "bash": [f"command_{j}" for j in range(3)],
                "python": [f"script_{j}.py" for j in range(2)],
            }

        # Save cell data to file
        filename = os.path.join(self.test_dir, "cells", f"cell_{index}.json")
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w") as f:
            json.dump(cell_data, f)

        return cell_data

    def _create_test_block_file(self, index, timestamp=None):
        """Helper to create a block file for testing."""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        start_time = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(hours=4)

        cell_ids = [f"cell_{index}_{i}" for i in range(16)]

        block_data = {
            "report_id": f"block_{index}",
            "window_start": start_time.isoformat(),
            "window_end": end_time.isoformat(),
            "total_events": 100 * index,
            "cells": cell_ids,
            "command_counts": {"ls": 50 * index, "cat": 30 * index, "grep": 20 * index},
            "top_processes": {"bash": 60 * index, "python": 40 * index},
        }

        # Create the blocks directory if it doesn't exist
        os.makedirs(os.path.join(self.test_dir, "blocks"), exist_ok=True)

        # Save block data to file
        filename = os.path.join(self.test_dir, "blocks", f"block_{index}.json")
        with open(filename, "w") as f:
            json.dump(block_data, f)

        return block_data, cell_ids

    def _create_test_daily_file(self, index, date=None):
        """Helper to create a daily report file for testing."""
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        dt = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        start_time = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = dt.replace(hour=23, minute=59, second=59, microsecond=999999)

        block_ids = [f"block_{index}_{i}" for i in range(6)]

        daily_data = {
            "report_id": f"daily_{date.replace('-', '')}",
            "date": date,
            "window_start": start_time.isoformat(),
            "window_end": end_time.isoformat(),
            "total_events": 1000 * index,
            "blocks": block_ids,
            "command_counts": {"ls": 500 * index, "cat": 300 * index, "grep": 200 * index},
            "top_processes": {"bash": 600 * index, "python": 400 * index},
            "unusual_activity": [],
        }

        # Create the daily directory if it doesn't exist
        os.makedirs(os.path.join(self.test_dir, "daily"), exist_ok=True)

        # Save daily data to file
        filename = os.path.join(self.test_dir, "daily", f"daily_{date.replace('-', '')}.json")
        with open(filename, "w") as f:
            json.dump(daily_data, f)

        return daily_data, block_ids

    def _create_test_weekly_file(self, index, start_date=None):
        """Helper to create a weekly report file for testing."""
        if start_date is None:
            now = datetime.now(timezone.utc)
            start_date = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")

        start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end_dt = start_dt + timedelta(days=6)
        end_date = end_dt.strftime("%Y-%m-%d")

        daily_ids = [f"daily_{(start_dt + timedelta(days=i)).strftime('%Y%m%d')}" for i in range(7)]

        command_trends = {
            "ls": [50, 60, 40, 70, 80, 30, 55],
            "cat": [30, 35, 25, 40, 45, 20, 30],
            "grep": [20, 25, 15, 30, 35, 10, 20],
        }

        process_trends = {
            "bash": [60, 70, 50, 80, 90, 40, 65],
            "python": [40, 45, 30, 50, 55, 25, 35],
        }

        weekly_data = {
            "report_id": f"weekly_{start_date.replace('-', '')}_{end_date.replace('-', '')}",
            "week_start_date": start_date,
            "week_end_date": end_date,
            "total_events": 7000 * index,
            "daily_reports": daily_ids,
            "command_trends": command_trends,
            "process_trends": process_trends,
            "security_incidents": [],
            "risk_score": min(70 * index, 100),
        }

        # Create the weekly directory if it doesn't exist
        os.makedirs(os.path.join(self.test_dir, "weekly"), exist_ok=True)

        # Save weekly data to file
        filename = os.path.join(
            self.test_dir,
            "weekly",
            f"weekly_{start_date.replace('-', '')}_{end_date.replace('-', '')}.json",
        )
        with open(filename, "w") as f:
            json.dump(weekly_data, f)

        return weekly_data, daily_ids

    def test_create_cell_with_real_service(self):
        """Test creating a cell report with the real ReportService."""
        # Create a cell
        now = datetime.now(timezone.utc)
        cell = Cell(
            report_id="test_cell",
            window_start=now.isoformat(),
            window_end=(now + timedelta(minutes=15)).isoformat(),
            total=10,
            command_counts={"ls": 6, "cat": 4},
            process_events={"bash": ["ls -la", "cat test.txt"]},
        )

        # Call create_cell
        self.manager.create_cell(cell)

        # Verify cell file was created
        cell_path = os.path.join(self.test_dir, "cells", "test_cell.json")
        self.assertTrue(os.path.exists(cell_path))

        # Load the cell and check its content
        with open(cell_path, "r") as f:
            saved_cell = json.load(f)

        self.assertEqual(saved_cell["report_id"], "test_cell")
        self.assertEqual(saved_cell["total"], 10)

        # Verify cell ID was added to recent_cells
        self.assertEqual(len(self.manager.recent_cells), 1)
        self.assertEqual(self.manager.recent_cells[0], "test_cell")

    def test_repository_integration(self):
        """Test that repositories can correctly save and load reports."""
        # Create some test data
        test_cell = Cell(
            report_id="test_cell_repo",
            window_start="2023-01-01T00:00:00+00:00",
            window_end="2023-01-01T00:15:00+00:00",
            total=5,
            command_counts={"ls": 3, "cat": 2},
        )

        # Save cell using the repository
        cell_repo = self.manager.cell_repository
        result = cell_repo.save(test_cell)
        self.assertTrue(result)

        # Load cell back
        loaded_cell = cell_repo.load("test_cell_repo")
        self.assertIsNotNone(loaded_cell)
        self.assertEqual(loaded_cell["report_id"], "test_cell_repo")

        # Get recent cells
        recent = cell_repo.get_recent(5)
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0], "test_cell_repo")

    def test_severity_calculator(self):
        """Test SeverityCalculator calculations."""
        # Test cases for calculate_from_lower_reports
        test_cases = [
            # All same severity
            ([{"severity": 3}, {"severity": 3}, {"severity": 3}], 3),
            # Mixed severities - median is 3, max is 5: (0.7*3 + 0.3*5) = 3.6 -> 4
            ([{"severity": 1}, {"severity": 3}, {"severity": 5}], 4),
            # Bias toward higher severity (70% median + 30% max)
            ([{"severity": 1}, {"severity": 1}, {"severity": 5}], 2),  # (0.7*1 + 0.3*5) = 2.2 -> 2
            # Empty list
            ([], None),
            # No severity fields
            ([{}, {}, {}], None),
            # Some missing severity fields
            ([{"severity": 2}, {}, {"severity": 4}], 3),  # (0.7*2 + 0.3*4) = 2.6 -> 3
        ]

        for report_list, expected in test_cases:
            result = SeverityCalculator.calculate_from_lower_reports(report_list)
            self.assertEqual(result, expected, f"Failed on {report_list} with result {result}")

        # Test calculate_risk_score
        self.assertEqual(SeverityCalculator.calculate_risk_score(1), 20)
        self.assertEqual(SeverityCalculator.calculate_risk_score(3), 60)
        self.assertEqual(SeverityCalculator.calculate_risk_score(5), 100)
        self.assertEqual(SeverityCalculator.calculate_risk_score(None), 40)  # Default

    @patch("linux_edr.application.services.report_service.ReportService._create_block")
    def test_service_integration(self, mock_create_block):
        """Test integration between ReportManager and ReportService."""
        # Add cells to trigger block creation
        for i in range(16):
            cell = Cell(
                report_id=f"test_cell_{i}",
                window_start="2023-01-01T00:00:00+00:00",
                window_end="2023-01-01T00:15:00+00:00",
                total=5,
                command_counts={"ls": 3, "cat": 2},
            )
            self.manager.create_cell(cell)

        # Verify cells were added to recent_cells
        self.assertEqual(len(self.manager.recent_cells), 16)

        # Verify _create_block was called
        mock_create_block.assert_called_once()

    def test_get_recent_reports_from_repositories(self):
        """Test that repositories can retrieve recent reports correctly."""
        # Create files with different timestamps
        for i in range(5):
            # Add a small delay to ensure different timestamps
            time.sleep(0.01)
            self._create_test_cell_file(i)

        # Create a fresh manager to load the reports
        manager = ReportManager(self.test_dir)

        # Get recent cells
        recent_cells = manager.recent_cells

        # Verify correct reports returned in order
        self.assertEqual(len(recent_cells), 5)

        # The most recent should be cell_4
        self.assertEqual(recent_cells[0], "cell_4")

    def test_get_report_delegated_to_service(self):
        """Test that get_report correctly delegates to the service."""
        # Create a test cell
        cell_data = self._create_test_cell_file(0)

        # Call get_report
        result = self.manager.get_report("cell_0", "cells")

        # Verify the returned report
        self.assertIsNotNone(result)
        self.assertEqual(result["report_id"], "cell_0")
        self.assertEqual(result["total"], cell_data["total"])

    def test_repository_not_found(self):
        """Test repository handling of nonexistent reports."""
        # Try to load a nonexistent report
        result = self.manager.get_report("nonexistent", "cells")

        # Should return None
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
