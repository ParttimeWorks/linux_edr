from pydantic import Field
from .base import BaseSyscallEvent

class CloneEvent(BaseSyscallEvent):
    """clone syscall event."""

    child_pid: int = Field(..., ge=0, description="PID of the cloned task")
    flags: str = Field(..., description="Clone flags")

    def __str__(self) -> str:  # pragma: no cover
        return f"{super().__str__()} clone -> child_pid={self.child_pid} flags={self.flags}" 