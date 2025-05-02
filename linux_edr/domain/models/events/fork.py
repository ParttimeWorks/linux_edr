from pydantic import Field
from .base import BaseSyscallEvent

class ForkEvent(BaseSyscallEvent):
    """fork syscall event."""

    child_pid: int = Field(..., ge=0, description="Child process PID created by fork")

    def __str__(self) -> str:  # pragma: no cover
        return f"{super().__str__()} fork -> child_pid={self.child_pid}" 