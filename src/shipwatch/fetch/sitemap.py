"""Docs sitemap parser for new-page detection."""

from __future__ import annotations

from xml.etree import ElementTree as ET

from shipwatch.dates import parse_datetime
from shipwatch.models import RawItem, SourceSpec
from shipwatch.textutil import collapse_ws

_NS = {
    "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
}


def parse_sitemap(
    body: bytes,
    source: SourceSpec,
    *,
    seen: set[str] | None = None,
    limit: int = 40,
) -> tuple[list[RawItem], list[str], list[str]]:
    """Return (new items, all loc URLs, child sitemap URLs)."""
    root = ET.fromstring(body)
    tag = _local(root.tag)
    child_sitemaps: list[str] = []
    locs: list[tuple[str, str | None]] = []
    if tag == "sitemapindex":
        for node in _findall(root, "sitemap"):
            loc = _child_text(node, "loc")
            if loc:
                child_sitemaps.append(loc)
    elif tag == "urlset":
        for node in _findall(root, "url"):
            loc = _child_text(node, "loc")
            lastmod = _child_text(node, "lastmod")
            if loc:
                locs.append((loc, lastmod))
    already = seen or set()
    items: list[RawItem] = []
    all_locs = [loc for loc, _lastmod in locs]
    for loc, lastmod in locs:
        if loc in already:
            continue
        title = _title_from_url(loc)
        items.append(
            RawItem(
                source_id=source.id,
                source_name=source.name,
                url=loc,
                title=f"New docs page: {title}",
                published_at=parse_datetime(lastmod),
                content=f"New page listed on the {source.name} sitemap: {loc}",
                summary=f"New page: {loc}",
                tags=list(source.tags) + ["docs", "new-page"],
            )
        )
        if len(items) >= limit:
            break
    return items, all_locs, child_sitemaps


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _findall(root: ET.Element, name: str) -> list[ET.Element]:
    found = list(root.findall(f"sm:{name}", _NS))
    if found:
        return found
    return [child for child in root if _local(child.tag) == name]


def _child_text(node: ET.Element, name: str) -> str:
    child = node.find(f"sm:{name}", _NS)
    if child is None:
        for item in node:
            if _local(item.tag) == name:
                child = item
                break
    return collapse_ws(child.text or "") if child is not None else ""


def _title_from_url(url: str) -> str:
    path = url.rstrip("/").rsplit("/", 1)[-1]
    return path.replace("-", " ").replace("_", " ") or url
