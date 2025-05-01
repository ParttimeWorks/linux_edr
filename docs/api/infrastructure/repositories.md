# Infrastructure Repositories

The infrastructure layer provides concrete implementations for repositories and external services. Repositories are responsible for data persistence and retrieval, implementing interfaces defined in the application layer.

## Event Repository

### EventRepository

Manages the persistence and retrieval of events.

```python
# Example usage
from linux_edr.infrastructure.repositories import EventRepository

# Create repository instance
event_repository = EventRepository()

# Use repository to save and retrieve events
event_repository.save(event)
events = event_repository.get_by_timestamp_range(start_time, end_time)
events_by_pid = event_repository.get_by_pid(pid)
```

## Report Repository

### ReportRepository

Manages the persistence and retrieval of reports.

```python
# Example usage
from linux_edr.infrastructure.repositories import ReportRepository

# Create repository instance
report_repository = ReportRepository()

# Use repository to save and retrieve reports
report_repository.save(report)
cell_reports = report_repository.get_cells_by_time_range(start_time, end_time)
block_report = report_repository.get_block_by_id(block_id)
latest_daily_report = report_repository.get_latest_daily_report()
```

### ReportHierarchyRepository

Manages the hierarchical relationship between reports.

```python
# Example usage
from linux_edr.infrastructure.repositories import ReportHierarchyRepository

# Create repository instance
report_hierarchy_repository = ReportHierarchyRepository()

# Use repository to manage report hierarchy
cells_in_block = report_hierarchy_repository.get_cells_for_block(block_id)
blocks_in_daily = report_hierarchy_repository.get_blocks_for_daily(daily_id)
report_hierarchy_repository.associate_cell_with_block(cell_id, block_id)
```

## Configuration Repository

### ConfigRepository

Manages application configuration settings.

```python
# Example usage
from linux_edr.infrastructure.repositories import ConfigRepository

# Create repository instance
config_repository = ConfigRepository()

# Use repository to retrieve configuration
trace_config = config_repository.get_trace_config()
reporting_config = config_repository.get_reporting_config()
ai_config = config_repository.get_ai_config()
```

## AI Analysis Repository

### AIAnalysisRepository

Manages the persistence and retrieval of AI analysis results.

```python
# Example usage
from linux_edr.infrastructure.repositories import AIAnalysisRepository

# Create repository instance
ai_analysis_repository = AIAnalysisRepository()

# Use repository to save and retrieve AI analysis results
ai_analysis_repository.save(analysis_result)
analysis_results = ai_analysis_repository.get_by_report_id(report_id)
latest_analysis = ai_analysis_repository.get_latest()
``` 