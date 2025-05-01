import os
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union, TypeVar, Generic

from linux_edr.domain.models.reports import Cell, Block, DailyReport, WeeklyReport, MonthlyReport

logger = logging.getLogger(__name__)

# Define a type variable for report types
T = TypeVar("T", Cell, Block, DailyReport, WeeklyReport, MonthlyReport)


class ReportRepository(ABC, Generic[T]):
    """Abstract repository interface for report operations."""

    @abstractmethod
    def save(self, report: T) -> bool:
        """
        Save a report to the repository.

        Args:
            report: The report to save

        Returns:
            True if saved successfully, False otherwise
        """
        pass

    @abstractmethod
    def load(self, report_id: str) -> Optional[Dict[str, Any]]:
        """
        Load a report from the repository.

        Args:
            report_id: ID of the report to load

        Returns:
            Report data as a dictionary or None if not found
        """
        pass

    @abstractmethod
    def get_recent(self, limit: int) -> List[str]:
        """
        Get the most recent report IDs.

        Args:
            limit: Maximum number of reports to retrieve

        Returns:
            List of report IDs sorted by recency (newest first)
        """
        pass


class FileSystemReportRepository(ReportRepository[T]):
    """
    File system implementation of the report repository.
    Stores reports as JSON files in a directory structure.
    """

    def __init__(self, base_dir: str, report_type: str):
        """
        Initialize the report repository.

        Args:
            base_dir: Base directory for reports
            report_type: Type of report ('cells', 'blocks', etc.)
        """
        self.dir_path = os.path.join(base_dir, report_type)
        self.report_type = report_type
        os.makedirs(self.dir_path, exist_ok=True)

    def save(self, report: T) -> bool:
        """
        Save a report to a JSON file.

        Args:
            report: Report to save

        Returns:
            True if saved successfully, False otherwise
        """
        filepath = os.path.join(self.dir_path, f"{report.report_id}.json")

        try:
            with open(filepath, "w") as f:
                json.dump(report.model_dump(), f, indent=2)
            logger.debug(f"Saved {self.report_type} report {report.report_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to save {self.report_type} report: {e}")
            return False

    def load(self, report_id: str) -> Optional[Dict[str, Any]]:
        """
        Load a report from a JSON file.

        Args:
            report_id: ID of the report to load

        Returns:
            Report data as a dictionary or None if not found
        """
        filepath = os.path.join(self.dir_path, f"{report_id}.json")

        if not os.path.exists(filepath):
            logger.debug(f"Report {report_id} not found at {filepath}")
            return None

        try:
            with open(filepath, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load report {report_id}: {e}")
            return None

    def get_recent(self, limit: int) -> List[str]:
        """
        Get the most recent report IDs based on file modification time.

        Args:
            limit: Maximum number of reports to retrieve

        Returns:
            List of report IDs sorted by recency (newest first)
        """
        if not os.path.exists(self.dir_path):
            return []

        # Get all JSON files in directory
        files = [f for f in os.listdir(self.dir_path) if f.endswith(".json")]

        # Sort by modification time (newest first)
        files.sort(key=lambda f: os.path.getmtime(os.path.join(self.dir_path, f)), reverse=True)

        # Return report IDs (filename without extension)
        return [os.path.splitext(f)[0] for f in files[:limit]]
