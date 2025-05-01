import os
import json
import logging
import statistics
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timezone, timedelta
from collections import Counter, defaultdict

from .models import Cell, Block, DailyReport, WeeklyReport, MonthlyReport

logger = logging.getLogger(__name__)

class ReportManager:
    """
    Manages the hierarchical reporting system for Linux EDR.
    
    This class handles the creation, storage, and aggregation of reports at different levels:
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
        self.reporter = reporter  # Instance of Reporter class for LLM analysis
        
        # Create reports directory if it doesn't exist
        os.makedirs(reports_dir, exist_ok=True)
        
        # Create subdirectories for each report level
        for subdir in ["cells", "blocks", "daily", "weekly", "monthly"]:
            os.makedirs(os.path.join(reports_dir, subdir), exist_ok=True)
        
        # Keep track of the most recent reports at each level
        self.recent_cells: List[str] = []
        self.recent_blocks: List[str] = []
        self.recent_daily_reports: List[str] = []
        self.recent_weekly_reports: List[str] = []
        
        # Load existing reports if any
        self._load_existing_reports()
        
        logger.info(f"Report manager initialized at {reports_dir}")
    
    def _load_existing_reports(self) -> None:
        """Load recent reports from disk."""
        # This implementation focuses on recent reports for simplicity
        # In a production system, you might want to load more historical data
        
        # Get the most recent cells (up to 16 for a block)
        self.recent_cells = self._get_recent_reports("cells", 16)
        
        # Get the most recent blocks (up to 6 for a daily report)
        self.recent_blocks = self._get_recent_reports("blocks", 6)
        
        # Get the most recent daily reports (up to 7 for a weekly report)
        self.recent_daily_reports = self._get_recent_reports("daily", 7)
        
        # Get the most recent weekly reports (up to 4 for a monthly report)
        self.recent_weekly_reports = self._get_recent_reports("weekly", 4)
        
        if self.recent_cells:
            logger.info(f"Loaded {len(self.recent_cells)} recent cells")
        if self.recent_blocks:
            logger.info(f"Loaded {len(self.recent_blocks)} recent blocks")
        if self.recent_daily_reports:
            logger.info(f"Loaded {len(self.recent_daily_reports)} recent daily reports")
        if self.recent_weekly_reports:
            logger.info(f"Loaded {len(self.recent_weekly_reports)} recent weekly reports")
    
    def _get_recent_reports(self, report_type: str, limit: int) -> List[str]:
        """
        Get the most recent report IDs of a given type.
        
        Args:
            report_type: Type of report ('cells', 'blocks', etc.)
            limit: Maximum number of reports to retrieve
            
        Returns:
            List of report IDs sorted by recency (newest first)
        """
        dir_path = os.path.join(self.reports_dir, report_type)
        if not os.path.exists(dir_path):
            return []
            
        # Get all JSON files in directory
        files = [f for f in os.listdir(dir_path) if f.endswith('.json')]
        
        # Sort by modification time (newest first)
        files.sort(key=lambda f: os.path.getmtime(os.path.join(dir_path, f)), reverse=True)
        
        # Return report IDs (filename without extension)
        return [os.path.splitext(f)[0] for f in files[:limit]]
    
    def _save_report(self, report: Union[Cell, Block, DailyReport, WeeklyReport, MonthlyReport], 
                    report_type: str) -> None:
        """
        Save a report to disk.
        
        Args:
            report: The report to save
            report_type: Type of report ('cells', 'blocks', etc.)
        """
        # Create filename based on report ID
        filename = f"{report.report_id}.json"
        filepath = os.path.join(self.reports_dir, report_type, filename)
        
        try:
            with open(filepath, 'w') as f:
                json.dump(report.model_dump(), f, indent=2)
            logger.debug(f"Saved {report_type[:-1]} report {report.report_id} to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save {report_type[:-1]} report: {e}")
    
    def _load_report(self, report_id: str, report_type: str) -> Optional[Dict[str, Any]]:
        """
        Load a report from disk.
        
        Args:
            report_id: ID of the report to load
            report_type: Type of report ('cells', 'blocks', etc.)
            
        Returns:
            Report data as a dictionary or None if report not found
        """
        filepath = os.path.join(self.reports_dir, report_type, f"{report_id}.json")
        
        if not os.path.exists(filepath):
            logger.debug(f"Report {report_id} not found at {filepath}")
            return None
            
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load report {report_id}: {e}")
            return None
    
    def create_cell(self, cell: Cell) -> None:
        """
        Save a new Cell report and update the hierarchy.
        
        Args:
            cell: The Cell report to save
        """
        # If we have a reporter and cell doesn't have analysis yet, get analysis
        if self.reporter and not cell.analysis:
            self.reporter.analyze_report(cell)
            
        # Save the cell
        self._save_report(cell, "cells")
        
        # Add to recent cells
        self.recent_cells.insert(0, cell.report_id)
        if len(self.recent_cells) > 16:
            self.recent_cells.pop()
        
        # Check if we have enough cells to create a block
        if len(self.recent_cells) >= 16:
            self._create_block()
    
    def _calculate_severity_from_lower_reports(self, report_data_list: List[Dict[str, Any]]) -> Optional[int]:
        """
        Calculate a severity score based on lower-level reports.
        
        Args:
            report_data_list: List of lower-level report data
            
        Returns:
            Calculated severity or None if no severity data available
        """
        severities = []
        for report in report_data_list:
            if severity := report.get('severity'):
                severities.append(severity)
        
        if not severities:
            return None

        # Calculate the median and add a bias toward higher severity
        # This ensures we don't underestimate security threats
        median = statistics.median(severities)
        max_severity = max(severities)
        
        # Apply a bias formula: 70% median + 30% max to favor higher severities
        weighted_severity = round(0.7 * median + 0.3 * max_severity)
        
        # Ensure the result is between 1 and 5
        return max(1, min(5, weighted_severity))
    
    def _create_block(self) -> None:
        """Create a Block report from recent Cell reports."""
        if len(self.recent_cells) < 16:
            return
        
        # Get the cells to include in this block
        cell_ids = self.recent_cells[:16]
        
        # Load the cell data
        cells_data = []
        for cell_id in cell_ids:
            cell_data = self._load_report(cell_id, "cells")
            if cell_data:
                cells_data.append(cell_data)
        
        if not cells_data:
            logger.warning("No valid cell data found for block creation")
            return
            
        # Get time range
        start_times = [datetime.fromisoformat(cell['window_start']) for cell in cells_data]
        end_times = [datetime.fromisoformat(cell['window_end']) for cell in cells_data]
        window_start = min(start_times).isoformat()
        window_end = max(end_times).isoformat()
        
        # Aggregate command counts
        command_counts: Dict[str, int] = defaultdict(int)
        for cell in cells_data:
            for cmd, count in cell.get('command_counts', {}).items():
                command_counts[cmd] += count
        
        # Calculate top processes
        process_counts: Dict[str, int] = defaultdict(int)
        for cell in cells_data:
            for proc_name, cmd_lines in cell.get('process_events', {}).items():
                process_counts[proc_name] += len(cmd_lines)
        
        # Sort and get top 10 processes
        top_processes = dict(sorted(process_counts.items(), key=lambda x: x[1], reverse=True)[:10])
        
        # Create a block ID
        block_id = f"block_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        
        # Calculate total events
        total_events = sum(cell.get('total', 0) for cell in cells_data)
        
        # Calculate severity based on cell severities
        severity = self._calculate_severity_from_lower_reports(cells_data)
        
        # Create the block
        block = Block(
            report_id=block_id,
            window_start=window_start,
            window_end=window_end,
            total_events=total_events,
            cells=cell_ids,
            command_counts=dict(command_counts),
            top_processes=top_processes,
            severity=severity
        )
        
        # Send to LLM for analysis
        if self.reporter:
            self.reporter.analyze_report(block)
        
        # Save the block
        self._save_report(block, "blocks")
        
        # Add to recent blocks
        self.recent_blocks.insert(0, block_id)
        if len(self.recent_blocks) > 6:
            self.recent_blocks.pop()
        
        logger.info(f"Created block {block_id} from {len(cells_data)} cells with severity {severity or 'unknown'}")
        
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
            block_data = self._load_report(block_id, "blocks")
            if block_data:
                blocks_data.append(block_data)
        
        if not blocks_data:
            logger.warning("No valid block data found for daily report creation")
            return
            
        # Get time range
        start_times = [datetime.fromisoformat(block['window_start']) for block in blocks_data]
        end_times = [datetime.fromisoformat(block['window_end']) for block in blocks_data]
        window_start = min(start_times).isoformat()
        window_end = max(end_times).isoformat()
        
        # Get date for the daily report (based on the latest block)
        report_date = datetime.fromisoformat(window_end).strftime("%Y-%m-%d")
        
        # Aggregate command counts
        command_counts: Dict[str, int] = defaultdict(int)
        for block in blocks_data:
            for cmd, count in block.get('command_counts', {}).items():
                command_counts[cmd] += count
        
        # Aggregate process counts
        process_counts: Dict[str, int] = defaultdict(int)
        for block in blocks_data:
            for proc, count in block.get('top_processes', {}).items():
                process_counts[proc] += count
        
        # Sort and get top 15 processes
        top_processes = dict(sorted(process_counts.items(), key=lambda x: x[1], reverse=True)[:15])
        
        # Create a daily report ID
        daily_id = f"daily_{report_date.replace('-', '')}"
        
        # Calculate total events
        total_events = sum(block.get('total_events', 0) for block in blocks_data)
        
        # Calculate severity based on block severities
        severity = self._calculate_severity_from_lower_reports(blocks_data)
        
        # Collect unusual activity from blocks
        unusual_activity = []
        for block in blocks_data:
            # If block has a high severity (4-5), treat it as unusual activity
            if block.get('severity', 0) >= 4:
                unusual_activity.append({
                    "time_window": f"{block['window_start']} to {block['window_end']}",
                    "severity": block.get('severity'),
                    "summary": block.get('analysis', 'High severity activity detected')[:100] + "..."
                })
        
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
            severity=severity
        )
        
        # Send to LLM for analysis
        if self.reporter:
            self.reporter.analyze_report(daily_report)
        
        # Save the daily report
        self._save_report(daily_report, "daily")
        
        # Add to recent daily reports
        self.recent_daily_reports.insert(0, daily_id)
        if len(self.recent_daily_reports) > 7:
            self.recent_daily_reports.pop()
        
        logger.info(f"Created daily report {daily_id} from {len(blocks_data)} blocks with severity {severity or 'unknown'}")
        
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
            report_data = self._load_report(daily_id, "daily")
            if report_data:
                daily_data.append(report_data)
        
        if not daily_data:
            logger.warning("No valid daily report data found for weekly report creation")
            return
            
        # Get date range
        daily_dates = [report['date'] for report in daily_data]
        daily_dates.sort()  # Sort chronologically
        
        week_start_date = daily_dates[0]
        week_end_date = daily_dates[-1]
        
        # Extract top commands across all daily reports
        all_commands: Dict[str, int] = defaultdict(int)
        for report in daily_data:
            for cmd, count in report.get('command_counts', {}).items():
                all_commands[cmd] += count
        
        # Get top 10 commands overall
        top_commands = dict(sorted(all_commands.items(), key=lambda x: x[1], reverse=True)[:10])
        
        # Track command trends by day
        command_trends: Dict[str, List[int]] = {cmd: [0] * 7 for cmd in top_commands}
        
        # Build daily command trends
        for i, report in enumerate(sorted(daily_data, key=lambda x: x['date'])):
            for cmd in top_commands:
                if cmd in report.get('command_counts', {}):
                    command_trends[cmd][i] = report['command_counts'][cmd]
        
        # Extract top processes across all daily reports
        all_processes: Dict[str, int] = defaultdict(int)
        for report in daily_data:
            for proc, count in report.get('top_processes', {}).items():
                all_processes[proc] += count
        
        # Get top 10 processes overall
        top_processes = dict(sorted(all_processes.items(), key=lambda x: x[1], reverse=True)[:10])
        
        # Track process trends by day
        process_trends: Dict[str, List[int]] = {proc: [0] * 7 for proc in top_processes}
        
        # Build daily process trends
        for i, report in enumerate(sorted(daily_data, key=lambda x: x['date'])):
            for proc in top_processes:
                if proc in report.get('top_processes', {}):
                    process_trends[proc][i] = report['top_processes'][proc]
        
        # Create a weekly report ID
        weekly_id = f"weekly_{week_start_date.replace('-', '')}_{week_end_date.replace('-', '')}"
        
        # Calculate total events
        total_events = sum(report.get('total_events', 0) for report in daily_data)
        
        # Collect security incidents from daily reports
        security_incidents = []
        for report in daily_data:
            # Any unusual activity from daily reports becomes an incident
            if report.get('unusual_activity'):
                for activity in report.get('unusual_activity', []):
                    security_incidents.append({
                        "date": report['date'],
                        "details": activity,
                        "risk_level": "high" if activity.get('severity', 0) >= 4 else "medium"
                    })
        
        # Calculate severity based on daily report severities
        severity = self._calculate_severity_from_lower_reports(daily_data)
        
        # Calculate risk score (0-100) from severity (1-5)
        # This is just a linear transformation from severity to match the existing model
        risk_score = min(20 * (severity or 2), 100) if severity else 40  # Default to moderate risk
        
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
            severity=severity
        )
        
        # Send to LLM for analysis
        if self.reporter:
            self.reporter.analyze_report(weekly_report)
        
        # Save the weekly report
        self._save_report(weekly_report, "weekly")
        
        # Add to recent weekly reports
        self.recent_weekly_reports.insert(0, weekly_id)
        if len(self.recent_weekly_reports) > 4:
            self.recent_weekly_reports.pop()
        
        logger.info(f"Created weekly report {weekly_id} from {len(daily_data)} daily reports with severity {severity or 'unknown'}")
        
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
            report_data = self._load_report(weekly_id, "weekly")
            if report_data:
                weekly_data.append(report_data)
        
        if not weekly_data:
            logger.warning("No valid weekly report data found for monthly report creation")
            return
            
        # Get the month based on the contained weekly reports
        start_dates = [report['week_start_date'] for report in weekly_data]
        end_dates = [report['week_end_date'] for report in weekly_data]
        
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
            for cmd, trends in report.get('command_trends', {}).items():
                command_summary[cmd] += sum(trends)
        
        # Aggregate process counts
        process_summary: Dict[str, int] = defaultdict(int)
        for report in weekly_data:
            for proc, trends in report.get('process_trends', {}).items():
                process_summary[proc] += sum(trends)
        
        # Sort by count (descending)
        command_summary = dict(sorted(command_summary.items(), key=lambda x: x[1], reverse=True)[:20])
        process_summary = dict(sorted(process_summary.items(), key=lambda x: x[1], reverse=True)[:20])
        
        # Create a monthly report ID
        monthly_id = f"monthly_{month.replace('-', '')}"
        
        # Calculate total events
        total_events = sum(report.get('total_events', 0) for report in weekly_data)
        
        # Calculate severity based on weekly report severities
        severity = self._calculate_severity_from_lower_reports(weekly_data)
        
        # Calculate average risk score
        avg_risk_score = int(sum(report.get('risk_score', 0) for report in weekly_data) / len(weekly_data))
        
        # Count security incidents
        all_incidents = []
        for report in weekly_data:
            all_incidents.extend(report.get('security_incidents', []))
            
        # Create security summary
        security_summary = {
            "total_incidents": len(all_incidents),
            "high_risk_incidents": sum(1 for inc in all_incidents if inc.get("risk_level", "").lower() == "high"),
            "medium_risk_incidents": sum(1 for inc in all_incidents if inc.get("risk_level", "").lower() == "medium"),
            "low_risk_incidents": sum(1 for inc in all_incidents if inc.get("risk_level", "").lower() == "low"),
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
            severity=severity
        )
        
        # Send to LLM for analysis
        if self.reporter:
            self.reporter.analyze_report(monthly_report)
            
            # Update recommendations from the LLM analysis if available
            if monthly_report.analysis:
                # Extract recommendations from analysis
                # Look for lines starting with "Recommendation" or in a section called "Recommendations"
                lines = monthly_report.analysis.split('\n')
                rec_section = False
                ai_recommendations = []
                
                for line in lines:
                    line = line.strip()
                    if "recommendation" in line.lower() or "recommend" in line.lower():
                        if line.startswith("-") or line.startswith("*"):
                            ai_recommendations.append(line[1:].strip())
                        elif ":" in line:
                            ai_recommendations.append(line.split(":", 1)[1].strip())
                    elif line.lower() in ["recommendations:", "recommendations", "strategic recommendations:"]:
                        rec_section = True
                    elif rec_section and line.startswith("-"):
                        ai_recommendations.append(line[1:].strip())
                    elif rec_section and line and line[0].isdigit() and "." in line[:3]:
                        ai_recommendations.append(line.split(".", 1)[1].strip())
                    elif rec_section and line == "":
                        rec_section = False
                
                if ai_recommendations:
                    monthly_report.recommendations = ai_recommendations
                    # Save the report again with the updated recommendations
                    self._save_report(monthly_report, "monthly")
        
        # Save the monthly report
        self._save_report(monthly_report, "monthly")
        
        logger.info(f"Created monthly report {monthly_id} from {len(weekly_data)} weekly reports with severity {severity or 'unknown'}")
    
    def get_report(self, report_id: str, report_type: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a report by ID and type.
        
        Args:
            report_id: ID of the report to retrieve
            report_type: Type of report ('cells', 'blocks', 'daily', 'weekly', 'monthly')
            
        Returns:
            Report data as a dictionary or None if not found
        """
        return self._load_report(report_id, report_type) 