from pydantic import BaseModel

class UnparsedEvent(BaseModel):
    """Represents a raw line from the trace pipe that could not be parsed."""
    raw_line: str 