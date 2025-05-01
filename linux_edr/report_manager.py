import os
import logging
from typing import List, Dict, Any, Optional, Union

from linux_edr.domain.models.reports import Cell, Block, DailyReport, WeeklyReport, MonthlyReport
from linux_edr.infrastructure.repositories.report_repository import FileSystemReportRepository
from linux_edr.application.services.report_service import ReportService

logger = logging.getLogger(__name__)


class ReportManager:
    """
    Manages the hierarchical reporting system for Linux EDR.

    This class acts as a facade over the clean architecture components:
    - Domain models for report data structures
    - Repositories for persistence
    - Services for business logic

    Report Hierarchy:
    - Level 1: Cell (15 minutes)
    - Level 2: Block (16 Cells = 4 hours)
    - Level 3: DailyReport (6 Blocks = 24 hours)
    - Level 4: WeeklyReport (7 DailyReports)
    - Level 5: MonthlyReport (~4 WeeklyReports)
    """

    def __init__(self, reports_dir: str, reporter=None):
        """
        Initialize the report manager.

        Args:
            reports_dir: Directory to store reports
            reporter: Reporter instance for LLM analysis
        """
        self.reports_dir = reports_dir

        # Create reports directory if it doesn't exist
        os.makedirs(reports_dir, exist_ok=True)

        # Initialize repositories
        self.cell_repository = FileSystemReportRepository(reports_dir, "cells")
        self.block_repository = FileSystemReportRepository(reports_dir, "blocks")
        self.daily_repository = FileSystemReportRepository(reports_dir, "daily")
        self.weekly_repository = FileSystemReportRepository(reports_dir, "weekly")
        self.monthly_repository = FileSystemReportRepository(reports_dir, "monthly")

        # Initialize the service
        self.service = ReportService(
            cell_repository=self.cell_repository,
            block_repository=self.block_repository,
            daily_repository=self.daily_repository,
            weekly_repository=self.weekly_repository,
            monthly_repository=self.monthly_repository,
            reporter=reporter,
        )

        logger.info(f"Report manager initialized at {reports_dir}")

    def create_cell(self, cell: Cell) -> None:
        """
        Save a new Cell report and update the hierarchy.

        Args:
            cell: The Cell report to save
        """
        self.service.add_cell(cell)

    def get_report(self, report_id: str, report_type: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a report by ID and type.

        Args:
            report_id: ID of the report to retrieve
            report_type: Type of report ('cells', 'blocks', 'daily', 'weekly', 'monthly')

        Returns:
            Report data as a dictionary or None if not found
        """
        return self.service.get_report(report_id, report_type)

    @property
    def recent_cells(self) -> List[str]:
        """Get the list of recent cell IDs."""
        return self.service.recent_cells

    @property
    def recent_blocks(self) -> List[str]:
        """Get the list of recent block IDs."""
        return self.service.recent_blocks

    @property
    def recent_daily_reports(self) -> List[str]:
        """Get the list of recent daily report IDs."""
        return self.service.recent_daily_reports

    @property
    def recent_weekly_reports(self) -> List[str]:
        """Get the list of recent weekly report IDs."""
        return self.service.recent_weekly_reports
