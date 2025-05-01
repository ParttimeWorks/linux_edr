# Domain Models

The domain layer contains the core business logic and entities of the Linux EDR system. These models are free from dependencies on external systems and define the core data structures.

## Core Models

### Event Models

Domain models for system events captured from the Linux kernel.

```python
# Example usage
from linux_edr.domain.models import Event, EventType, ProcessEvent

# Create an event instance
event = ProcessEvent(
    pid=1234,
    command="ls",
    args=["-la", "/home"],
    timestamp=datetime.now()
)
```

### Report Models

Domain models for different report types in the hierarchical reporting system.

```python
# Example usage
from linux_edr.domain.models import Report, ReportLevel, CellReport

# Create a report instance
report = CellReport(
    id="cell-2023-05-12-12-00",
    timestamp=datetime.now(),
    events=[...],  # List of events
    level=ReportLevel.CELL
)
```

## Value Objects

Immutable objects that model domain concepts.

```python
# Example usage
from linux_edr.domain.models import TimeWindow, ProcessIdentifier

# Create value objects
time_window = TimeWindow(start=datetime.now(), duration=timedelta(minutes=5))
process_id = ProcessIdentifier(pid=1234, command="bash")
```

## Data Transfer Objects (DTOs)

Objects used to transfer data between layers with specific structure.

```python
# Example usage
from linux_edr.domain.models import EventDTO, ReportDTO

# Create DTOs for transferring data
event_dto = EventDTO(
    type="process",
    pid=1234,
    command="ls",
    timestamp="2023-05-12T12:00:00Z"
)
```

## Enumerations

Type-safe enumerations for domain concepts.

```python
# Example usage
from linux_edr.domain.models import EventType, ReportLevel, Severity

# Use enumerations
event_type = EventType.PROCESS
report_level = ReportLevel.BLOCK
severity = Severity.HIGH
```

## Exception Classes

Domain-specific exceptions that represent error cases in the business logic.

```python
# Example usage
from linux_edr.domain.exceptions import InvalidEventError, InvalidReportError

# Raise domain exceptions
if not validate_event(event_data):
    raise InvalidEventError("Event missing required fields")
``` 