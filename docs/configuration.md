# Configuration

Linux EDR behavior is controlled via a configuration file, typically named `config.ini`. The tool searches for this file in the following locations (in order):

1.  `./config.ini` (current directory)
2.  `~/.config/linux_edr/config.ini` (user's config directory)
3.  `/etc/linux_edr/config.ini` (system-wide config)
4.  The default `config.ini` included with the package.

You can also specify a path directly using the `--config` command-line option.

## Configuration Options

Here are the available sections and options:

```ini
[DEFAULT]
# Path to the kernel trace_pipe used for monitoring execve events.
# Default: /sys/kernel/tracing/trace_pipe
trace_path = /sys/kernel/tracing/trace_pipe

# Interval (in minutes) at which summary reports (Cells) are generated.
# Default: 15
report_interval = 15

# The OpenAI model to use for security analysis (e.g., gpt-4o-mini, gpt-4).
# Default: gpt-4o-mini
model = gpt-4o-mini

# Enable verbose debug logging (true/false).
# Default: false
debug = false

# Path to save periodic JSON reports (Cells). Leave empty to disable file output.
# The Report Manager will still store hierarchical reports in `reports_dir`.
# Default: (empty string)
output_file = 

[OPENAI]
# Your OpenAI API key. If left empty, the tool will attempt to read the
# OPENAI_API_KEY environment variable.
# Default: (empty string)
api_key = 

[REPORTS]
# The base directory where hierarchical reports (Cells, Blocks, Daily, etc.)
# will be stored in subdirectories.
# Default: reports
reports_dir = reports

[ADVANCED]
# The maximum number of raw events to buffer in memory before being processed
# into a Cell report. Acts as a backpressure mechanism.
# Default: 10000
max_events_buffer = 10000

# Limits the number of command examples per process included in the prompt
# sent to the LLM for Cell-level analysis, preventing overly long prompts.
# Default: 50
max_summary_lines = 50

# Whether to include the raw event data within the saved JSON Cell reports.
# Set to false to reduce storage space if raw data is not needed.
# Default: true
include_raw_events = true

# Whether to include security findings in reports (true/false)
# Default: true
include_security_findings = true

# Whether to log verbose raw event data in debug mode (true/false)
# Default: true
verbose_debug_logging = true

# Whether to enable syscall tracing (true/false)
# Default: true
enable_syscall_tracing = true

# Comma-separated list of syscalls to trace (enter and exit events will be enabled)
# Default: execve,fork,clone,connect
syscalls_to_trace = execve,fork,clone,connect
``` 