import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Union
from collections import defaultdict

from linux_edr.domain.models.reports import Cell, Block, DailyReport, WeeklyReport, MonthlyReport
from linux_edr.infrastructure.repositories.report_repository import ReportRepository
from .severity_calculator import SeverityCalculator

logger = logging.getLogger(__name__)


class ReportService:
    """
    Service for creating, managing, and analyzing reports in the hierarchical reporting system.

    Responsible for:
    - Creating higher-level reports from lower-level ones
    - Calculating aggregated metrics and trends
    - Determining unusual activity and security incidents
    """

    def __init__(
        self,
        cell_repository: ReportRepository[Cell],
        block_repository: ReportRepository[Block],
        daily_repository: ReportRepository[DailyReport],
        weekly_repository: ReportRepository[WeeklyReport],
        monthly_repository: ReportRepository[MonthlyReport],
        reporter=None,
    ):
        """
        Initialize the report service.

        Args:
            cell_repository: Repository for Cell reports
            block_repository: Repository for Block reports
            daily_repository: Repository for DailyReport reports
            weekly_repository: Repository for WeeklyReport reports
            monthly_repository: Repository for MonthlyReport reports
            reporter: Optional reporter instance for LLM analysis
        """
        self.cell_repository = cell_repository
        self.block_repository = block_repository
        self.daily_repository = daily_repository
        self.weekly_repository = weekly_repository
        self.monthly_repository = monthly_repository
        self.reporter = reporter

        # Keep track of the most recent reports at each level
        self.recent_cells: List[str] = cell_repository.get_recent(16)
        self.recent_blocks: List[str] = block_repository.get_recent(6)
        self.recent_daily_reports: List[str] = daily_repository.get_recent(7)
        self.recent_weekly_reports: List[str] = weekly_repository.get_recent(4)

        logger.info(f"Report service initialized")
        if self.recent_cells:
            logger.info(f"Loaded {len(self.recent_cells)} recent cells")
        if self.recent_blocks:
            logger.info(f"Loaded {len(self.recent_blocks)} recent blocks")
        if self.recent_daily_reports:
            logger.info(f"Loaded {len(self.recent_daily_reports)} recent daily reports")
        if self.recent_weekly_reports:
            logger.info(f"Loaded {len(self.recent_weekly_reports)} recent weekly reports")

    def add_cell(self, cell: Cell) -> None:
        """
        Add a new Cell report and cascade creation of higher-level reports if needed.

        Args:
            cell: The Cell report to add
        """
        # If we have a reporter and cell doesn't have analysis yet, get analysis
        if self.reporter and not cell.analysis:
            self.reporter.analyze_report(cell)

        # Save the cell
        self.cell_repository.save(cell)

        # Add to recent cells
        self.recent_cells.insert(0, cell.report_id)
        if len(self.recent_cells) > 16:
            self.recent_cells.pop()

        # Check if we have enough cells to create a block
        if len(self.recent_cells) >= 16:
            self._create_block()

    def _create_block(self) -> None:
        """Create a Block report from recent Cell reports."""
        if len(self.recent_cells) < 16:
            return

        # Get the cells to include in this block
        cell_ids = self.recent_cells[:16]

        # Load the cell data
        cells_data = []
        for cell_id in cell_ids:
            cell_data = self.cell_repository.load(cell_id)
            if cell_data:
                cells_data.append(cell_data)

        if not cells_data:
            logger.warning("No valid cell data found for block creation")
            return

        # Get time range
        start_times = [datetime.fromisoformat(cell["window_start"]) for cell in cells_data]
        end_times = [datetime.fromisoformat(cell["window_end"]) for cell in cells_data]
        window_start = min(start_times).isoformat()
        window_end = max(end_times).isoformat()

        # Aggregate command counts
        command_counts: Dict[str, int] = defaultdict(int)
        for cell in cells_data:
            for cmd, count in cell.get("command_counts", {}).items():
                command_counts[cmd] += count

        # Calculate top processes
        process_counts: Dict[str, int] = defaultdict(int)
        for cell in cells_data:
            for proc_name, cmd_lines in cell.get("process_events", {}).items():
                process_counts[proc_name] += len(cmd_lines)

        # Sort and get top 10 processes
        top_processes = dict(sorted(process_counts.items(), key=lambda x: x[1], reverse=True)[:10])

        # Create a block ID
        block_id = f"block_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        # Calculate total events
        total_events = sum(cell.get("total", 0) for cell in cells_data)

        # Calculate severity based on cell severities
        severity = SeverityCalculator.calculate_from_lower_reports(cells_data)

        # Create the block
        block = Block(
            report_id=block_id,
            window_start=window_start,
            window_end=window_end,
            total_events=total_events,
            cells=cell_ids,
            command_counts=dict(command_counts),
            top_processes=top_processes,
            severity=severity,
        )

        # Send to LLM for analysis
        if self.reporter:
            self.reporter.analyze_report(block)

        # Save the block
        self.block_repository.save(block)

        # Add to recent blocks
        self.recent_blocks.insert(0, block_id)
        if len(self.recent_blocks) > 6:
            self.recent_blocks.pop()

        logger.info(
            f"Created block {block_id} from {len(cells_data)} cells with severity {severity or 'unknown'}"
        )

        # Check if we have enough blocks to create a daily report
        if len(self.recent_blocks) >= 6:
            self._create_daily_report()

    def _create_daily_report(self) -> None:
        """Create a DailyReport from 6 recent Block reports."""
        # Ensure we have enough blocks
        if len(self.recent_blocks) < 6:
            return

        # Get the blocks to include in this daily report
        block_ids = self.recent_blocks[:6]

        # Load the block data
        blocks_data = []
        for block_id in block_ids:
            block_data = self.block_repository.load(block_id)
            if block_data:
                blocks_data.append(block_data)

        if not blocks_data:
            logger.warning("No valid block data found for daily report creation")
            return

        # Get time range
        start_times = [datetime.fromisoformat(block["window_start"]) for block in blocks_data]
        end_times = [datetime.fromisoformat(block["window_end"]) for block in blocks_data]
        window_start = min(start_times).isoformat()
        window_end = max(end_times).isoformat()

        # Get date for the daily report (based on the latest block)
        report_date = datetime.fromisoformat(window_end).strftime("%Y-%m-%d")

        # Aggregate command counts
        command_counts: Dict[str, int] = defaultdict(int)
        for block in blocks_data:
            for cmd, count in block.get("command_counts", {}).items():
                command_counts[cmd] += count

        # Aggregate process counts
        process_counts: Dict[str, int] = defaultdict(int)
        for block in blocks_data:
            for proc, count in block.get("top_processes", {}).items():
                process_counts[proc] += count

        # Sort and get top 15 processes
        top_processes = dict(sorted(process_counts.items(), key=lambda x: x[1], reverse=True)[:15])

        # Create a daily report ID
        daily_id = f"daily_{report_date.replace('-', '')}"

        # Calculate total events
        total_events = sum(block.get("total_events", 0) for block in blocks_data)

        # Calculate severity based on block severities
        severity = SeverityCalculator.calculate_from_lower_reports(blocks_data)

        # Collect unusual activity from blocks
        unusual_activity = []
        for block in blocks_data:
            # If block has a high severity (4-5), treat it as unusual activity
            if block.get("severity", 0) >= 4:
                unusual_activity.append(
                    {
                        "time_window": f"{block['window_start']} to {block['window_end']}",
                        "severity": block.get("severity"),
                        "summary": block.get("analysis", "High severity activity detected")[:100]
                        + "...",
                    }
                )

        # Create the daily report
        daily_report = DailyReport(
            report_id=daily_id,
            date=report_date,
            window_start=window_start,
            window_end=window_end,
            total_events=total_events,
            blocks=block_ids,
            command_counts=dict(command_counts),
            top_processes=top_processes,
            unusual_activity=unusual_activity,
            severity=severity,
        )

        # Send to LLM for analysis
        if self.reporter:
            self.reporter.analyze_report(daily_report)

        # Save the daily report
        self.daily_repository.save(daily_report)

        # Add to recent daily reports
        self.recent_daily_reports.insert(0, daily_id)
        if len(self.recent_daily_reports) > 7:
            self.recent_daily_reports.pop()

        logger.info(
            f"Created daily report {daily_id} from {len(blocks_data)} blocks with severity {severity or 'unknown'}"
        )

        # Check if we have enough daily reports to create a weekly report
        if len(self.recent_daily_reports) >= 7:
            self._create_weekly_report()

    def _create_weekly_report(self) -> None:
        """Create a WeeklyReport from 7 recent DailyReport reports."""
        # Ensure we have enough daily reports
        if len(self.recent_daily_reports) < 7:
            return

        # Get the daily reports to include in this weekly report
        daily_ids = self.recent_daily_reports[:7]

        # Load the daily report data
        daily_data = []
        for daily_id in daily_ids:
            report_data = self.daily_repository.load(daily_id)
            if report_data:
                daily_data.append(report_data)

        if not daily_data:
            logger.warning("No valid daily report data found for weekly report creation")
            return

        # Get date range
        daily_dates = [report["date"] for report in daily_data]
        daily_dates.sort()  # Sort chronologically

        week_start_date = daily_dates[0]
        week_end_date = daily_dates[-1]

        # Extract top commands across all daily reports
        all_commands: Dict[str, int] = defaultdict(int)
        for report in daily_data:
            for cmd, count in report.get("command_counts", {}).items():
                all_commands[cmd] += count

        # Get top 10 commands overall
        top_commands = dict(sorted(all_commands.items(), key=lambda x: x[1], reverse=True)[:10])

        # Track command trends by day
        command_trends: Dict[str, List[int]] = {cmd: [0] * 7 for cmd in top_commands}

        # Build daily command trends
        for i, report in enumerate(sorted(daily_data, key=lambda x: x["date"])):
            for cmd in top_commands:
                if cmd in report.get("command_counts", {}):
                    command_trends[cmd][i] = report["command_counts"][cmd]

        # Extract top processes across all daily reports
        all_processes: Dict[str, int] = defaultdict(int)
        for report in daily_data:
            for proc, count in report.get("top_processes", {}).items():
                all_processes[proc] += count

        # Get top 10 processes overall
        top_processes = dict(sorted(all_processes.items(), key=lambda x: x[1], reverse=True)[:10])

        # Track process trends by day
        process_trends: Dict[str, List[int]] = {proc: [0] * 7 for proc in top_processes}

        # Build daily process trends
        for i, report in enumerate(sorted(daily_data, key=lambda x: x["date"])):
            for proc in top_processes:
                if proc in report.get("top_processes", {}):
                    process_trends[proc][i] = report["top_processes"][proc]

        # Create a weekly report ID
        weekly_id = f"weekly_{week_start_date.replace('-', '')}_{week_end_date.replace('-', '')}"

        # Calculate total events
        total_events = sum(report.get("total_events", 0) for report in daily_data)

        # Collect security incidents from daily reports
        security_incidents = []
        for report in daily_data:
            # Any unusual activity from daily reports becomes an incident
            if report.get("unusual_activity"):
                for activity in report.get("unusual_activity", []):
                    security_incidents.append(
                        {
                            "date": report["date"],
                            "details": activity,
                            "risk_level": "high" if activity.get("severity", 0) >= 4 else "medium",
                        }
                    )

        # Calculate severity based on daily report severities
        severity = SeverityCalculator.calculate_from_lower_reports(daily_data)

        # Calculate risk score (0-100) from severity (1-5)
        risk_score = SeverityCalculator.calculate_risk_score(severity)

        # Create the weekly report
        weekly_report = WeeklyReport(
            report_id=weekly_id,
            week_start_date=week_start_date,
            week_end_date=week_end_date,
            total_events=total_events,
            daily_reports=daily_ids,
            command_trends=command_trends,
            process_trends=process_trends,
            security_incidents=security_incidents,
            risk_score=risk_score,
            severity=severity,
        )

        # Send to LLM for analysis
        if self.reporter:
            self.reporter.analyze_report(weekly_report)

        # Save the weekly report
        self.weekly_repository.save(weekly_report)

        # Add to recent weekly reports
        self.recent_weekly_reports.insert(0, weekly_id)
        if len(self.recent_weekly_reports) > 4:
            self.recent_weekly_reports.pop()

        logger.info(
            f"Created weekly report {weekly_id} from {len(daily_data)} daily reports with severity {severity or 'unknown'}"
        )

        # Check if we have enough weekly reports to create a monthly report
        if len(self.recent_weekly_reports) >= 4:
            self._create_monthly_report()

    def _create_monthly_report(self) -> None:
        """Create a MonthlyReport from approximately 4 recent WeeklyReport reports."""
        # Ensure we have enough weekly reports
        if len(self.recent_weekly_reports) < 4:
            return

        # Get the weekly reports to include in this monthly report
        weekly_ids = self.recent_weekly_reports[:4]

        # Load the weekly report data
        weekly_data = []
        for weekly_id in weekly_ids:
            report_data = self.weekly_repository.load(weekly_id)
            if report_data:
                weekly_data.append(report_data)

        if not weekly_data:
            logger.warning("No valid weekly report data found for monthly report creation")
            return

        # Get the month based on the contained weekly reports
        start_dates = [report["week_start_date"] for report in weekly_data]
        end_dates = [report["week_end_date"] for report in weekly_data]

        all_dates = start_dates + end_dates
        all_dates.sort()

        start_date = all_dates[0]
        end_date = all_dates[-1]

        # Get the month (from the start date)
        start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
        month = start_datetime.strftime("%Y-%m")

        # Aggregate command counts
        command_summary: Dict[str, int] = defaultdict(int)
        for report in weekly_data:
            for cmd, trends in report.get("command_trends", {}).items():
                command_summary[cmd] += sum(trends)

        # Aggregate process counts
        process_summary: Dict[str, int] = defaultdict(int)
        for report in weekly_data:
            for proc, trends in report.get("process_trends", {}).items():
                process_summary[proc] += sum(trends)

        # Sort by count (descending)
        command_summary = dict(
            sorted(command_summary.items(), key=lambda x: x[1], reverse=True)[:20]
        )
        process_summary = dict(
            sorted(process_summary.items(), key=lambda x: x[1], reverse=True)[:20]
        )

        # Create a monthly report ID
        monthly_id = f"monthly_{month.replace('-', '')}"

        # Calculate total events
        total_events = sum(report.get("total_events", 0) for report in weekly_data)

        # Calculate severity based on weekly report severities
        severity = SeverityCalculator.calculate_from_lower_reports(weekly_data)

        # Calculate average risk score
        avg_risk_score = int(
            sum(report.get("risk_score", 0) for report in weekly_data) / len(weekly_data)
        )

        # Count security incidents
        all_incidents = []
        for report in weekly_data:
            all_incidents.extend(report.get("security_incidents", []))

        # Create security summary
        security_summary = {
            "total_incidents": len(all_incidents),
            "high_risk_incidents": sum(
                1 for inc in all_incidents if inc.get("risk_level", "").lower() == "high"
            ),
            "medium_risk_incidents": sum(
                1 for inc in all_incidents if inc.get("risk_level", "").lower() == "medium"
            ),
            "low_risk_incidents": sum(
                1 for inc in all_incidents if inc.get("risk_level", "").lower() == "low"
            ),
        }

        # Generate basic recommendations based on severity
        recommendations = []
        if severity and severity >= 4:
            recommendations.append("Conduct a thorough security audit of all systems")
            recommendations.append("Review user privileges and access controls")
            recommendations.append("Implement additional monitoring for high-risk commands")
        elif severity and severity >= 3:
            recommendations.append("Review security logs for suspicious patterns")
            recommendations.append("Update system security policies")

        # Create the monthly report
        monthly_report = MonthlyReport(
            report_id=monthly_id,
            month=month,
            start_date=start_date,
            end_date=end_date,
            total_events=total_events,
            weekly_reports=weekly_ids,
            command_summary=command_summary,
            process_summary=process_summary,
            security_summary=security_summary,
            risk_score=avg_risk_score,
            recommendations=recommendations,
            severity=severity,
        )

        # Send to LLM for analysis
        if self.reporter:
            self.reporter.analyze_report(monthly_report)

            # Update recommendations from the LLM analysis if available
            if monthly_report.analysis:
                # Extract recommendations from analysis
                lines = monthly_report.analysis.split("\n")
                rec_section = False
                ai_recommendations = []

                for line in lines:
                    line = line.strip()
                    # Check for section headers
                    if line.lower() in [
                        "recommendations:",
                        "recommendations",
                        "strategic recommendations:",
                        "strategic recommendations",
                        "security recommendations:",
                        "security recommendations",
                    ]:
                        rec_section = True
                        continue

                    # If we're in a recommendations section
                    if rec_section:
                        # Empty line could end the section
                        if not line:
                            # But only end if we've found at least one recommendation
                            if ai_recommendations:
                                rec_section = False
                            continue

                        # Check for bullet points or numbered items
                        if line.startswith("-") or line.startswith("*"):
                            ai_recommendations.append(line[1:].strip())
                        elif line and line[0].isdigit() and ("." in line[:3] or ")" in line[:3]):
                            # Handle numbered items like "1. " or "1) "
                            parts = line.split(".", 1) if "." in line[:3] else line.split(")", 1)
                            if len(parts) > 1:
                                ai_recommendations.append(parts[1].strip())

                    # Check for standalone recommendations with indicators
                    elif "recommend" in line.lower():
                        if line.startswith("-") or line.startswith("*"):
                            ai_recommendations.append(line[1:].strip())
                        elif ":" in line:
                            parts = line.split(":", 1)
                            if len(parts) > 1 and "recommend" in parts[0].lower():
                                ai_recommendations.append(parts[1].strip())

                # Also look for specific patterns that might contain recommendations
                if not ai_recommendations:
                    for line in lines:
                        line = line.strip()
                        if line.lower().startswith(
                            (
                                "update ",
                                "implement ",
                                "enable ",
                                "configure ",
                                "review ",
                                "monitor ",
                            )
                        ):
                            if len(line) > 10:  # Minimum reasonable length
                                ai_recommendations.append(line)

                # If we found recommendations, update the report
                if ai_recommendations:
                    monthly_report.recommendations = ai_recommendations
                    # Save the report again with the updated recommendations
                    self.monthly_repository.save(monthly_report)

        # Save the monthly report
        self.monthly_repository.save(monthly_report)

        logger.info(
            f"Created monthly report {monthly_id} from {len(weekly_data)} weekly reports with severity {severity or 'unknown'}"
        )

    def get_report(self, report_id: str, report_type: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a report by ID and type.

        Args:
            report_id: ID of the report to retrieve
            report_type: Type of report ('cells', 'blocks', 'daily', 'weekly', 'monthly')

        Returns:
            Report data as a dictionary or None if not found
        """
        if report_type == "cells":
            return self.cell_repository.load(report_id)
        elif report_type == "blocks":
            return self.block_repository.load(report_id)
        elif report_type == "daily":
            return self.daily_repository.load(report_id)
        elif report_type == "weekly":
            return self.weekly_repository.load(report_id)
        elif report_type == "monthly":
            return self.monthly_repository.load(report_id)
        else:
            logger.error(f"Unknown report type: {report_type}")
            return None
