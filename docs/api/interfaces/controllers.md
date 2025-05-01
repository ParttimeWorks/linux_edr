# Interface Controllers

The interfaces layer contains controllers that handle incoming requests and convert them to application use case calls. These controllers act as entry points to the system.

## CLI Controllers

Controllers for command-line interface interactions.

### CLIController

Handles command-line interface requests.

```python
# Example usage
from linux_edr.interfaces.controllers import CLIController

# Create controller instance (with dependencies injected)
cli_controller = CLIController(
    start_application_use_case=start_application_use_case,
    shutdown_application_use_case=shutdown_application_use_case
)

# Use controller to handle CLI commands
cli_controller.handle_start_command()
cli_controller.handle_stop_command()
```

### ReportCommandController

Handles report-related commands from the CLI.

```python
# Example usage
from linux_edr.interfaces.controllers import ReportCommandController

# Create controller instance (with dependencies injected)
report_command_controller = ReportCommandController(
    report_repository=report_repository
)

# Use controller to handle report commands
report_command_controller.handle_list_reports_command()
report_command_controller.handle_show_report_command(report_id)
report_command_controller.handle_export_report_command(report_id, output_file)
```

### ConfigCommandController

Handles configuration-related commands from the CLI.

```python
# Example usage
from linux_edr.interfaces.controllers import ConfigCommandController

# Create controller instance (with dependencies injected)
config_command_controller = ConfigCommandController(
    config_repository=config_repository
)

# Use controller to handle config commands
config_command_controller.handle_show_config_command()
config_command_controller.handle_update_config_command(config_key, config_value)
```

## API Controllers

Controllers for API interactions.

### ReportAPIController

Handles report-related API requests.

```python
# Example usage
from linux_edr.interfaces.controllers import ReportAPIController

# Create controller instance (with dependencies injected)
report_api_controller = ReportAPIController(
    report_repository=report_repository
)

# Use controller to handle API requests
reports = report_api_controller.handle_get_reports_request(limit=10, offset=0)
report = report_api_controller.handle_get_report_request(report_id)
```

### EventAPIController

Handles event-related API requests.

```python
# Example usage
from linux_edr.interfaces.controllers import EventAPIController

# Create controller instance (with dependencies injected)
event_api_controller = EventAPIController(
    event_repository=event_repository
)

# Use controller to handle API requests
events = event_api_controller.handle_get_events_request(
    start_time=start_time,
    end_time=end_time,
    limit=100
)
```

### AIAnalysisAPIController

Handles AI analysis-related API requests.

```python
# Example usage
from linux_edr.interfaces.controllers import AIAnalysisAPIController

# Create controller instance (with dependencies injected)
ai_analysis_api_controller = AIAnalysisAPIController(
    analyze_report_with_ai_use_case=analyze_report_with_ai_use_case,
    ai_analysis_repository=ai_analysis_repository
)

# Use controller to handle API requests
analysis = ai_analysis_api_controller.handle_get_analysis_request(report_id)
new_analysis = ai_analysis_api_controller.handle_create_analysis_request(report_id)
``` 