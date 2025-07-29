"""
Timezone utilities for consistent Eastern Time handling throughout the system.
All trade-related times should be in Eastern Time regardless of server location.
"""

import pytz
from datetime import datetime
from typing import Union

# Eastern Timezone
EASTERN_TZ = pytz.timezone('US/Eastern')

def get_eastern_time() -> datetime:
    """Get current time in Eastern Time"""
    return datetime.now(EASTERN_TZ)

def to_eastern_time(dt: Union[datetime, str]) -> datetime:
    """Convert any datetime to Eastern Time"""
    if isinstance(dt, str):
        # Parse ISO string
        dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
    
    if dt.tzinfo is None:
        # Assume UTC if no timezone info
        dt = pytz.UTC.localize(dt)
    
    return dt.astimezone(EASTERN_TZ)

def to_eastern_iso(dt: Union[datetime, str] = None) -> str:
    """Convert datetime to Eastern Time ISO string"""
    if dt is None:
        dt = get_eastern_time()
    else:
        dt = to_eastern_time(dt)
    
    return dt.isoformat()

def from_eastern_iso(iso_string: str) -> datetime:
    """Parse ISO string as Eastern Time"""
    dt = datetime.fromisoformat(iso_string)
    if dt.tzinfo is None:
        # If no timezone info, assume it's already Eastern Time
        return EASTERN_TZ.localize(dt)
    return dt.astimezone(EASTERN_TZ)

def eastern_to_unix_timestamp(dt: Union[datetime, str]) -> int:
    """Convert Eastern Time to Unix timestamp (seconds)"""
    if isinstance(dt, str):
        dt = from_eastern_iso(dt)
    return int(dt.timestamp())

def unix_to_eastern_time(unix_timestamp: int) -> datetime:
    """Convert Unix timestamp to Eastern Time"""
    dt = datetime.fromtimestamp(unix_timestamp, EASTERN_TZ)
    return dt

def format_eastern_time(dt: Union[datetime, str], format_str: str = None) -> str:
    """Format Eastern Time for display"""
    if isinstance(dt, str):
        dt = from_eastern_iso(dt)
    
    if format_str:
        return dt.strftime(format_str)
    else:
        return dt.strftime('%m/%d/%Y, %I:%M:%S %p') 