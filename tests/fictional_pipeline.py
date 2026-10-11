"""Run the --no-llm pipeline against invented-company fixtures."""

from __future__ import annotations

from pathlib import Path

from shipwatch.config import AppConfig, BriefSettings, FetchSettings, LLMSettings, ScoringSettings
from shipwatch.fetch.client import PoliteClient
from shipwatch.models import Briefing, Item, SourceKind, SourceSpec
from shipwatch.output.render import write_outputs
from shipwatch.pipeline.run import run_pipeline
from shipwatch.storage import Store
from tests.conftest import NOW, fixture_bytes, map_transport

SAMPLE_NOTE = (
    "Sample briefing generated from fictional fixtures; companies and products are invented."
)

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def fictional_sources() -> list[SourceSpec]:
    return [
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
        SourceSpec(
            id="mirror",
            name="Mirror",
            kind=SourceKind.RSS,
            url="https://mirror.example/rss.xml",
            tags=["mirror"],
        ),
    ]


def fictional_mapping() -> dict[str, tuple[int, bytes, dict[str, str]]]:
    return {
        "https://acme.example/news/rss.xml": (
            200,
            fixture_bytes("rss_acme.xml"),
            {"etag": "oa-1", "content-type": "application/rss+xml"},
        ),
        "https://contoso.example/news": (
            200,
            fixture_bytes("html_contoso.html"),
            {"etag": "an-1", "content-type": "text/html"},
        ),
        "https://api.github.com/repos/example/northwind/releases?per_page=30": (
            200,
            fixture_bytes("github_releases.json"),
            {"etag": "gh-1", "content-type": "application/json"},
        ),
        "https://docs.fabrikam.example/sitemap.xml": (
            200,
            fixture_bytes("sitemap.xml"),
            {"etag": "sm-1", "content-type": "application/xml"},
        ),
        "https://mirror.example/rss.xml": (
            200,
            fixture_bytes("rss_mirror.xml"),
            {"etag": "mi-1"},
        ),
    }


def fictional_config(data_dir: Path, output_dir: Path) -> AppConfig:
    return AppConfig(
        data_dir=data_dir,
        sources=fictional_sources(),
        llm=LLMSettings(base_url="https://llm.example/v1", model="test"),
        scoring=ScoringSettings(),
        brief=BriefSettings(top_n=8, since="14d", output_dir=output_dir),
        fetch=FetchSettings(respect_robots=False, min_interval_seconds=0),
    )


def run_fictional_pipeline(
    data_dir: Path,
    output_dir: Path,
    *,
    sample_note: bool = False,
    html: bool = True,
    top_n: int = 8,
) -> tuple[Briefing, list[Item]]:
    cfg = fictional_config(data_dir, output_dir)
    cfg.brief.top_n = top_n
    store = Store(data_dir / "shipwatch.db")
    client = PoliteClient(
        cfg.fetch, store, transport=map_transport(fictional_mapping()), sleep=lambda _s: None
    )
    briefing, items, _stats = run_pipeline(
        cfg,
        store,
        since="14d",
        top_n=top_n,
        no_llm=True,
        client=client,
        html=html,
        now=NOW,
    )
    if sample_note and SAMPLE_NOTE not in briefing.notes:
        briefing.notes.insert(0, SAMPLE_NOTE)
        write_outputs(
            briefing,
            items,
            output_dir,
            html=html,
            archive=store.list_briefings(limit=20),
        )
    return briefing, items
