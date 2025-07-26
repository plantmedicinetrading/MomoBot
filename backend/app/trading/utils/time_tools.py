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

def get_10s_bucket(timestamp: str) -> str:
    """
    Round the timestamp down to the nearest 10-second interval.
    Example input: "2025-07-21T14:32:45.123456Z"
    Returns: "2025-07-21T14:32:40Z"
    """
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        bucket_second = (dt.second // 10) * 10
        bucket = dt.replace(second=bucket_second, microsecond=0).astimezone(timezone.utc)
        return bucket.isoformat().replace("+00:00", "Z")
    except Exception as e:
        print(f"[TimeTools] Failed to parse timestamp for 10s bucket: {timestamp} — {e}")
        return timestamp