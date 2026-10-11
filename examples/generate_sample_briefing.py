"""Write examples/briefing.md and briefing.json from recorded fixtures."""

from __future__ import annotations

from pathlib import Path

from shipwatch.config import AppConfig, BriefSettings, FetchSettings, ScoringSettings
from shipwatch.fetch.client import PoliteClient
from shipwatch.models import SourceKind, SourceSpec
from shipwatch.output.render import write_outputs
from shipwatch.pipeline.run import run_pipeline
from shipwatch.storage import Store
from tests.conftest import NOW, fixture_bytes, map_transport

OUT = Path(__file__).resolve().parent


def main() -> None:
    data_dir = OUT / ".sample-data"
    store = Store(data_dir / "shipwatch.db")
    cfg = AppConfig(
        data_dir=data_dir,
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
                selector="article",
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
                tags=["google"],
            ),
        ],
        scoring=ScoringSettings(),
        brief=BriefSettings(top_n=8, since="14d", output_dir=OUT, html=True),
        fetch=FetchSettings(respect_robots=False, min_interval_seconds=0),
    )
    mapping = {
        "https://openai.example/news/rss.xml": (200, fixture_bytes("rss_openai.xml"), {}),
        "https://anthropic.example/news": (200, fixture_bytes("html_anthropic.html"), {}),
        "https://api.github.com/repos/langchain-ai/langchain/releases?per_page=30": (
            200,
            fixture_bytes("github_releases.json"),
            {},
        ),
        "https://ai.example/sitemap.xml": (200, fixture_bytes("sitemap.xml"), {}),
    }
    client = PoliteClient(cfg.fetch, store, transport=map_transport(mapping), sleep=lambda _s: None)
    briefing, items, _stats = run_pipeline(
        cfg, store, since="14d", no_llm=True, client=client, html=True, now=NOW
    )
    write_outputs(briefing, items, OUT, html=True, archive=[briefing])
    print(f"wrote {OUT / 'briefing.md'}")


if __name__ == "__main__":
    main()
