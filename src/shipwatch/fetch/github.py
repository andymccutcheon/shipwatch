"""GitHub Releases API parser."""

from __future__ import annotations

import json

from shipwatch.dates import parse_datetime
from shipwatch.models import RawItem, SourceSpec
from shipwatch.textutil import collapse_ws


def parse_github_releases(body: bytes, source: SourceSpec, *, limit: int = 40) -> list[RawItem]:
    payload = json.loads(body.decode("utf-8"))
    if isinstance(payload, dict) and "message" in payload:
        raise ValueError(f"GitHub API error for {source.repo}: {payload.get('message')}")
    if not isinstance(payload, list):
        raise ValueError(f"unexpected GitHub releases payload for {source.repo}")
    items: list[RawItem] = []
    for row in payload:
        if not isinstance(row, dict) or row.get("draft"):
            continue
        url = str(row.get("html_url") or "")
        title = collapse_ws(str(row.get("name") or row.get("tag_name") or url))
        body_text = collapse_ws(str(row.get("body") or ""))
        published = parse_datetime(row.get("published_at") or row.get("created_at"))
        if not url or not title:
            continue
        items.append(
            RawItem(
                source_id=source.id,
                source_name=source.name,
                url=url,
                title=title,
                published_at=published,
                content=body_text,
                summary=body_text[:400],
                tags=list(source.tags),
            )
        )
        if len(items) >= limit:
            break
    return items
