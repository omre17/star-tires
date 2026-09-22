"""Attendance calculations shared by reports and the AI context. All times UTC."""
from datetime import datetime, timedelta, timezone


def calculate_hours(events, start=None, end=None):
    opened = None
    seconds = 0.0
    for event in events:
        timestamp = datetime.fromisoformat(event['timestamp'])
        if timestamp.tzinfo is not None:
            timestamp = timestamp.astimezone(timezone.utc).replace(tzinfo=None)
        if event['action'] == 'start' and opened is None:
            opened = timestamp
        elif event['action'] == 'end' and opened is not None:
            left = max(opened, start) if start else opened
            right = min(timestamp, end) if end else timestamp
            seconds += max(0, (right - left).total_seconds())
            opened = None
    # Open shifts are intentionally excluded from payroll until clock-out.
    return seconds / 3600


def weekly_hours(events, now=None):
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    if now.tzinfo:
        now = now.astimezone(timezone.utc).replace(tzinfo=None)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    sunday = midnight - timedelta(days=(now.weekday() + 1) % 7)
    return calculate_hours(events, sunday, now)
