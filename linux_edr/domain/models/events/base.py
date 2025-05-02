from pydantic import BaseModel, Field, field_validator
from datetime import datetime

class BaseSyscallEvent(BaseModel):
    """Common attributes for all syscall events."""

    timestamp: str = Field(..., description="Kernel timestamp (can be converted to datetime later)")
    pid: int = Field(..., ge=0, description="Process ID that triggered the syscall")

    # --- validators -------------------------------------------------------
    @field_validator("timestamp")
    @classmethod
    def _validate_iso_or_numeric(cls, v: str) -> str:  # pragma: no cover
        """Accepts isoformat or numeric timestamps but ensures non-empty."""
        if not v:
            raise ValueError("timestamp cannot be empty")
        return v

    @field_validator("pid")
    @classmethod
    def _validate_pid(cls, v: int) -> int:  # pragma: no cover
        if v < 0:
            raise ValueError("pid must be non-negative")
        return v

    # --- helpers ----------------------------------------------------------
    def __str__(self) -> str:  # pragma: no cover – convenience only
        return f"[{self.timestamp}] pid={self.pid}" 