# Application Use Cases

The application layer contains use cases that implement specific business processes. Each use case represents a specific action or workflow that the system can perform, orchestrating multiple services to fulfill a business need.

## Event Collection Use Cases

Use cases for collecting and processing system events.

### CollectEventsUseCase

Collects events from the system and prepares them for processing.

```python
# Example usage
from linux_edr.application.use_cases import CollectEventsUseCase

# Create use case instance (with dependencies injected)
collect_events_use_case = CollectEventsUseCase(
    trace_reader=trace_reader,
    aggregator=aggregator
)

# Execute use case
collect_events_use_case.execute()
```

### ProcessEventsUseCase

Processes collected events and prepares them for reporting.

```python
# Example usage
from linux_edr.application.use_cases import ProcessEventsUseCase

# Create use case instance (with dependencies injected)
process_events_use_case = ProcessEventsUseCase(
    aggregator=aggregator,
    event_enrichment_service=event_enrichment_service,
    event_analysis_service=event_analysis_service
)

# Execute use case
processed_events = process_events_use_case.execute()
```

## Reporting Use Cases

Use cases for generating and managing reports.

### GenerateCellReportUseCase

Generates a cell report from collected events.

```python
# Example usage
from linux_edr.application.use_cases import GenerateCellReportUseCase

# Create use case instance (with dependencies injected)
generate_cell_report_use_case = GenerateCellReportUseCase(
    aggregator=aggregator,
    report_generation_service=report_generation_service,
    report_repository=report_repository
)

# Execute use case
cell_report = generate_cell_report_use_case.execute()
```

### GenerateBlockReportUseCase

Generates a block report from cell reports.

```python
# Example usage
from linux_edr.application.use_cases import GenerateBlockReportUseCase

# Create use case instance (with dependencies injected)
generate_block_report_use_case = GenerateBlockReportUseCase(
    report_repository=report_repository,
    report_generation_service=report_generation_service
)

# Execute use case
block_report = generate_block_report_use_case.execute()
```

### AnalyzeReportWithAIUseCase

Analyzes a report using AI services.

```python
# Example usage
from linux_edr.application.use_cases import AnalyzeReportWithAIUseCase

# Create use case instance (with dependencies injected)
analyze_report_with_ai_use_case = AnalyzeReportWithAIUseCase(
    report_repository=report_repository,
    ai_analysis_service=ai_analysis_service
)

# Execute use case
ai_analysis = analyze_report_with_ai_use_case.execute(report_id="cell-2023-05-12-12-00")
```

## System Management Use Cases

Use cases for managing the system's operation.

### StartApplicationUseCase

Starts all components of the application.

```python
# Example usage
from linux_edr.application.use_cases import StartApplicationUseCase

# Create use case instance (with dependencies injected)
start_application_use_case = StartApplicationUseCase(
    trace_reader=trace_reader,
    aggregator=aggregator,
    scheduler=scheduler
)

# Execute use case
start_application_use_case.execute()
```

### ShutdownApplicationUseCase

Gracefully shuts down all components of the application.

```python
# Example usage
from linux_edr.application.use_cases import ShutdownApplicationUseCase

# Create use case instance (with dependencies injected)
shutdown_application_use_case = ShutdownApplicationUseCase(
    trace_reader=trace_reader,
    aggregator=aggregator,
    scheduler=scheduler
)

# Execute use case
shutdown_application_use_case.execute()
``` 