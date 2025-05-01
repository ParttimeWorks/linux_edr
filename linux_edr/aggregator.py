import threading
import logging
from collections import deque
from typing import Deque, Dict, Any, List, Optional
from time import monotonic

logger = logging.getLogger(__name__)

class Aggregator:
    """
    Thread-safe in-memory buffer for incoming events.
    
    Uses a fixed-size deque for back-pressure protection and provides
    methods to safely add events and retrieve snapshots of the buffer.
    """
    
    def __init__(self, maxlen: int = 10000, max_age_seconds: Optional[float] = None):
        """
        Initialize the aggregator.
        
        Args:
            maxlen: Maximum number of events to store in the buffer
            max_age_seconds: Maximum age of events to keep (None means no limit)
        """
        self.buffer: Deque[Dict[str, Any]] = deque(maxlen=maxlen)
        self.lock = threading.Lock()
        self.maxlen = maxlen
        self.max_age_seconds = max_age_seconds
        self.last_timestamp = monotonic()
        self.total_received = 0
        self.total_dropped = 0
        
        logger.debug(f"Initialized aggregator with buffer size {maxlen}")

    def add(self, event: Dict[str, Any]) -> bool:
        """
        Add an event to the buffer.
        
        Args:
            event: Event dictionary to add
            
        Returns:
            True if the event was added, False if it was dropped
        """
        if not event:
            logger.warning("Attempted to add empty event, skipping")
            return False
            
        try:
            with self.lock:
                # Add timestamp for age tracking if needed
                if self.max_age_seconds is not None and "_timestamp" not in event:
                    event["_timestamp"] = monotonic()
                    
                # Add the event
                self.buffer.append(event)
                self.total_received += 1
                
                # Check if buffer is getting full
                if len(self.buffer) >= self.maxlen * 0.9:
                    logger.warning(f"Event buffer is at {len(self.buffer)}/{self.maxlen} capacity")
                    
                return True
        except Exception as e:
            logger.error(f"Error adding event to buffer: {e}")
            self.total_dropped += 1
            return False

    def snapshot_and_clear(self) -> List[Dict[str, Any]]:
        """
        Take a snapshot of the current buffer and clear it.
        
        Returns:
            List of events in the buffer
        """
        with self.lock:
            # Remove old events if max_age is set
            if self.max_age_seconds is not None:
                now = monotonic()
                cutoff = now - self.max_age_seconds
                
                # Only process events with _timestamp
                while self.buffer and "_timestamp" in self.buffer[0] and self.buffer[0]["_timestamp"] < cutoff:
                    self.buffer.popleft()
            
            # Capture all events in the buffer
            events = list(self.buffer)
            
            # Clear internal timestamps before returning
            for event in events:
                event.pop("_timestamp", None)
                
            # Log statistics
            count = len(events)
            logger.debug(f"Taking snapshot of {count} events (received: {self.total_received}, dropped: {self.total_dropped})")
            
            # Clear the buffer
            self.buffer.clear()
            
        return events
        
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the aggregator.
        
        Returns:
            Dictionary with statistics
        """
        with self.lock:
            return {
                "buffer_size": len(self.buffer),
                "buffer_capacity": self.maxlen,
                "total_received": self.total_received,
                "total_dropped": self.total_dropped,
                "buffer_usage_percent": (len(self.buffer) / self.maxlen) * 100 if self.maxlen > 0 else 0
            } 