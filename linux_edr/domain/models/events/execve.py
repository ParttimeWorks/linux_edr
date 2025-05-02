from typing import List
from pydantic import Field

from .base import BaseSyscallEvent

class ExecveEvent(BaseSyscallEvent):
    """execve syscall event."""

    command: str = Field(..., description="Executable invoked (basename)")
    args: List[str] = Field(default_factory=list, description="Arguments supplied to the executable")

    def __str__(self) -> str:  # pragma: no cover
        cmd_line = " ".join([self.command, *self.args])
        return f"{super().__str__()} execve -> {cmd_line}" 