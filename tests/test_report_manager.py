import unittest
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime, timezone
import json

from linux_edr.report_manager import ReportManager
from linux_edr.models import Cell, Block, DailyReport


class TestReportManager(unittest.TestCase):
    """Tests for the ReportManager class that handles hierarchical reporting."""

    def setUp(self):
        # Create a temporary directory for test reports
        self.test_dir = tempfile.mkdtemp()
        
        # Create report directories
        for subdir in ["cells", "blocks", "daily", "weekly", "monthly"]:
            os.makedirs(os.path.join(self.test_dir, subdir), exist_ok=True)

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
        
        # Verify empty recent report lists
        self.assertEqual(manager.recent_cells, [])
        self.assertEqual(manager.recent_blocks, [])
        self.assertEqual(manager.recent_daily_reports, [])
        self.assertEqual(manager.recent_weekly_reports, [])

    def test_save_and_load_report(self):
        """Test saving and loading a report."""
        manager = ReportManager(self.test_dir)
        
        # Create a cell report
        cell = Cell(
            report_id="test_cell_1",
            window_start="2023-01-01T00:00:00+00:00",
            window_end="2023-01-01T00:15:00+00:00",
            total=5,
            command_counts={"ls": 3, "cat": 2}
        )
        
        # Use _save_report to save the cell
        manager._save_report(cell, "cells")
        
        # Verify file was created
        cell_path = os.path.join(self.test_dir, "cells", "test_cell_1.json")
        self.assertTrue(os.path.exists(cell_path))
        
        # Use _load_report to load the cell
        loaded_data = manager._load_report("test_cell_1", "cells")
        
        # Verify data was loaded correctly
        self.assertIsNotNone(loaded_data)
        self.assertEqual(loaded_data["report_id"], "test_cell_1")
        self.assertEqual(loaded_data["total"], 5)
        self.assertEqual(loaded_data["command_counts"]["ls"], 3)

    def test_load_nonexistent_report(self):
        """Test loading a nonexistent report."""
        manager = ReportManager(self.test_dir)
        
        # Try to load a nonexistent report
        result = manager._load_report("nonexistent", "cells")
        
        # Should return None
        self.assertIsNone(result)

    def test_get_recent_reports(self):
        """Test getting recent reports."""
        manager = ReportManager(self.test_dir)
        
        # Create three cell reports with different timestamps
        for i in range(3):
            cell = Cell(
                report_id=f"test_cell_{i}",
                window_start="2023-01-01T00:00:00+00:00",
                window_end="2023-01-01T00:15:00+00:00",
                total=5,
                command_counts={"ls": 3, "cat": 2}
            )
            manager._save_report(cell, "cells")
            
            # Add a small delay to ensure different modification times
            if i < 2:  # No need to delay after the last one
                import time
                time.sleep(0.1)
        
        # Get the two most recent reports
        recent = manager._get_recent_reports("cells", 2)
        
        # Should have the two most recent reports (in reverse order)
        self.assertEqual(len(recent), 2)
        self.assertEqual(recent[0], "test_cell_2")  # Most recent first
        self.assertEqual(recent[1], "test_cell_1")

    def test_create_cell(self):
        """Test create_cell method."""
        manager = ReportManager(self.test_dir)
        
        # Create a cell
        cell = Cell(
            report_id="test_cell_1",
            window_start="2023-01-01T00:00:00+00:00",
            window_end="2023-01-01T00:15:00+00:00",
            total=5,
            command_counts={"ls": 3, "cat": 2}
        )
        
        # Call create_cell
        manager.create_cell(cell)
        
        # Verify cell was saved
        cell_path = os.path.join(self.test_dir, "cells", "test_cell_1.json")
        self.assertTrue(os.path.exists(cell_path))
        
        # Verify cell was added to recent_cells
        self.assertEqual(len(manager.recent_cells), 1)
        self.assertEqual(manager.recent_cells[0], "test_cell_1")

    def test_cell_limit(self):
        """Test that recent_cells is limited to the correct size."""
        manager = ReportManager(self.test_dir)
        
        # Add more cells than the limit (16)
        for i in range(20):
            cell = Cell(
                report_id=f"test_cell_{i}",
                window_start="2023-01-01T00:00:00+00:00",
                window_end="2023-01-01T00:15:00+00:00",
                total=5,
                command_counts={"ls": 3, "cat": 2}
            )
            manager.create_cell(cell)
        
        # Should have at most 16 cells (the limit for a block)
        self.assertLessEqual(len(manager.recent_cells), 16)
        
        # The most recent cells should be at the beginning
        self.assertEqual(manager.recent_cells[0], "test_cell_19")

    @patch('linux_edr.report_manager.ReportManager._create_block')
    def test_block_creation_trigger(self, mock_create_block):
        """Test that _create_block is called when there are enough cells."""
        manager = ReportManager(self.test_dir)
        
        # Add exactly 16 cells (the number needed for a block)
        for i in range(16):
            cell = Cell(
                report_id=f"test_cell_{i}",
                window_start="2023-01-01T00:00:00+00:00",
                window_end="2023-01-01T00:15:00+00:00",
                total=5,
                command_counts={"ls": 3, "cat": 2}
            )
            manager.create_cell(cell)
        
        # _create_block should have been called
        mock_create_block.assert_called_once()
        
    def test_get_report(self):
        """Test get_report method."""
        manager = ReportManager(self.test_dir)
        
        # Create a cell report
        cell = Cell(
            report_id="test_cell_1",
            window_start="2023-01-01T00:00:00+00:00",
            window_end="2023-01-01T00:15:00+00:00",
            total=5,
            command_counts={"ls": 3, "cat": 2}
        )
        
        # Save the cell
        manager._save_report(cell, "cells")
        
        # Use get_report to retrieve it
        report = manager.get_report("test_cell_1", "cells")
        
        # Verify report was loaded correctly
        self.assertIsNotNone(report)
        self.assertEqual(report["report_id"], "test_cell_1")
        self.assertEqual(report["total"], 5)


if __name__ == "__main__":
    unittest.main() 