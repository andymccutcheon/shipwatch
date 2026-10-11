from __future__ import annotations

from shipwatch.fetch.github import parse_github_releases
from shipwatch.fetch.html import parse_html
from shipwatch.fetch.rss import parse_rss
from shipwatch.fetch.sitemap import parse_sitemap
from shipwatch.models import SourceKind, SourceSpec
from tests.conftest import fixture_bytes


def test_parse_rss_strips_tracking_and_reads_items() -> None:
    source = SourceSpec(id="acme-news", name="Acme AI News", kind=SourceKind.RSS, url="https://x")
    items = parse_rss(fixture_bytes("rss_acme.xml"), source)
    titles = {i.title for i in items}
    assert len(items) >= 3
    assert any(t.startswith("Acme AI cuts API prices") for t in titles)
    assert any("Helio-8" in t for t in titles)
    price = next(i for i in items if "price" in i.title.lower())
    assert "50% price reduction" in price.content
    assert price.published_at is not None


def test_parse_html_splits_articles() -> None:
    source = SourceSpec(
        id="contoso-news",
        name="Contoso Models News",
        kind=SourceKind.HTML,
        url="https://contoso.example/news",
        selector="article",
    )
    items = parse_html(fixture_bytes("html_contoso.html"), source, source.url or "")
    titles = [i.title.lower() for i in items]
    assert len(items) >= 4
    assert any("computer use" in t for t in titles)
    assert any("ships 3" in t or "ships 3×" in t or "ships 3x" in t for t in titles)
    assert any("deprecate" in i.content.lower() for i in items)


def test_parse_html_heading_fallback() -> None:
    source = SourceSpec(
        id="contoso-news", name="Contoso Models News", kind=SourceKind.HTML, url="https://x"
    )
    items = parse_html(fixture_bytes("html_contoso.html"), source, "https://contoso.example/news")
    assert len(items) >= 2


def test_parse_github_skips_drafts() -> None:
    source = SourceSpec(
        id="northwind", name="Northwind Agents", kind=SourceKind.GITHUB, repo="example/northwind"
    )
    items = parse_github_releases(fixture_bytes("github_releases.json"), source)
    titles = {i.title for i in items}
    assert "northwind 1.2.0" in titles
    assert "northwind 1.2.1" in titles
    assert "draft only" not in titles
    assert any("DeskRetrievalChain" in i.content for i in items)


def test_parse_sitemap_reports_new_pages() -> None:
    source = SourceSpec(
        id="docs",
        name="Fabrikam Docs",
        kind=SourceKind.SITEMAP,
        url="https://docs.fabrikam.example/sitemap.xml",
    )
    items, locs, children = parse_sitemap(fixture_bytes("sitemap.xml"), source, seen=set())
    assert children == []
    assert len(locs) == 2
    assert len(items) == 2
    again, _, _ = parse_sitemap(fixture_bytes("sitemap.xml"), source, seen=set(locs))
    assert again == []
