# Development Guide

Contributions and local development are welcome!

## Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/ParttimeWorks/linux_edr.git
    cd linux-edr
    ```

2.  **Install in editable mode with development dependencies:**
    We use `uv` for all dependency management.
    ```bash
    # Installs the package itself and dependencies listed under [project.optional-dependencies]
    # in pyproject.toml (like pytest, mypy, black, mkdocs, etc.)
    uv pip install -e .[dev]
    ```

## Running Tests

The project uses `pytest` for testing.

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test files or functions
uv run pytest tests/test_app.py::test_parse_execve
```

## Type Checking

We use `mypy` for static type checking.

```bash
uv run mypy linux_edr
```

## Code Style

Code style is enforced using `black`.

```bash
# Check formatting
uv run black --check .

# Apply formatting
uv run black .
```

## Building Documentation

Documentation is built using `MkDocs`.

```bash
# Serve documentation locally for preview (auto-reloads on changes)
mkdocs serve

# Build the static documentation site (output in the `site/` directory)
mkdocs build
``` 