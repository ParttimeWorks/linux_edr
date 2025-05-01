import unittest
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import json

from linux_edr.report_manager import ReportManager
from linux_edr.domain.models.reports import Cell, Block
from linux_edr.application.services.report_service import ReportService


class TestReportManagerBlocks(unittest.TestCase):
    """Additional tests for the block creation in ReportManager."""

    def setUp(self):
        # Create a temporary directory for test reports
        self.test_dir = tempfile.mkdtemp()
            
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
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w") as f:
            json.dump(cell_data, f)
            
        return cell_data
    
    @patch('linux_edr.application.services.report_service.ReportService._create_daily_report')
    def test_block_creation_via_service(self, mock_create_daily):
        """Test block creation through the service."""
        # Create a cell that should trigger block creation
        cell = Cell(
            report_id="cell_16",
            window_start="2023-01-01T00:00:00+00:00",
            window_end="2023-01-01T00:15:00+00:00",
            total=5,
            command_counts={"ls": 3, "cat": 2}
        )
        
        # Patch the service's _create_block method
        with patch.object(self.manager.service, '_create_block') as mock_create_block:
            # Set up enough cells to trigger block creation
            self.manager.service.recent_cells = [f"cell_{i}" for i in range(16)]
            
            # Call add_cell on the actual service with our patched method
            self.manager.service.add_cell(cell)
            
            # Verify _create_block was called
            mock_create_block.assert_called_once()
    
    def test_block_creation_with_enough_cells(self):
        """Test block creation with the real service when enough cells are available."""
        # Create 16 cells and add them to the repository
        cell_ids = []
        for i in range(16):
            # Create cell file
            cell_data = self._create_test_cell_file(i)
            cell_ids.append(f"cell_{i}")
        
        # Set the service's recent_cells directly
        self.manager.service.recent_cells = cell_ids.copy()
        
        # Mock _create_daily_report to prevent it from running
        with patch.object(self.manager.service, '_create_daily_report'):
            # Call _create_block
            self.manager.service._create_block()
            
            # Verify a block file was created
            block_files = os.listdir(os.path.join(self.test_dir, "blocks"))
            self.assertEqual(len(block_files), 1)
            
            # Load the block file and check its content
            with open(os.path.join(self.test_dir, "blocks", block_files[0]), "r") as f:
                block_data = json.load(f)
                
            # Verify block data
            self.assertEqual(len(block_data["cells"]), 16)
            self.assertIn("ls", block_data["command_counts"])
            self.assertIn("cat", block_data["command_counts"])
    
    def test_create_block_not_enough_cells(self):
        """Test block creation service when there aren't enough cells."""
        # Prepare just 10 cells (fewer than the 16 required)
        cell_ids = []
        for i in range(10):
            cell_data = self._create_test_cell_file(i)
            cell_ids.append(f"cell_{i}")
            
        # Set the service's recent_cells directly
        self.manager.service.recent_cells = cell_ids.copy()
        
        # Call _create_block
        self.manager.service._create_block()
        
        # Verify no block file was created
        block_files = os.listdir(os.path.join(self.test_dir, "blocks"))
        self.assertEqual(len(block_files), 0)
        
        # Verify recent_blocks is still empty
        self.assertEqual(len(self.manager.service.recent_blocks), 0)
    
    @patch('linux_edr.application.services.report_service.ReportService._create_daily_report')
    def test_block_triggers_daily_report(self, mock_create_daily):
        """Test that creating enough blocks triggers daily report creation."""
        # Add 6 blocks to recent_blocks (the threshold for creating a daily report)
        self.manager.service.recent_blocks = [f"block_{i}" for i in range(6)]
        
        # Add 16 cells to recent_cells to trigger block creation
        cell_ids = []
        for i in range(16):
            cell_data = self._create_test_cell_file(i)
            cell_ids.append(f"cell_{i}")
            
        self.manager.service.recent_cells = cell_ids.copy()
        
        # Call _create_block
        self.manager.service._create_block()
        
        # Verify _create_daily_report was called
        mock_create_daily.assert_called_once()


if __name__ == "__main__":
    unittest.main() 