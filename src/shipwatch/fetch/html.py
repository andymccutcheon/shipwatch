"""HTML changelog extraction: CSS selector, heading split, or readability."""

from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from shipwatch.dates import parse_datetime
from shipwatch.models import RawItem, SourceSpec
from shipwatch.textutil import collapse_ws, slug

_STRIP = ("script", "style", "nav", "footer", "header", "aside", "form", "noscript", "svg")


def parse_html(body: bytes, source: SourceSpec, url: str, *, limit: int = 40) -> list[RawItem]:
    soup = BeautifulSoup(body, "lxml")
    if source.selector:
        nodes = [n for n in soup.select(source.selector) if isinstance(n, Tag)]
        items = [_item_from_node(node, source, url) for node in nodes]
        items = [i for i in items if i and len(i.content) >= 20]
        if items:
            return items[:limit]
    articles = [n for n in soup.find_all("article") if isinstance(n, Tag)]
    if len(articles) >= 2:
        items = [_item_from_node(node, source, url) for node in articles]
        items = [i for i in items if i and len(i.content) >= 20]
        if len(items) >= 2:
            return items[:limit]
    heading_items = split_by_headings(soup, source, url)
    if len(heading_items) >= 2:
        return heading_items[:limit]
    text = readable_text(soup)
    title = _page_title(soup) or source.name
    if not text:
        return []
    return [
        RawItem(
            source_id=source.id,
            source_name=source.name,
            url=url,
            title=title,
            content=text,
            summary=text[:400],
            tags=list(source.tags),
        )
    ]


def _content_root(work: BeautifulSoup) -> Tag:
    articles = work.find_all("article")
    if len(articles) == 1:
        return articles[0]
    return work.find("main") or work.body or work


def readable_text(soup: BeautifulSoup) -> str:
    work = BeautifulSoup(str(soup), "lxml")
    for tag in work(_STRIP):
        tag.decompose()
    root = _content_root(work)
    blocks: list[str] = []
    for node in root.find_all(["p", "li", "h1", "h2", "h3", "h4"]):
        text = collapse_ws(node.get_text(" ", strip=True))
        if len(text) >= 25:
            blocks.append(text)
    if blocks:
        return "\n".join(blocks)
    return collapse_ws(root.get_text(" ", strip=True))


def split_by_headings(soup: BeautifulSoup, source: SourceSpec, url: str) -> list[RawItem]:
    work = BeautifulSoup(str(soup), "lxml")
    for tag in work(_STRIP):
        tag.decompose()
    root = _content_root(work)
    headings = [h for h in root.find_all(["h2", "h3"]) if collapse_ws(h.get_text(" ", strip=True))]
    items: list[RawItem] = []
    for heading in headings:
        title = collapse_ws(heading.get_text(" ", strip=True))
        if _skip_heading(title):
            continue
        chunks: list[str] = []
        link = _first_link(heading, url)
        published = None
        for sibling in heading.find_all_next():
            if sibling in headings:
                break
            if sibling.name in {"h2", "h3"}:
                break
            if sibling.name in {"time"} and sibling.get("datetime"):
                published = parse_datetime(sibling.get("datetime"))
            text = (
                collapse_ws(sibling.get_text(" ", strip=True))
                if sibling.name in {"p", "li"}
                else ""
            )
            if text:
                chunks.append(text)
            if sibling.name == "a" and sibling.get("href") and not link:
                link = urljoin(url, sibling.get("href"))
        content = "\n".join(chunks)
        if len(content) < 40:
            continue
        items.append(
            RawItem(
                source_id=source.id,
                source_name=source.name,
                url=link or _fragment_url(url, title),
                title=title,
                published_at=published,
                content=content,
                summary=content[:400],
                tags=list(source.tags),
            )
        )
    return items


def _item_from_node(node: Tag, source: SourceSpec, url: str) -> RawItem | None:
    title_node = node.find(["h1", "h2", "h3", "h4", "a"])
    title = collapse_ws(
        title_node.get_text(" ", strip=True) if title_node else node.get_text(" ", strip=True)
    )
    if not title:
        return None
    link = _entry_url(node, url, title)
    time_node = node.find("time")
    published = parse_datetime(time_node.get("datetime") if time_node else None)
    paragraphs = [
        collapse_ws(p.get_text(" ", strip=True))
        for p in node.find_all(["p", "li"])
        if collapse_ws(p.get_text(" ", strip=True))
    ]
    text = "\n".join(paragraphs) or collapse_ws(node.get_text(" ", strip=True))
    return RawItem(
        source_id=source.id,
        source_name=source.name,
        url=link,
        title=title[:240],
        published_at=published,
        content=text,
        summary=text[:400],
        tags=list(source.tags),
    )


def _fragment_url(base: str, title: str) -> str:
    return f"{base.rstrip('#')}#{slug(title)}"


def _entry_url(node: Tag, base: str, title: str) -> str:
    link = _first_link(node, base)
    if link and link.rstrip("/") != base.rstrip("/"):
        return link
    return _fragment_url(base, title)


def _first_link(node: Tag, base: str) -> str:
    anchor = node.find("a", href=True)
    if anchor and anchor.get("href"):
        return urljoin(base, str(anchor.get("href")))
    return ""


def _page_title(soup: BeautifulSoup) -> str:
    if soup.title and soup.title.string:
        return collapse_ws(soup.title.string)
    heading = soup.find(["h1", "h2"])
    return collapse_ws(heading.get_text(" ", strip=True)) if heading else ""


def _skip_heading(title: str) -> bool:
    lowered = title.lower()
    if lowered in {"contents", "on this page", "overview", "table of contents"}:
        return True
    return len(title) <= 3
