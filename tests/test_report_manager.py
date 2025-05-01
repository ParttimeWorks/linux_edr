import unittest
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime, timezone
import json

from linux_edr.report_manager import ReportManager
from linux_edr.domain.models.reports import Cell, Block, DailyReport
from linux_edr.application.services.report_service import ReportService


class TestReportManager(unittest.TestCase):
    """Tests for the ReportManager class that handles hierarchical reporting."""

    def setUp(self):
        # Create a temporary directory for test reports
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        # Clean up the temporary directory
        shutil.rmtree(self.test_dir)

    def test_init(self):
        """Test initialization of ReportManager."""
        manager = ReportManager(self.test_dir)

        # Verify directories were created
        for subdir in ["cells", "blocks", "daily", "weekly", "monthly"]:
            dir_path = os.path.join(self.test_dir, subdir)
            self.assertTrue(os.path.exists(dir_path), f"Directory {dir_path} was not created")

        # Verify repositories are initialized
        self.assertIsNotNone(manager.cell_repository)
        self.assertIsNotNone(manager.block_repository)
        self.assertIsNotNone(manager.daily_repository)
        self.assertIsNotNone(manager.weekly_repository)
        self.assertIsNotNone(manager.monthly_repository)

        # Verify service is initialized
        self.assertIsNotNone(manager.service)

        # Verify empty recent report lists (via properties)
        self.assertEqual(manager.recent_cells, [])
        self.assertEqual(manager.recent_blocks, [])
        self.assertEqual(manager.recent_daily_reports, [])
        self.assertEqual(manager.recent_weekly_reports, [])

    def test_init_with_reporter(self):
        """Test initialization with a reporter instance."""
        mock_reporter = MagicMock()
        manager = ReportManager(self.test_dir, reporter=mock_reporter)

        # Verify reporter was passed to the service
        self.assertEqual(manager.service.reporter, mock_reporter)

    @patch("linux_edr.application.services.report_service.ReportService.add_cell")
    def test_create_cell(self, mock_add_cell):
        """Test create_cell method delegates to the service."""
        manager = ReportManager(self.test_dir)

        # Create a cell
        cell = Cell(
            report_id="test_cell_1",
            window_start="2023-01-01T00:00:00+00:00",
            window_end="2023-01-01T00:15:00+00:00",
            total=5,
            command_counts={"ls": 3, "cat": 2},
        )

        # Call create_cell
        manager.create_cell(cell)

        # Verify service.add_cell was called
        mock_add_cell.assert_called_once_with(cell)

    @patch("linux_edr.application.services.report_service.ReportService.get_report")
    def test_get_report(self, mock_get_report):
        """Test get_report method delegates to the service."""
        manager = ReportManager(self.test_dir)

        # Mock return value
        mock_report = {"report_id": "test_cell_1", "total": 5}
        mock_get_report.return_value = mock_report

        # Call get_report
        result = manager.get_report("test_cell_1", "cells")

        # Verify service.get_report was called
        mock_get_report.assert_called_once_with("test_cell_1", "cells")

        # Verify result
        self.assertEqual(result, mock_report)

    def test_recent_properties(self):
        """Test that recent_* properties delegate to the service."""
        # Create a manager with a mock service
        manager = ReportManager(self.test_dir)
        mock_service = MagicMock()
        manager.service = mock_service

        # Set mock return values
        mock_service.recent_cells = ["cell1", "cell2"]
        mock_service.recent_blocks = ["block1"]
        mock_service.recent_daily_reports = ["daily1", "daily2", "daily3"]
        mock_service.recent_weekly_reports = ["weekly1"]

        # Test properties
        self.assertEqual(manager.recent_cells, ["cell1", "cell2"])
        self.assertEqual(manager.recent_blocks, ["block1"])
        self.assertEqual(manager.recent_daily_reports, ["daily1", "daily2", "daily3"])
        self.assertEqual(manager.recent_weekly_reports, ["weekly1"])


if __name__ == "__main__":
    unittest.main()
