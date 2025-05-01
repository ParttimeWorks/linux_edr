import unittest
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
import json

from linux_edr.report_manager import ReportManager
from linux_edr.models import Cell, Block, DailyReport, WeeklyReport, MonthlyReport


class TestReportManagerFull(unittest.TestCase):
    """Comprehensive tests for the ReportManager class."""

    def setUp(self):
        # Create a temporary directory for test reports
        self.test_dir = tempfile.mkdtemp()
        
        # Create report directories
        for subdir in ["cells", "blocks", "daily", "weekly", "monthly"]:
            os.makedirs(os.path.join(self.test_dir, subdir), exist_ok=True)
            
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
            "command_counts": {"ls": 3 * index, "cat": 2 * index}
        }
        
        if with_process_events:
            cell_data["process_events"] = {
                "bash": [f"command_{j}" for j in range(3)],
                "python": [f"script_{j}.py" for j in range(2)]
            }
        
        # Save cell data to file
        filename = os.path.join(self.test_dir, "cells", f"cell_{index}.json")
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
            "top_processes": {"bash": 60 * index, "python": 40 * index}
        }
        
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
            "unusual_activity": []
        }
        
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
            "grep": [20, 25, 15, 30, 35, 10, 20]
        }
        
        process_trends = {
            "bash": [60, 70, 50, 80, 90, 40, 65],
            "python": [40, 45, 30, 50, 55, 25, 35]
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
            "risk_score": min(70 * index, 100)
        }
        
        # Save weekly data to file
        filename = os.path.join(
            self.test_dir, 
            "weekly", 
            f"weekly_{start_date.replace('-', '')}_{end_date.replace('-', '')}.json"
        )
        with open(filename, "w") as f:
            json.dump(weekly_data, f)
            
        return weekly_data, daily_ids
    
    def test_create_cell(self):
        """Test creating a cell report."""
        # Create a cell
        now = datetime.now(timezone.utc)
        cell = Cell(
            report_id="test_cell",
            window_start=now.isoformat(),
            window_end=(now + timedelta(minutes=15)).isoformat(),
            total=10,
            command_counts={"ls": 6, "cat": 4},
            process_events={"bash": ["ls -la", "cat test.txt"]}
        )
        
        # Mock _create_block to prevent it from running
        with patch.object(self.manager, '_create_block') as mock_create_block:
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
            
            # _create_block should not be called yet (need 16 cells)
            mock_create_block.assert_not_called()
    
    def test_create_cell_triggers_block_creation(self):
        """Test that adding enough cells triggers block creation."""
        # Add 15 cells to recent_cells, then add one more to trigger block creation
        cell_ids = []
        for i in range(15):
            cell_data = self._create_test_cell_file(i)
            cell_ids.append(f"cell_{i}")
            
        self.manager.recent_cells = cell_ids.copy()
        
        # Create the 16th cell
        cell = Cell(
            report_id="cell_16",
            window_start=datetime.now(timezone.utc).isoformat(),
            window_end=(datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat(),
            total=10,
            command_counts={"ls": 6, "cat": 4},
            process_events={"bash": ["ls -la", "cat test.txt"]}
        )
        
        # Mock _create_block to verify it's called
        with patch.object(self.manager, '_create_block') as mock_create_block:
            # Call create_cell
            self.manager.create_cell(cell)
            
            # Verify _create_block was called
            mock_create_block.assert_called_once()
    
    def test_create_daily_report(self):
        """Test _create_daily_report with enough blocks."""
        # Create 6 blocks in the blocks directory
        block_ids = []
        for i in range(6):
            timestamp = datetime.now(timezone.utc) + timedelta(hours=4 * i)
            block_data, _ = self._create_test_block_file(i, timestamp)
            block_ids.append(f"block_{i}")
            
        # Set recent_blocks
        self.manager.recent_blocks = block_ids.copy()
        
        # Mock _create_weekly_report to prevent it from running
        with patch.object(self.manager, '_create_weekly_report') as mock_create_weekly:
            # Call _create_daily_report
            self.manager._create_daily_report()
            
            # Verify a daily report file was created
            daily_files = os.listdir(os.path.join(self.test_dir, "daily"))
            self.assertEqual(len(daily_files), 1)
            
            # Load the daily report and check its content
            with open(os.path.join(self.test_dir, "daily", daily_files[0]), "r") as f:
                daily_data = json.load(f)
                
            # Verify daily report data
            self.assertEqual(len(daily_data["blocks"]), 6)
            self.assertIn("command_counts", daily_data)
            self.assertIn("top_processes", daily_data)
            
            # Verify report ID was added to recent_daily_reports
            self.assertEqual(len(self.manager.recent_daily_reports), 1)
            self.assertEqual(self.manager.recent_daily_reports[0], daily_data["report_id"])
            
            # _create_weekly_report should not be called yet (need 7 daily reports)
            mock_create_weekly.assert_not_called()
    
    def test_create_daily_report_not_enough_blocks(self):
        """Test _create_daily_report with insufficient blocks."""
        # Create just 3 blocks (fewer than the 6 required)
        block_ids = []
        for i in range(3):
            block_data, _ = self._create_test_block_file(i)
            block_ids.append(f"block_{i}")
            
        # Set recent_blocks
        self.manager.recent_blocks = block_ids.copy()
        
        # Call _create_daily_report
        self.manager._create_daily_report()
        
        # Verify no daily report was created
        daily_files = os.listdir(os.path.join(self.test_dir, "daily"))
        self.assertEqual(len(daily_files), 0)
        
        # Verify recent_daily_reports is still empty
        self.assertEqual(len(self.manager.recent_daily_reports), 0)
    
    def test_create_weekly_report(self):
        """Test _create_weekly_report with enough daily reports."""
        # Create 7 daily reports in the daily directory
        today = datetime.now(timezone.utc)
        daily_ids = []
        for i in range(7):
            date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            daily_data, _ = self._create_test_daily_file(i, date)
            daily_ids.append(daily_data["report_id"])
            
        # Set recent_daily_reports
        self.manager.recent_daily_reports = daily_ids.copy()
        
        # Mock _create_monthly_report to prevent it from running
        with patch.object(self.manager, '_create_monthly_report') as mock_create_monthly:
            # Call _create_weekly_report
            self.manager._create_weekly_report()
            
            # Verify a weekly report file was created
            weekly_files = os.listdir(os.path.join(self.test_dir, "weekly"))
            self.assertEqual(len(weekly_files), 1)
            
            # Load the weekly report and check its content
            with open(os.path.join(self.test_dir, "weekly", weekly_files[0]), "r") as f:
                weekly_data = json.load(f)
                
            # Verify weekly report data
            self.assertEqual(len(weekly_data["daily_reports"]), 7)
            self.assertIn("command_trends", weekly_data)
            self.assertIn("process_trends", weekly_data)
            
            # Verify report ID was added to recent_weekly_reports
            self.assertEqual(len(self.manager.recent_weekly_reports), 1)
            self.assertEqual(self.manager.recent_weekly_reports[0], weekly_data["report_id"])
            
            # _create_monthly_report should not be called yet (need 4 weekly reports)
            mock_create_monthly.assert_not_called()
    
    def test_create_weekly_report_not_enough_daily_reports(self):
        """Test _create_weekly_report with insufficient daily reports."""
        # Create just 4 daily reports (fewer than the 7 required)
        daily_ids = []
        for i in range(4):
            date = (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d")
            daily_data, _ = self._create_test_daily_file(i, date)
            daily_ids.append(daily_data["report_id"])
            
        # Set recent_daily_reports
        self.manager.recent_daily_reports = daily_ids.copy()
        
        # Call _create_weekly_report
        self.manager._create_weekly_report()
        
        # Verify no weekly report was created
        weekly_files = os.listdir(os.path.join(self.test_dir, "weekly"))
        self.assertEqual(len(weekly_files), 0)
        
        # Verify recent_weekly_reports is still empty
        self.assertEqual(len(self.manager.recent_weekly_reports), 0)
    
    def test_create_monthly_report(self):
        """Test _create_monthly_report with enough weekly reports."""
        # Create 4 weekly reports in the weekly directory
        today = datetime.now(timezone.utc)
        weekly_ids = []
        
        for i in range(4):
            # Each week starts on Sunday of the week (i weeks ago)
            start_date = today - timedelta(days=7*i + today.weekday())
            start_date_str = start_date.strftime("%Y-%m-%d")
            
            weekly_data, _ = self._create_test_weekly_file(i, start_date_str)
            weekly_ids.append(weekly_data["report_id"])
            
        # Set recent_weekly_reports
        self.manager.recent_weekly_reports = weekly_ids.copy()
        
        # Call _create_monthly_report
        self.manager._create_monthly_report()
        
        # Verify a monthly report file was created
        monthly_files = os.listdir(os.path.join(self.test_dir, "monthly"))
        self.assertEqual(len(monthly_files), 1)
        
        # Load the monthly report and check its content
        with open(os.path.join(self.test_dir, "monthly", monthly_files[0]), "r") as f:
            monthly_data = json.load(f)
            
        # Verify monthly report data
        self.assertEqual(len(monthly_data["weekly_reports"]), 4)
        self.assertIn("command_summary", monthly_data)
        self.assertIn("process_summary", monthly_data)
        self.assertIn("security_summary", monthly_data)
    
    def test_create_monthly_report_not_enough_weekly_reports(self):
        """Test _create_monthly_report with insufficient weekly reports."""
        # Create just 2 weekly reports (fewer than the 4 required)
        weekly_ids = []
        for i in range(2):
            start_date = (datetime.now(timezone.utc) - timedelta(days=7*i))
            start_date_str = start_date.strftime("%Y-%m-%d")
            
            weekly_data, _ = self._create_test_weekly_file(i, start_date_str)
            weekly_ids.append(weekly_data["report_id"])
            
        # Set recent_weekly_reports
        self.manager.recent_weekly_reports = weekly_ids.copy()
        
        # Call _create_monthly_report
        self.manager._create_monthly_report()
        
        # Verify no monthly report was created
        monthly_files = os.listdir(os.path.join(self.test_dir, "monthly"))
        self.assertEqual(len(monthly_files), 0)
    
    def test_get_recent_reports(self):
        """Test _get_recent_reports method."""
        # Create some test files with different timestamps
        for i in range(5):
            # Create with delays to ensure different timestamps
            time.sleep(0.01)
            self._create_test_cell_file(i)
        
        # Call _get_recent_reports
        recent_cells = self.manager._get_recent_reports("cells", 3)
        
        # Should return the 3 most recent cells
        self.assertEqual(len(recent_cells), 3)
        
        # Since we created them in order 0-4, the most recent should be 4, 3, 2
        expected_cells = [f"cell_{i}" for i in range(4, 1, -1)]
        self.assertEqual(recent_cells, expected_cells)
    
    def test_get_recent_reports_empty_dir(self):
        """Test _get_recent_reports on empty directory."""
        # Remove the cells directory
        shutil.rmtree(os.path.join(self.test_dir, "cells"))
        
        # Call _get_recent_reports on nonexistent directory
        recent_cells = self.manager._get_recent_reports("cells", 3)
        
        # Should return empty list
        self.assertEqual(recent_cells, [])
    
    def test_get_report(self):
        """Test get_report method."""
        # Create a test cell
        cell_data = self._create_test_cell_file(0)
        
        # Call get_report
        result = self.manager.get_report("cell_0", "cells")
        
        # Verify the returned report
        self.assertIsNotNone(result)
        self.assertEqual(result["report_id"], "cell_0")
        self.assertEqual(result["total"], cell_data["total"])
    
    def test_get_report_nonexistent(self):
        """Test get_report on nonexistent report."""
        # Call get_report on nonexistent ID
        result = self.manager.get_report("nonexistent", "cells")
        
        # Should return None
        self.assertIsNone(result)
    
    @patch('os.path.getmtime')
    def test_load_existing_reports(self, mock_getmtime):
        """Test _load_existing_reports method."""
        # Create test files for each report level
        # We need to mock getmtime to control the order
        
        # Set up mock for getmtime to return predictable timestamps
        def mock_getmtime_side_effect(path):
            # Extract filename from path
            filename = os.path.basename(path)
            # Extract number from filename (assuming format like 'cell_1.json')
            try:
                num = int(filename.split('_')[1].split('.')[0])
                # Return timestamp based on number (higher = more recent)
                return 1000 + num
            except:
                return 1000
        
        mock_getmtime.side_effect = mock_getmtime_side_effect
        
        # Create test files for each level
        cell_ids = []
        for i in range(20):
            self._create_test_cell_file(i)
            cell_ids.append(f"cell_{i}")
            
        block_ids = []
        for i in range(10):
            block_data, _ = self._create_test_block_file(i)
            block_ids.append(f"block_{i}")
            
        daily_ids = []
        for i in range(10):
            date = (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d")
            daily_data, _ = self._create_test_daily_file(i, date)
            daily_ids.append(daily_data["report_id"])
            
        weekly_ids = []
        for i in range(5):
            start_date = (datetime.now(timezone.utc) - timedelta(days=7*i))
            start_date_str = start_date.strftime("%Y-%m-%d")
            
            weekly_data, _ = self._create_test_weekly_file(i, start_date_str)
            weekly_ids.append(weekly_data["report_id"])
        
        # Create a fresh ReportManager to load the reports
        manager = ReportManager(self.test_dir)
        
        # Check that the reports were loaded correctly
        # Should have the most recent reports in each category
        expected_cells = [f"cell_{i}" for i in range(19, 3, -1)]  # Most recent 16
        expected_blocks = [f"block_{i}" for i in range(9, 3, -1)]  # Most recent 6
        
        self.assertEqual(len(manager.recent_cells), 16)
        self.assertEqual(len(manager.recent_blocks), 6)
        self.assertEqual(len(manager.recent_daily_reports), 7)
        self.assertEqual(len(manager.recent_weekly_reports), 4)
        
        # Check specific IDs (the most recent ones based on our mock)
        for i, cell_id in enumerate(expected_cells):
            self.assertIn(cell_id, manager.recent_cells)
            
        for i, block_id in enumerate(expected_blocks):
            self.assertIn(block_id, manager.recent_blocks)


import time

if __name__ == "__main__":
    unittest.main() 