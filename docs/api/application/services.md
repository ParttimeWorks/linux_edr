# Application Services

The application layer contains stateless services that implement business rules and orchestrate domain objects. These services don't have direct access to external systems but instead use interfaces implemented by the infrastructure layer.

## Event Processing Services

Services for processing and analyzing events.

### EventAnalysisService

Analyzes events to identify suspicious patterns or anomalies.

```python
# Example usage
from linux_edr.application.services import EventAnalysisService

# Create service instance
event_analysis_service = EventAnalysisService()

# Use service to analyze events
analysis_results = event_analysis_service.analyze_events(events)
suspicious_events = event_analysis_service.identify_suspicious_events(events)
```

### EventEnrichmentService

Enriches raw events with additional contextual information.

```python
# Example usage
from linux_edr.application.services import EventEnrichmentService

# Create service instance
event_enrichment_service = EventEnrichmentService()

# Use service to enrich events
enriched_events = event_enrichment_service.enrich_events(raw_events)
contextualized_event = event_enrichment_service.add_process_context(event)
```

## Reporting Services

Services for generating and managing reports.

### ReportGenerationService

Generates reports from events.

```python
# Example usage
from linux_edr.application.services import ReportGenerationService

# Create service instance
report_generation_service = ReportGenerationService()

# Use service to generate reports
cell_report = report_generation_service.generate_cell_report(events)
block_report = report_generation_service.generate_block_report(cell_reports)
daily_report = report_generation_service.generate_daily_report(block_reports)
```

### ReportAnalysisService

Analyzes reports to extract insights and identify patterns.

```python
# Example usage
from linux_edr.application.services import ReportAnalysisService

# Create service instance
report_analysis_service = ReportAnalysisService()

# Use service to analyze reports
insights = report_analysis_service.extract_insights(report)
patterns = report_analysis_service.identify_patterns(reports)
```

## AI Integration Services

Services for AI-based analysis and integration.

### AIAnalysisService

Provides AI-powered analysis of events and reports.

```python
# Example usage
from linux_edr.application.services import AIAnalysisService

# Create service instance
ai_analysis_service = AIAnalysisService()

# Use service for AI analysis
ai_analysis = ai_analysis_service.analyze_report(report)
summary = ai_analysis_service.generate_summary(report)
recommendations = ai_analysis_service.generate_recommendations(report)
``` 