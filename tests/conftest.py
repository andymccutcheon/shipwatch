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
                id="openai-news",
                name="OpenAI News",
                kind=SourceKind.RSS,
                url="https://openai.example/news/rss.xml",
                tags=["openai"],
            ),
            SourceSpec(
                id="anthropic-news",
                name="Anthropic News",
                kind=SourceKind.HTML,
                url="https://anthropic.example/news",
                tags=["anthropic"],
            ),
            SourceSpec(
                id="langchain",
                name="LangChain",
                kind=SourceKind.GITHUB,
                repo="langchain-ai/langchain",
                tags=["langchain"],
            ),
            SourceSpec(
                id="gemini-docs",
                name="Gemini docs",
                kind=SourceKind.SITEMAP,
                url="https://ai.example/sitemap.xml",
                tags=["google", "docs"],
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
    source_id: str = "openai",
    source_name: str = "OpenAI",
    url: str = "https://openai.example/price-cut",
    title: str = "OpenAI cuts API prices for GPT-5 mini",
    content: str = "OpenAI announced a 50% price reduction for GPT-5 mini input tokens in the API.",
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
