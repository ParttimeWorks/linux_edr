import logging.config
from collections import defaultdict
import re
import os
from typing import Dict, List, Optional, Any, NamedTuple, Iterator, Set, Tuple, Union
from apscheduler.schedulers.background import BackgroundScheduler
from .trace import TraceReader
from .aggregator import Aggregator
from .summary import build_summary
from .reporter import Reporter
from .config import Config
from .report_manager import ReportManager
from .models import Cell
from .domain.models.events import BaseSyscallEvent, ExecveEvent


def setup_logging(debug: bool = False) -> None:
    """
    Configure application logging with appropriate levels.

    Args:
        debug: Whether to enable debug logging
    """
    log_level = "DEBUG" if debug else "INFO"

    logging.config.dictConfig(
        {
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
        }
    )


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
        # Re-use the pre-compiled pattern
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
            process_name = event.get("command")
            if not process_name:
                continue

            # Join command and args in the most compact/pythonic way
            cmd_line = " ".join([process_name, *map(str, event.get("args", []))])
            grouped_events[process_name].append(cmd_line)
        except Exception as e:
            logging.warning("Error processing event %s: %s", event, e)

    return dict(grouped_events)


class SyscallTracer:
    """Handles the enabling and management of syscall trace events."""

    def __init__(self, config: Config):
        """
        Initialize the syscall tracer with configuration.

        Args:
            config: Application configuration
        """
        self.config = config
        self.syscall_base = "/sys/kernel/tracing/events/syscalls"

    def enable_syscall_events(self) -> int:
        """
        Enable the syscall trace events specified in configuration.

        Returns:
            Number of successfully enabled events
        """
        # Check if syscall tracing is enabled
        if not self.config.get("ADVANCED", "enable_syscall_tracing", True):
            logging.info("Syscall tracing disabled in configuration")
            return 0

        # Get list of syscalls to trace
        syscalls = self._get_syscalls_to_trace()

        # Enable each syscall's enter and exit events
        return self._enable_events(syscalls)

    def _get_syscalls_to_trace(self) -> List[str]:
        """Get list of syscalls to trace from configuration."""
        syscalls_str = self.config.get("ADVANCED", "syscalls_to_trace", "execve")
        return [s.strip() for s in syscalls_str.split(",")]

    def _enable_events(self, syscalls: List[str]) -> int:
        """
        Enable trace events for the specified syscalls.

        Args:
            syscalls: List of syscall names to enable

        Returns:
            Number of successfully enabled events
        """
        enabled_count = 0

        for syscall in syscalls:
            # Enable enter and exit events for this syscall
            enabled_count += self._enable_syscall(syscall)

        # Log summary
        if enabled_count > 0:
            logging.info(f"Successfully enabled {enabled_count} syscall trace events")
        else:
            logging.warning("Failed to enable any syscall trace events")

        return enabled_count

    def _enable_syscall(self, syscall: str) -> int:
        """
        Enable enter and exit trace events for a single syscall.

        Args:
            syscall: Name of the syscall to enable

        Returns:
            Number of successfully enabled events (0, 1, or 2)
        """
        event_types = ["sys_enter_", "sys_exit_"]
        enabled_count = 0

        for event_prefix in event_types:
            event_path = f"{self.syscall_base}/{event_prefix}{syscall}/enable"
            if self._enable_single_event(event_path):
                enabled_count += 1

        return enabled_count

    def _enable_single_event(self, event_path: str) -> bool:
        """
        Enable a single trace event by writing to its enable file.

        Args:
            event_path: Path to the trace event enable file

        Returns:
            True if successfully enabled, False otherwise
        """
        if not os.path.exists(event_path):
            logging.warning(f"Ftrace event path not found: {event_path}")
            return False

        try:
            logging.info(f"Enabling ftrace event: {event_path}")
            with open(event_path, "w") as f:
                f.write("1")
            logging.debug(f"Successfully enabled {event_path}")
            return True
        except PermissionError:
            logging.error(f"Permission denied enabling {event_path}. Run with sudo.")
            return False
        except Exception as e:
            logging.error(f"Error enabling ftrace event {event_path}: {e}")
            return False


