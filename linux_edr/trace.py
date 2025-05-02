import os
import selectors
import fcntl
import errno
import logging
import time
import re
import mmap
from typing import Generator, Optional, Union, Tuple, List

# Default path to the kernel's trace_pipe
TRACE_PATH = "/sys/kernel/tracing/trace_pipe"
# Maximum time to wait when reading (in seconds)
DEFAULT_TIMEOUT = 1.0

logger = logging.getLogger(__name__)

# Pre-compiled regexes for supported syscalls
EXECVE_PATTERN = re.compile(r"(\S+)\s+\[(\d+)\]\s+.*execve.*\((.*?)\)")
FORK_PATTERN = re.compile(r"(\S+)\s+\[(\d+)\]\s+.*fork.*child_pid=(\d+)")
CLONE_PATTERN = re.compile(r"(\S+)\s+\[(\d+)\]\s+.*clone.*child_pid=(\d+)\s+flags=(\S+)")
CONNECT_PATTERN = re.compile(r"(\S+)\s+\[(\d+)\]\s+.*connect.*fd=(\d+)\s+addr=(.+)")

from .domain.models.events import (
    ExecveEvent, ForkEvent, CloneEvent, ConnectEvent, BaseSyscallEvent, UnparsedEvent
)

# ----------------------- Helpers to resolve execve pointers -----------------------

def _read_string_from_mem(pid: int, address: int, max_len: int = 4096) -> Optional[str]:
    """Attempt to read a NUL-terminated string from another process's memory.

    Requires sufficient privileges (typically root / CAP_SYS_PTRACE).

    Args:
        pid: Process ID whose memory to read.
        address: Address of the string.
        max_len: Maximum number of bytes to read.

    Returns:
        Decoded string if successful, otherwise None.
    """
    try:
        with open(f"/proc/{pid}/mem", "rb", buffering=0) as mem_fd:
            mem_fd.seek(address)
            data = mem_fd.read(max_len)

        if not data:
            return None

        nul_idx = data.find(b"\x00")
        if nul_idx != -1:
            data = data[:nul_idx]

        return data.decode("utf-8", errors="replace")
    except Exception:
        return None

def _resolve_execve_cmd(pid: int, filename_ptr: str) -> Tuple[str, List[str]]:
    """Resolve the filename and arguments for an execve trace when only pointers are present.

    Strategy:
        1. Attempt to read the filename string via /proc/<pid>/mem using the supplied pointer.
        2. Fallback to /proc/<pid>/cmdline which usually contains argv contents.

    Args:
        pid: The PID from the trace event.
        filename_ptr: Hex string pointer to filename (may include trailing comma).

    Returns:
        Tuple of (command, args list). Unknown values will be "<unknown>" or empty list.
    """
    # Clean pointer string and convert to int
    filename_ptr = filename_ptr.strip().rstrip(",")
    cmd: str = "<unknown>"
    args: List[str] = []

    try:
        address = int(filename_ptr, 16)
        if address:
            if (s := _read_string_from_mem(pid, address)):
                cmd = os.path.basename(s)
    except Exception:
        pass

    # If we still don't have a usable cmd, fallback to cmdline
    if cmd == "<unknown>":
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                data = f.read()
            if data:
                parts = data.split(b"\x00")
                if parts:
                    cmd = os.path.basename(parts[0].decode("utf-8", errors="replace"))
                    args = [p.decode("utf-8", errors="replace") for p in parts[1:] if p]
        except Exception:
            pass

    return cmd, args

