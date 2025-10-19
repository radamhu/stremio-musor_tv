"""Time window computation for filtering live content."""
from datetime import datetime, timedelta
from typing import Optional, Literal


TimePreset = Literal["now", "next2h", "tonight"]


class TimeWindow:
    """Represents a time window with start and end."""
    def __init__(self, start: datetime, end: datetime):
        self.start = start
        self.end = end


def compute_window(preset: Optional[TimePreset] = None, now: Optional[datetime] = None) -> TimeWindow:
    """Compute time window based on preset."""
    if now is None:
        now = datetime.now()
    
    tz_now = now  # Assume process TZ=Europe/Budapest
    start = tz_now
    end = tz_now
    
    preset = preset or "now"
    
    if preset == "now":
        end = start + timedelta(minutes=90)
    elif preset == "next2h":
        end = start + timedelta(hours=2)
    elif preset == "tonight":
        tonight_start = tz_now.replace(hour=18, minute=0, second=0, microsecond=0)
        tonight_end = tz_now.replace(hour=23, minute=59, second=59, microsecond=999999)
        return TimeWindow(tonight_start, tonight_end)
    
    return TimeWindow(start, end)


def within_window(start_iso: str, window: TimeWindow) -> bool:
    """Check if a time is within the given window."""
    t = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
    return window.start <= t <= window.end
