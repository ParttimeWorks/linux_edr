from collections import Counter
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Union, Optional
from .models import SummaryReport, Cell


def build_summary(
    events: List[Dict[str, Any]], window_minutes: int, as_cell: bool = False
) -> Union[SummaryReport, Cell]:
    """
    Build a summary report for the given events.

    Args:
        events: List of execve events to summarize
        window_minutes: Time window in minutes
        as_cell: Whether to return a Cell instead of SummaryReport

    Returns:
        A SummaryReport or Cell object containing the command counts and time window
    """
    now = datetime.now(timezone.utc)
    start = now - timedelta(minutes=window_minutes)

    # Count occurrences of each command, ignoring events without a command field (e.g., UnparsedEvent)
    counts = Counter(
        evt["command"]
        for evt in events
        if isinstance(evt, dict) and evt.get("command")
    )
    proc_summary: Dict[str, int] = dict(counts)

    report_data = {
        "report_id": now.isoformat(),
        "window_start": start.isoformat(),
        "window_end": now.isoformat(),
        "total": len(events),
        "command_counts": proc_summary,
    }

    if as_cell:
        return Cell(**report_data)
    else:
        return SummaryReport(**report_data)
