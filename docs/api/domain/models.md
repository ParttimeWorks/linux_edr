# Domain Models

The domain layer contains the core business logic and entities of the Linux EDR system. These models are free from dependencies on external systems and define the core data structures.

## Core Models

### Event Models

Domain models for system events captured from the Linux kernel. These models are based on Pydantic for validation and type safety.

All syscall events inherit from a `BaseSyscallEvent`:

```python
from linux_edr.domain.models.events import BaseSyscallEvent

# Base class structure (simplified)
class BaseSyscallEvent(BaseModel):
    timestamp: str
    pid: int
```

Specific syscall events extend this base class, adding relevant fields.

#### Execve Event

```python
from linux_edr.domain.models.events import ExecveEvent

# Example usage
event = ExecveEvent(
    timestamp="12345.67890",
    pid=1234,
    command="ls",
    args=["-la", "/home"],
)
print(event.model_dump())
```

#### Fork/Clone Events

```python
from linux_edr.domain.models.events import ForkEvent, CloneEvent

# Example usage
fork_evt = ForkEvent(timestamp="12346.00000", pid=100, child_pid=101)
clone_evt = CloneEvent(timestamp="12347.00000", pid=200, child_pid=201, flags="CLONE_FS")

print(fork_evt)
print(clone_evt)
```

#### Connect Event

```python
from linux_edr.domain.models.events import ConnectEvent

# Example usage
connect_evt = ConnectEvent(
    timestamp="12348.00000",
    pid=500,
    fd=3,
    address="192.168.1.1:80"
)
print(connect_evt)
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