class TraceReader:
    """
    Non-blocking reader for trace_pipe via selectors.

    This class provides an iterator interface to read from the kernel trace_pipe
    without blocking, using the selectors module for efficient I/O multiplexing.
    """

    def __init__(self, path: str = TRACE_PATH, read_timeout: float = DEFAULT_TIMEOUT):
        """
        Initialize the trace reader.

        Args:
            path: Path to the trace_pipe file
            read_timeout: Maximum time to wait for data in seconds (None means wait forever)
        """
        self.path = path
        self.sel = selectors.DefaultSelector()
        self.fd: Optional[int] = None
        self.read_timeout = read_timeout
        self._setup_fd()

    def _setup_fd(self) -> None:
        """Set up the file descriptor for non-blocking reads."""
        try:
            if not os.path.exists(self.path):
                logger.warning(
                    f"Trace path {self.path} does not exist. Will attempt to open anyway."
                )

            # Open the file in non-blocking mode
            self.fd = os.open(self.path, os.O_RDONLY | os.O_NONBLOCK)

            # Register the file descriptor with the selector
            self._register_fd()

            logger.debug(f"Successfully opened trace pipe at {self.path}")
        except PermissionError as e:
            logger.warning(
                f"Permission denied opening {self.path}. Run with sudo or correct permissions."
            )
            raise
        except (FileNotFoundError, OSError) as e:
            # Treat ENOENT (No such file or directory) similarly to FileNotFoundError to allow retry logic
            if isinstance(e, OSError) and getattr(e, "errno", None) != errno.ENOENT:
                # Re-raise any other OSError that is not ENOENT so the generic block handles it
                raise
            # Handle case where the trace pipe is not yet available. Retry a few times
            max_retries = 3
            for attempt in range(1, max_retries + 1):
                logger.warning(
                    f"Trace pipe not found at {self.path} (attempt {attempt}/{max_retries}). Retrying shortly..."
                )
                time.sleep(1)
                try:
                    self.fd = os.open(self.path, os.O_RDONLY | os.O_NONBLOCK)
                    self._register_fd()
                    logger.debug(
                        f"Successfully opened trace pipe at {self.path} on retry {attempt}"
                    )
                    break
                except FileNotFoundError:
                    if attempt == max_retries:
                        logger.error(f"Trace pipe still not available after {max_retries} attempts")
                        raise
                    # Otherwise loop and retry
            else:
                # If we exited loop without break, re-raise original error
                raise e
        except Exception as e:
            logger.debug(f"Failed to open trace pipe at {self.path}: {e}")
            raise

    def _register_fd(self) -> None:
        """Register the file descriptor for read events."""
        if self.fd is None:
            return
            
        self.sel.register(self.fd, selectors.EVENT_READ)

    def _reopen_if_needed(self) -> bool:
        """
        Reopen the file descriptor if it's closed or invalid.

        Returns:
            True if reopened successfully, False otherwise
        """
        if self.fd is None or not os.path.exists(self.path):
            try:
                logger.info(f"Attempting to (re)open trace pipe at {self.path}")
                if self.fd is not None:
                    # Clean up existing resources
                    try:
                        self.sel.unregister(self.fd)
                        os.close(self.fd)
                    except Exception as e:
                        logger.warning(f"Error cleaning up old file descriptor: {e}")

                # Wait briefly before reopening
                time.sleep(1)
                self._setup_fd()
                return True
            except Exception as e:
                logger.error(f"Failed to reopen trace pipe: {e}")
                return False
        return True

    def _parse_line(self, line: str) -> Optional[BaseSyscallEvent]:
        """Attempt to parse a supported syscall line into a Pydantic model."""
        # execve
        if m := EXECVE_PATTERN.search(line):
            ts, pid_str, cmd_args = m.groups()
            pid = int(pid_str)
            parts = cmd_args.split() if cmd_args else []
            if not parts:
                return None

            # Typical trace contents: "filename: 7ffcb..., argv: 7ff..., envp: ..."
            if parts[0].startswith("filename:"):
                # Extract pointer after "filename:" which is at index 1
                filename_ptr = parts[1] if len(parts) > 1 else "0"
                command, argv = _resolve_execve_cmd(pid, filename_ptr)
                return ExecveEvent(timestamp=ts, pid=pid, command=command, args=argv)

            # Fallback: treat the first token as command as before
            return ExecveEvent(timestamp=ts, pid=pid, command=parts[0].strip('"'), args=parts[1:])

        # fork
        if m := FORK_PATTERN.search(line):
            ts, pid_str, child_pid_str = m.groups()
            return ForkEvent(timestamp=ts, pid=int(pid_str), child_pid=int(child_pid_str))

        # clone
        if m := CLONE_PATTERN.search(line):
            ts, pid_str, child_pid_str, flags = m.groups()
            return CloneEvent(timestamp=ts, pid=int(pid_str), child_pid=int(child_pid_str), flags=flags)

        # connect
        if m := CONNECT_PATTERN.search(line):
            ts, pid_str, fd_str, addr = m.groups()
            return ConnectEvent(timestamp=ts, pid=int(pid_str), fd=int(fd_str), address=addr)

        return None

    def __iter__(self) -> Generator[Union[BaseSyscallEvent, UnparsedEvent], None, None]:
        """
        Iterate over events from the trace pipe.

        Attempts to parse known syscall events into Pydantic models.
        If a line cannot be parsed, it yields an `UnparsedEvent` model containing the raw line.

        Yields:
            A `BaseSyscallEvent` subclass if parsed successfully, otherwise an `UnparsedEvent`.
        """
        if self.fd is None:
            logger.error("Cannot iterate: file descriptor is not open")
            return

        try:
            while True:
                # Ensure file still exists; if not, attempt reopen.
                if self.fd is None or not os.path.exists(self.path):
                    if not self._reopen_if_needed():
                        logger.warning("Trace file unavailable, will retry in 5 seconds")
                        time.sleep(5)
                        continue

                try:
                    # Wait for read events with timeout
                    events = self.sel.select(timeout=self.read_timeout)

                    if not events:
                        # No events within timeout, just continue
                        continue

                    for key, _ in events:
                        try:
                            data = os.read(key.fd, 4096)
                            if not data:  # EOF
                                logger.warning("Received EOF on trace pipe, will reopen")
                                self._reopen_if_needed()
                                # Return from iterator to avoid infinite loop
                                return

                            # Decode safely with error handling
                            try:
                                text = data.decode("utf-8", errors="replace")
                            except UnicodeDecodeError as e:
                                logger.warning(
                                    f"Unicode decode error: {e}, using replacement chars"
                                )
                                text = data.decode("utf-8", errors="replace")

                            for line in text.splitlines():
                                if not line.strip():
                                    continue

                                parsed_evt = self._parse_line(line)
                                # Yield the parsed object if recognized, else yield an UnparsedEvent
                                if parsed_evt:
                                    yield parsed_evt
                                else:
                                    # Optionally log the unparsed line here if needed
                                    # logger.debug(f"Unparsed trace line: {line}")
                                    yield UnparsedEvent(raw_line=line)
                        except OSError as e:
                            if e.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
                                continue
                            elif e.errno == errno.EBADF:
                                # Bad file descriptor, try to reopen
                                logger.warning("Bad file descriptor, reopening trace pipe")
                                self._reopen_if_needed()
                                break
                            else:
                                # Other OS errors – log once and exit iterator to avoid tight error loops
                                logger.error(f"OS Error reading from trace pipe: {e}")
                                self._reopen_if_needed()
                                return
                except Exception as e:
                    # Any unexpected error – log, pause briefly to avoid tight error loops, then retry
                    logger.error(f"Unexpected error in trace reader: {e}")
                    time.sleep(1)
                    continue
        except KeyboardInterrupt:
            logger.info("Trace reader interrupted")
        finally:
            self.close()

    def close(self) -> None:
        """Close the trace reader and free resources."""
        if self.fd is not None:
            try:
                self.sel.unregister(self.fd)
                os.close(self.fd)
                logger.debug("Trace reader closed")
            except Exception as e:
                logger.warning(f"Error closing trace reader: {e}")
            finally:
                self.fd = None

    def __del__(self) -> None:
        """Ensure resources are freed when object is garbage collected."""
        try:
            self.close()
        except Exception:
            # Suppress any exceptions during garbage collection
            pass