class LinuxEDRApp:
    """Main application class for Linux EDR."""

    def __init__(
        self,
        config_path: Optional[str] = None,
        interval: Optional[int] = None,
        debug: Optional[bool] = None,
    ) -> None:
        """
        Initialize the Linux EDR application.

        Args:
            config_path: Path to config file
            interval: Reporting interval in minutes
            debug: Whether to enable debug logging
        """
        # Load configuration
        self.config = Config(config_path)

        # Override config with command line arguments if provided
        self.interval = (
            interval if interval is not None else self.config.get("DEFAULT", "report_interval", 15)
        )
        self.debug = debug if debug is not None else self.config.get("DEFAULT", "debug", False)
        self.verbose_debug = self.config.get("ADVANCED", "verbose_debug_logging", True)

        # Setup logging based on configuration
        setup_logging(self.debug)

        # Get trace path from config
        trace_path = self.config.get("DEFAULT", "trace_path", "/sys/kernel/tracing/trace_pipe")
        if not os.path.exists(trace_path):
            logging.warning(f"Trace path {trace_path} does not exist. Will wait for it to appear.")

        # Enable required syscall tracing events
        self.syscall_tracer = SyscallTracer(self.config)
        self.syscall_tracer.enable_syscall_events()

        # Initialize components with configuration
        self.reader = TraceReader(path=trace_path)

        # Get buffer size from config
        max_events = self.config.get("ADVANCED", "max_events_buffer", 10000)
        self.agg = Aggregator(maxlen=max_events)

        # Configure reporter with OpenAI API key and model
        api_key = self.config.get("OPENAI", "api_key", os.environ.get("OPENAI_API_KEY"))
        model = self.config.get("DEFAULT", "model", "gpt-4o-mini")
        self.rep = Reporter(api_key=api_key, model=model)

        # Initialize report manager with reporter instance
        reports_dir = self.config.get("REPORTS", "reports_dir", "reports")
        self.report_manager = ReportManager(reports_dir, reporter=self.rep)

        # Configure scheduler
        self.scheduler = BackgroundScheduler(misfire_grace_time=30)
        self.scheduler.add_job(self._summarize, "interval", minutes=self.interval, id="summarize")

        logging.info(f"Linux EDR initialized with interval={self.interval}m")

    def _summarize(self) -> None:
        """Generate and save summary of collected events."""
        events = self.agg.snapshot_and_clear()
        if not events:
            logging.info("No events to summarize")
            return

        # Group events by process name as requested
        grouped_events = process_raw_events(events)

        # Create the summary - get both SummaryReport and Cell
        window_minutes = self.scheduler.get_job("summarize").trigger.interval.seconds // 60
        cell = build_summary(events, window_minutes=window_minutes, as_cell=True)

        # Set process events in the cell
        cell.process_events = grouped_events

        # Add the cell to the report manager - it will handle the LLM analysis
        self.report_manager.create_cell(cell)

        logging.info(f"Created cell report {cell.report_id} with {cell.total} events")

    def _process_event(self, evt: BaseSyscallEvent) -> None:
        """
        Process a single event from the trace reader.

        Args:
            evt: Raw event string from trace_pipe
        """
        if self.verbose_debug:
            self._log_debug_event(evt)

        # If the trace reader already produced a validated ExecveEvent model, buffer it directly.
        if isinstance(evt, BaseSyscallEvent):
            self.agg.add(evt.model_dump() if hasattr(evt, "model_dump") else evt.dict())
            return
        else:
            logging.warning(f"Invalid event type: {type(evt)}")

    def _log_debug_event(self, evt: BaseSyscallEvent) -> None:
        """
        Parse and log detailed event information.

        Args:
            evt: Raw event string from trace_pipe
        """
        if not self.debug or not self.verbose_debug:
            return

        try:
            logging.debug(f"{evt}")
        except Exception as e:
            logging.debug(f"Parse error: {str(e)}")

    def run(self) -> None:
        """Run the application."""
        try:
            # Start the scheduler
            self.scheduler.start()
            logging.info("Scheduler started")

            # Read and process events
            for evt in self.reader:
                if evt:
                    self._process_event(evt)

        except KeyboardInterrupt:
            logging.info("Application interrupted")
        finally:
            # Shut down cleanly
            self.scheduler.shutdown()
            logging.info("Application stopped")
