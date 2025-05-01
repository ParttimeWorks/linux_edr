import logging.config
from collections import defaultdict
import re
import os
from typing import Dict, List, Optional, Any, NamedTuple, Iterator
from apscheduler.schedulers.background import BackgroundScheduler
from .trace import TraceReader
from .aggregator import Aggregator
from .summary import build_summary
from .reporter import Reporter
from .config import Config
from .report_manager import ReportManager
from .models import Cell

def setup_logging(debug: bool = False) -> None:
    """
    Configure application logging with appropriate levels.
    
    Args:
        debug: Whether to enable debug logging
    """
    log_level = "DEBUG" if debug else "INFO"
    
    logging.config.dictConfig({
        "version": 1,
        "formatters": {"default": {"format": "%(asctime)s %(levelname)s %(message)s"}},
        "handlers": {
            "console": {"class": "logging.StreamHandler", "level": log_level},
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": "linux_edr.log",
                "maxBytes": 10_000_000,
                "backupCount": 5,
                "level": "DEBUG",
            },
        },
        "root": {"handlers": ["console", "file"], "level": log_level},
    })

# Use NamedTuple for better type safety
class ExecveEvent(NamedTuple):
    """Parsed execve event from ftrace."""
    timestamp: str
    pid: int
    command: str
    args: List[str]

# Pre-compile the execve pattern once at import time for better performance
# Example trace snippet:
#   "12345 [678] ... execve("/usr/bin/python3" \"python3\" \"script.py\")"
EXECVE_PATTERN = re.compile(r"(\S+)\s+\[(\d+)\]\s+.*execve.*\((.*?)\)")

def parse_execve(line: str) -> Optional[ExecveEvent]:
    """
    Parse execve events from ftrace output.
    
    Args:
        line: A line from the trace file
        
    Returns:
        ExecveEvent if the line contains an execve syscall, None otherwise
    """
    if not line or not isinstance(line, str):
        return None
        
    try:
        # Re-use the pre-compiled pattern; compiling inside the tight loop is unnecessarily
        # expensive when processing thousands of trace lines per second.
        match = EXECVE_PATTERN.search(line)
        if not match:
            return None
            
        timestamp, pid_str, cmd_args = match.groups()
        
        # Safely parse the pid
        try:
            pid = int(pid_str)
        except ValueError:
            logging.warning(f"Failed to parse PID from trace line: {line}")
            return None
            
        cmd_parts = cmd_args.split() if cmd_args else []
        if not cmd_parts:
            return None
            
        return ExecveEvent(timestamp, pid, cmd_parts[0].strip('"'), cmd_parts[1:])
    except Exception as e:
        logging.error(f"Error parsing execve event: {e}, line: {line}")
        return None

def process_raw_events(events: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """
    Process raw events into the requested format grouping by process name.
    
    Args:
        events: List of execve events to process
        
    Returns:
        Dictionary with process names as keys and lists of command lines as values
    """
    if not events:
        return {}
        
    grouped_events: Dict[str, List[str]] = defaultdict(list)

    for event in events:
        try:
            if process_name := event.get("command"):
                # Join command and args in the most compact/pythonic way
                cmd_line = " ".join([process_name, *map(str, event.get("args", []))])
                grouped_events[process_name].append(cmd_line)
        except Exception as e:
            logging.warning("Error processing event %s: %s", event, e)

    return dict(grouped_events)

class LinuxEDRApp:
    """Main application class for Linux EDR."""
    
    def __init__(
        self, 
        config_path: Optional[str] = None, 
        interval: Optional[int] = None, 
        output_file: Optional[str] = None, 
        debug: Optional[bool] = None
    ) -> None:
        """
        Initialize the Linux EDR application.
        
        Args:
            config_path: Path to config file
            interval: Reporting interval in minutes
            output_file: Path to output file
            debug: Whether to enable debug logging
        """
        # Load configuration
        self.config = Config(config_path)
        
        # Override config with command line arguments if provided
        self.interval = interval if interval is not None else self.config.get("DEFAULT", "report_interval", 15)
        self.output_file = output_file if output_file is not None else self.config.get("DEFAULT", "output_file", "")
        self.debug = debug if debug is not None else self.config.get("DEFAULT", "debug", False)
        
        # Setup logging based on configuration
        setup_logging(self.debug)
        
        # Get trace path from config
        trace_path = self.config.get("DEFAULT", "trace_path", "/sys/kernel/tracing/trace_pipe")
        if not os.path.exists(trace_path):
            logging.warning(f"Trace path {trace_path} does not exist. Will wait for it to appear.")
        
        # Initialize components with configuration
        self.reader = TraceReader(path=trace_path)
        
        # Get buffer size from config
        max_events = self.config.get("ADVANCED", "max_events_buffer", 10000)
        self.agg = Aggregator(maxlen=max_events)
        
        # Configure reporter with OpenAI API key and model
        api_key = self.config.get("OPENAI", "api_key", os.environ.get("OPENAI_API_KEY"))
        model = self.config.get("DEFAULT", "model", "gpt-4o-mini")
        self.rep = Reporter(api_key=api_key, output_file=self.output_file, model=model)
        
        # Initialize report manager
        reports_dir = self.config.get("REPORTS", "reports_dir", "reports")
        self.report_manager = ReportManager(reports_dir)
        
        # Configure scheduler
        self.scheduler = BackgroundScheduler(misfire_grace_time=30)
        self.scheduler.add_job(self._summarize, 'interval', minutes=self.interval, id='summarize')
        
        logging.info(f"Linux EDR initialized with interval={self.interval}m, output={self.output_file or 'none'}")

    def _summarize(self) -> None:
        """Generate and save summary of collected events."""
        events = self.agg.snapshot_and_clear()
        if not events:
            logging.info("No events to summarize")
            return
        
        # Group events by process name as requested
        grouped_events = process_raw_events(events)
        
        # Create the summary - get both SummaryReport and Cell
        window_minutes = self.scheduler.get_job('summarize').trigger.interval.seconds // 60
        summary = build_summary(events, window_minutes=window_minutes, as_cell=False)
        cell = build_summary(events, window_minutes=window_minutes, as_cell=True)
        
        # Set process events in the cell
        cell.process_events = grouped_events
        
        # Check if we should include raw events in reports
        include_raw = self.config.get("ADVANCED", "include_raw_events", True)
        max_lines = self.config.get("ADVANCED", "max_summary_lines", 50)
        
        # Save to file (for backward compatibility) if output file is specified
        if self.output_file:
            # Set process events in the summary for backward compatibility
            summary.process_events = grouped_events
            
            self.rep.save_json(
                summary, 
                include_raw_events=include_raw if len(events) <= max_lines else False,
                raw_events=events if include_raw and len(events) <= max_lines else None
            )
            # Send to LLM for analysis
            self.rep.send_llm(summary)
        
        # Add the cell to the report manager to trigger higher-level report generation
        self.report_manager.create_cell(cell)
        
        logging.info(f"Created cell report {cell.report_id} with {cell.total} events")

    def run(self) -> None:
        """Run the application."""
        try:
            # Start the scheduler
            self.scheduler.start()
            logging.info("Scheduler started")
            
            # Read and process events
            for evt in self.reader:
                if evt:
                    self.agg.add(evt)
                    
        except KeyboardInterrupt:
            logging.info("Application interrupted")
        finally:
            # Shut down cleanly
            self.scheduler.shutdown()
            logging.info("Application stopped") 