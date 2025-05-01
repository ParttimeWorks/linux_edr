# Installation

Install Linux EDR using `uv` directly from the latest GitHub release or a specific version tag:

```bash
# Install from the latest GitHub release
uv pip install git+https://github.com/ParttimeWorks/linux_edr.git@master
```

## Requirements

- Python 3.11 or later
- [uv](https://github.com/astral-sh/uv) for dependency management
- Linux kernel with ftrace support
- Appropriate permissions to read from `/sys/kernel/tracing/trace_pipe` (typically requires root privileges) 