"""RSS and Atom parsing."""

from __future__ import annotations

from shipwatch.dates import parse_datetime
from shipwatch.models import RawItem, SourceSpec
from shipwatch.textutil import collapse_ws

try:
    import feedparser
except ImportError:  # pragma: no cover
    feedparser = None  # type: ignore[assignment]


def parse_rss(body: bytes, source: SourceSpec, *, limit: int = 40) -> list[RawItem]:
    if feedparser is None:  # pragma: no cover
        raise RuntimeError("feedparser is required to parse RSS/Atom feeds")
    parsed = feedparser.parse(body)
    items: list[RawItem] = []
    for entry in parsed.entries[:limit]:
        link = _entry_link(entry)
        title = collapse_ws(getattr(entry, "title", "") or link or "untitled")
        summary = collapse_ws(_html_to_text(getattr(entry, "summary", "") or ""))
        content = _entry_content(entry) or summary
        published = (
            parse_datetime(getattr(entry, "published", None))
            or parse_datetime(getattr(entry, "updated", None))
            or _struct_time(getattr(entry, "published_parsed", None))
            or _struct_time(getattr(entry, "updated_parsed", None))
        )
        if not link:
            continue
        items.append(
            RawItem(
                source_id=source.id,
                source_name=source.name,
                url=link,
                title=title,
                published_at=published,
                content=content,
                summary=summary,
                tags=list(source.tags),
            )
        )
    return items


def _entry_link(entry: object) -> str:
    link = getattr(entry, "link", "") or ""
    if link:
        return str(link)
    links = getattr(entry, "links", None) or []
    for item in links:
        href = item.get("href") if isinstance(item, dict) else getattr(item, "href", "")
        if href:
            return str(href)
    return ""


def _entry_content(entry: object) -> str:
    contents = getattr(entry, "content", None) or []
    parts: list[str] = []
    for item in contents:
        value = item.get("value") if isinstance(item, dict) else getattr(item, "value", "")
        if value:
            parts.append(_html_to_text(str(value)))
    return collapse_ws("\n".join(parts))


def _html_to_text(value: str) -> str:
    if "<" not in value:
        return value
    from bs4 import BeautifulSoup

    return BeautifulSoup(value, "lxml").get_text(" ", strip=True)


def _struct_time(value: object):
    if not value:
        return None
    from datetime import datetime, timezone

    try:
        return datetime(*value[:6], tzinfo=timezone.utc)  # type: ignore[index]
    except (TypeError, ValueError):
        return None
