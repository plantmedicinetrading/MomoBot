from datetime import datetime, timezone

def get_minute_bucket(timestamp: str) -> str:
    """
    Round the timestamp down to the nearest minute.
    Example input: "2025-07-21T14:32:45.123456Z"
    Returns: "2025-07-21T14:32:00Z"
    """
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        bucket = dt.replace(second=0, microsecond=0).astimezone(timezone.utc)
        return bucket.isoformat().replace("+00:00", "Z")
    except Exception as e:
        print(f"[TimeTools] Failed to parse timestamp: {timestamp} — {e}")
        return timestamp