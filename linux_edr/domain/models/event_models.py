from pydantic import BaseModel, Field
from typing import List, Any

class ExecveEvent(BaseModel):
    """Validated execve syscall event."""

    timestamp: str = Field(..., description="Trace timestamp string as reported by ftrace")
    pid: int = Field(..., description="Process ID of the task that executed the syscall")
    command: str = Field(..., description="Executable invoked (basename)")
    args: List[str] = Field(default_factory=list, description="Arguments supplied to the executable")

    # Helper constructors ---------------------------------------------------
    @classmethod
    def from_namedtuple(cls, nt: Any) -> "ExecveEvent":
        """Build ExecveEvent from an ExecveEvent NamedTuple instance."""
        return cls(timestamp=nt.timestamp, pid=nt.pid, command=nt.command, args=list(nt.args))

    def __str__(self) -> str:  # pragma: no cover – convenience only
        """Human-readable representation useful in logs."""
        cmd_line = " ".join([self.command, *self.args])
        return f"[{self.timestamp}] pid={self.pid} cmd={cmd_line}" 