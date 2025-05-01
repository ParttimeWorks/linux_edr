# Models API

This page documents the Pydantic models used for representing events and reports in the legacy codebase.

## Event Models

### CommandLine

Represents a command line with command name and arguments.

```python
from linux_edr.models import CommandLine

cmd = CommandLine(
    command="ls",
    args=["-la", "/home"]
)
```

### ProcessEvents

Collection of process execution events.

```python
from linux_edr.models import ProcessEvents

events = ProcessEvents(
    events=[event1, event2, event3]
)
```

## Report Models

### SummaryReport

Base class for all summary reports.

```python
from linux_edr.models import SummaryReport

# Used as a base class for specific report types
```

### Cell

Represents a 5-minute report cell.

```python
from linux_edr.models import Cell

cell = Cell(
    id="cell-2023-05-12-12-00",
    start_time=datetime.now(),
    end_time=datetime.now() + timedelta(minutes=5),
    command_count=42,
    unique_commands=15,
    # other fields...
)
```

### Block

Represents an hourly report block containing multiple cells.

```python
from linux_edr.models import Block

block = Block(
    id="block-2023-05-12-12",
    start_time=datetime.now(),
    end_time=datetime.now() + timedelta(hours=1),
    cells=["cell-1", "cell-2", "cell-3"],
    # other fields...
)
```

### DailyReport

Represents a daily report containing multiple blocks.

```python
from linux_edr.models import DailyReport

daily = DailyReport(
    id="daily-2023-05-12",
    start_time=datetime.now(),
    end_time=datetime.now() + timedelta(days=1),
    blocks=["block-1", "block-2", "block-3"],
    # other fields...
)
```

### WeeklyReport

Represents a weekly report containing multiple daily reports.

```python
from linux_edr.models import WeeklyReport

weekly = WeeklyReport(
    id="weekly-2023-05-12",
    start_time=datetime.now(),
    end_time=datetime.now() + timedelta(weeks=1),
    dailies=["daily-1", "daily-2", "daily-3"],
    # other fields...
)
```

### MonthlyReport

Represents a monthly report containing multiple weekly reports.

```python
from linux_edr.models import MonthlyReport

monthly = MonthlyReport(
    id="monthly-2023-05",
    start_time=datetime.now(),
    end_time=datetime.now() + timedelta(days=30),
    weeklies=["weekly-1", "weekly-2", "weekly-3", "weekly-4"],
    # other fields...
)
``` 