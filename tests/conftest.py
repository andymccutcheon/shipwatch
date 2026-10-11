from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from shipwatch.config import AppConfig, BriefSettings, FetchSettings, LLMSettings, ScoringSettings
from shipwatch.fetch.client import HttpResponse
from shipwatch.models import Item, ItemKind, SourceKind, SourceSpec
from shipwatch.storage import Store

FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def now() -> datetime:
    return NOW


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "shipwatch.db")


@pytest.fixture
def cfg(tmp_path: Path) -> AppConfig:
    return AppConfig(
        data_dir=tmp_path / "data",
        sources=[
            SourceSpec(
                id="acme-news",
                name="Acme AI News",
                kind=SourceKind.RSS,
                url="https://acme.example/news/rss.xml",
                tags=["acme"],
            ),
            SourceSpec(
                id="contoso-news",
                name="Contoso Models News",
                kind=SourceKind.HTML,
                url="https://contoso.example/news",
                tags=["contoso"],
            ),
            SourceSpec(
                id="northwind",
                name="Northwind Agents",
                kind=SourceKind.GITHUB,
                repo="example/northwind",
                tags=["northwind"],
            ),
            SourceSpec(
                id="fabrikam-docs",
                name="Fabrikam Docs",
                kind=SourceKind.SITEMAP,
                url="https://docs.fabrikam.example/sitemap.xml",
                tags=["fabrikam", "docs"],
            ),
        ],
        llm=LLMSettings(base_url="https://llm.example/v1", model="test"),
        scoring=ScoringSettings(),
        brief=BriefSettings(top_n=8, since="14d", output_dir=tmp_path / "out"),
        fetch=FetchSettings(respect_robots=False, min_interval_seconds=0),
    )


def fixture_bytes(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def map_transport(mapping: dict[str, tuple[int, bytes, dict[str, str]]]):
    def _transport(url: str, headers: dict[str, str]) -> HttpResponse:
        if url.endswith("/robots.txt"):
            return HttpResponse(
                200, url, b"User-agent: *\nAllow: /\n", {"content-type": "text/plain"}
            )
        if url not in mapping:
            return HttpResponse(404, url, b"missing", {})
        status, body, resp_headers = mapping[url]
        if (
            status == 200
            and headers.get("If-None-Match")
            and resp_headers.get("etag")
            and headers["If-None-Match"] == resp_headers["etag"]
        ):
            return HttpResponse(304, url, b"", resp_headers, not_modified=True)
        return HttpResponse(status, url, body, resp_headers)

    return _transport


def make_item(
    *,
    item_id: str = "item1",
    source_id: str = "acme",
    source_name: str = "Acme AI",
    url: str = "https://acme.example/price-cut",
    title: str = "Acme AI cuts API prices for Helio-7 mini",
    content: str = (
        "Acme AI announced a 50% price reduction for Helio-7 mini input tokens in the API."
    ),
    kind: ItemKind = ItemKind.PRICING_CHANGE,
    published_at: datetime | None = None,
) -> Item:
    return Item(
        id=item_id,
        source_id=source_id,
        source_name=source_name,
        url=url,
        title=title,
        published_at=published_at or NOW,
        content=content,
        summary=content,
        kind=kind,
    )
