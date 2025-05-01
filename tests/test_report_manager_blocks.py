import unittest
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import json

from linux_edr.report_manager import ReportManager
from linux_edr.models import Cell, Block


class TestReportManagerBlocks(unittest.TestCase):
    """Additional tests for the block creation in ReportManager."""

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
    
    def _create_test_cell_file(self, index, timestamp=None):
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
        
        # Save cell data to file
        filename = os.path.join(self.test_dir, "cells", f"cell_{index}.json")
        with open(filename, "w") as f:
            json.dump(cell_data, f)
            
        return cell_data
    
    def test_create_block_with_enough_cells(self):
        """Test _create_block when enough cells are available."""
        # Prepare 16 cells in the cells directory
        cell_ids = []
        for i in range(16):
            cell_data = self._create_test_cell_file(i)
            cell_ids.append(f"cell_{i}")
            
        # Fill the recent_cells list with these IDs
        self.manager.recent_cells = cell_ids.copy()
        
        # Mock _create_daily_report to prevent it from running
        with patch.object(self.manager, '_create_daily_report') as mock_create_daily:
            # Call _create_block
            self.manager._create_block()
            
            # Verify a block file was created in the blocks directory
            block_files = os.listdir(os.path.join(self.test_dir, "blocks"))
            self.assertEqual(len(block_files), 1)
            
            # Load the block file and check its content
            with open(os.path.join(self.test_dir, "blocks", block_files[0]), "r") as f:
                block_data = json.load(f)
                
            # Verify block data
            self.assertEqual(len(block_data["cells"]), 16)
            self.assertEqual(block_data["total_events"], sum(5 * i for i in range(16)))
            self.assertIn("ls", block_data["command_counts"])
            self.assertIn("cat", block_data["command_counts"])
            
            # Verify the block ID was added to recent_blocks
            self.assertEqual(len(self.manager.recent_blocks), 1)
            self.assertEqual(self.manager.recent_blocks[0], block_data["report_id"])
            
            # _create_daily_report should not be called yet (need 6 blocks)
            mock_create_daily.assert_not_called()
    
    # def test_create_block_time_window(self):
    #     """Test that the block's time window encompasses all its cells."""
    #     # Create cells with specific timestamps
    #     from datetime import timedelta
        
    #     base_time = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    #     cell_ids = []
        
    #     for i in range(16):
    #         # Each cell has a 15-min window, starting at successive time points
    #         cell_time = base_time + timedelta(minutes=15 * i)
    #         cell_data = self._create_test_cell_file(i, cell_time)
    #         cell_ids.append(f"cell_{i}")
        
    #     # Set recent_cells
    #     self.manager.recent_cells = cell_ids.copy()
        
    #     # Call _create_block
    #     self.manager._create_block()
        
    #     # Get the block file
    #     block_files = os.listdir(os.path.join(self.test_dir, "blocks"))
    #     with open(os.path.join(self.test_dir, "blocks", block_files[0]), "r") as f:
    #         block_data = json.load(f)
        
    #     # Calculate expected time window
    #     expected_start = base_time.isoformat()
    #     expected_end = (base_time + timedelta(minutes=15 * 15 + 15)).isoformat()
        
    #     # Verify time window
    #     self.assertEqual(block_data["window_start"], expected_start)
    #     self.assertEqual(block_data["window_end"], expected_end)
    
    def test_create_block_not_enough_cells(self):
        """Test _create_block when there aren't enough cells."""
        # Prepare just 10 cells (fewer than the 16 required)
        cell_ids = []
        for i in range(10):
            cell_data = self._create_test_cell_file(i)
            cell_ids.append(f"cell_{i}")
            
        # Fill the recent_cells list with these IDs
        self.manager.recent_cells = cell_ids.copy()
        
        # Call _create_block
        self.manager._create_block()
        
        # Verify no block file was created
        block_files = os.listdir(os.path.join(self.test_dir, "blocks"))
        self.assertEqual(len(block_files), 0)
        
        # Verify recent_blocks is still empty
        self.assertEqual(len(self.manager.recent_blocks), 0)
    
    # def test_create_block_with_invalid_cells(self):
    #     """Test _create_block when some cells are invalid/missing."""
    #     # Create some valid cell files and some nonexistent IDs
    #     valid_ids = []
    #     for i in range(10):
    #         cell_data = self._create_test_cell_file(i)
    #         valid_ids.append(f"cell_{i}")
            
    #     # Mix in some nonexistent IDs
    #     all_ids = valid_ids + ["nonexistent1", "nonexistent2", "nonexistent3", 
    #                           "nonexistent4", "nonexistent5", "nonexistent6"]
        
    #     # Set recent_cells to include all these IDs
    #     self.manager.recent_cells = all_ids
        
    #     # Call _create_block - should use only the valid cells
    #     self.manager._create_block()
        
    #     # Verify a block was created despite missing cells
    #     block_files = os.listdir(os.path.join(self.test_dir, "blocks"))
    #     self.assertEqual(len(block_files), 1)
        
    #     # Load the block and verify it has only the valid cells
    #     with open(os.path.join(self.test_dir, "blocks", block_files[0]), "r") as f:
    #         block_data = json.load(f)
            
    #     # Should have 10 cells (the valid ones)
    #     self.assertEqual(len(block_data["cells"]), 10)
    
    @patch('linux_edr.report_manager.ReportManager._create_daily_report')
    def test_create_block_triggers_daily_report(self, mock_create_daily):
        """Test that creating enough blocks triggers daily report creation."""
        # Add 6 blocks to recent_blocks (the threshold for creating a daily report)
        self.manager.recent_blocks = [f"block_{i}" for i in range(6)]
        
        # Now create a block using _create_block
        # First we need cells
        cell_ids = []
        for i in range(16):
            cell_data = self._create_test_cell_file(i)
            cell_ids.append(f"cell_{i}")
            
        self.manager.recent_cells = cell_ids.copy()
        
        # Call _create_block
        self.manager._create_block()
        
        # Verify _create_daily_report was called
        mock_create_daily.assert_called_once()


if __name__ == "__main__":
    unittest.main() 