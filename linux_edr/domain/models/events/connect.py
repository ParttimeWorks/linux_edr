from pydantic import Field
from .base import BaseSyscallEvent

class ConnectEvent(BaseSyscallEvent):
    """connect syscall event."""

    fd: int = Field(..., ge=0, description="Socket file descriptor")
    address: str = Field(..., description="Destination address (ip:port or path)")

    def __str__(self) -> str:  # pragma: no cover
        return f"{super().__str__()} connect -> fd={self.fd} addr={self.address}" 