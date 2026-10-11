"""Date parsing and window helpers."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any

UTC = timezone.utc

_SINCE_RE = re.compile(r"^(\d+)\s*([dwh])$", re.IGNORECASE)


def now_utc() -> datetime:
    return datetime.now(tz=UTC)


def ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def parse_since(value: str, *, now: datetime | None = None) -> datetime:
    """Parse ``7d``, ``2w``, ``12h``, or an ISO-8601 timestamp into a UTC start."""
    stamp = now or now_utc()
    stamp = ensure_aware(stamp)
    raw = value.strip()
    match = _SINCE_RE.match(raw)
    if match:
        amount = int(match.group(1))
        unit = match.group(2).lower()
        delta = {
            "d": timedelta(days=amount),
            "w": timedelta(weeks=amount),
            "h": timedelta(hours=amount),
        }[unit]
        return stamp - delta
    parsed = parse_datetime(raw)
    if parsed is None:
        raise ValueError(f"unrecognized --since value: {value!r} (use 7d, 2w, 12h, or ISO-8601)")
    return parsed


def parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return ensure_aware(value)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=UTC)
    text = str(value).strip()
    if not text:
        return None
    try:
        return ensure_aware(parsedate_to_datetime(text))
    except (TypeError, ValueError, IndexError):
        pass
    cleaned = text.replace("Z", "+00:00")
    try:
        return ensure_aware(datetime.fromisoformat(cleaned))
    except ValueError:
        return None


def format_window(start: datetime, end: datetime) -> str:
    start = ensure_aware(start)
    end = ensure_aware(end)
    return f"{start.day} {start.strftime('%b %Y')} – {end.day} {end.strftime('%b %Y')}"


def isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
    return ensure_aware(value).isoformat()
