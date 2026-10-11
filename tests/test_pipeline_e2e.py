from __future__ import annotations

from pathlib import Path

from shipwatch.fetch.client import PoliteClient
from shipwatch.models import SourceKind, SourceSpec
from shipwatch.output.render import render_html, render_json, render_markdown, render_rss
from shipwatch.pipeline.run import run_pipeline
from tests.conftest import fixture_bytes, map_transport


def test_full_pipeline_from_fixtures(cfg, store, now) -> None:
    cfg.sources.append(
        SourceSpec(
            id="mirror",
            name="Mirror",
            kind=SourceKind.RSS,
            url="https://mirror.example/rss.xml",
            tags=["mirror"],
        )
    )
    mapping = {
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
    client = PoliteClient(cfg.fetch, store, transport=map_transport(mapping), sleep=lambda _s: None)
    briefing, items, stats = run_pipeline(
        cfg,
        store,
        since="14d",
        top_n=8,
        no_llm=True,
        client=client,
        html=True,
        now=now,
    )
    assert stats.fetched == 5
    assert stats.items_new >= 5
    assert briefing.coverage.total_claims >= 1
    assert briefing.coverage.supported + briefing.coverage.flagged == len(briefing.kept_claims())
    assert all(claim.source_item_ids for claim in briefing.kept_claims())
    md = render_markdown(briefing, items)
    assert "Grounding:" in md
    assert "](http" in md
    js = render_json(briefing, items)
    assert '"coverage_ratio"' in js
    html = render_html(briefing, items)
    assert "<html" in html
    rss = render_rss([briefing], items)
    assert "<rss" in rss
    assert (cfg.brief.output_dir / "briefing.md").exists()
    assert (cfg.brief.output_dir / "index.html").exists()

    # Conditional GET should 304 on the second fetch.
    stats2 = run_pipeline(cfg, store, since="14d", no_llm=True, client=client, html=False, now=now)[
        2
    ]
    statuses = {o.source_id: o.status for o in stats2.outcomes}
    assert statuses["acme-news"] == "not_modified"


def test_run_pipeline_accepts_now_kw() -> None:
    import inspect

    from shipwatch.pipeline.run import run_brief

    assert "now" in inspect.signature(run_brief).parameters
    assert Path(__file__).exists()
