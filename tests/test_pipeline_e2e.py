from __future__ import annotations

from pathlib import Path

from shipwatch.fetch.client import PoliteClient
from shipwatch.models import ItemKind
from shipwatch.output.render import render_html, render_json, render_markdown, render_rss
from shipwatch.pipeline.run import run_pipeline
from shipwatch.storage import Store
from tests.conftest import NOW, map_transport
from tests.fictional_pipeline import (
    EXAMPLES,
    SAMPLE_NOTE,
    fictional_config,
    fictional_mapping,
    run_fictional_pipeline,
)


def test_full_pipeline_from_fixtures(tmp_path: Path) -> None:
    briefing, items = run_fictional_pipeline(tmp_path / "data", tmp_path / "out")
    story = next(i for i in items if "ships" in i.title.lower() and "northwind" in i.title.lower())
    price = next(i for i in items if "price" in i.title.lower())
    assert story.kind is ItemKind.NON_SHIPMENT
    assert price.kind is ItemKind.PRICING_CHANGE
    assert price.score > story.score
    assert briefing.coverage.total_claims >= 1
    assert briefing.coverage.supported + briefing.coverage.flagged == len(briefing.kept_claims())
    assert all(claim.source_item_ids for claim in briefing.kept_claims())
    md = render_markdown(briefing, items)
    assert "Grounding:" in md
    assert "](http" in md
    assert "Two-person team closed" not in md
    js = render_json(briefing, items)
    assert '"coverage_ratio"' in js
    html = render_html(briefing, items)
    assert "<html" in html
    rss = render_rss([briefing], items)
    assert "<rss" in rss
    assert (tmp_path / "out" / "briefing.md").exists()
    assert (tmp_path / "out" / "index.html").exists()

    cfg = fictional_config(tmp_path / "data", tmp_path / "out")
    store = Store(tmp_path / "data" / "shipwatch.db")
    client = PoliteClient(
        cfg.fetch, store, transport=map_transport(fictional_mapping()), sleep=lambda _s: None
    )
    stats2 = run_pipeline(cfg, store, since="14d", no_llm=True, client=client, html=False, now=NOW)[
        2
    ]
    statuses = {o.source_id: o.status for o in stats2.outcomes}
    assert statuses["acme-news"] == "not_modified"


def test_sample_briefing_is_fictional_pipeline_output(tmp_path: Path) -> None:
    briefing, items = run_fictional_pipeline(
        tmp_path / "data", tmp_path / "out", sample_note=True, html=True
    )
    generated = (tmp_path / "out" / "briefing.md").read_text(encoding="utf-8")
    committed = (EXAMPLES / "briefing.md").read_text(encoding="utf-8")
    assert generated == committed
    assert SAMPLE_NOTE in generated
    assert SAMPLE_NOTE in briefing.notes
    blob = generated.lower()
    for leak in (
        "vercel",
        "openai",
        "anthropic",
        "rillet",
        "pinecone",
        "cloudflare",
        "github copilot",
        "claude",
        "gemini",
        "langchain",
    ):
        assert leak not in blob
    for item in items:
        host = item.url.split("/")[2]
        assert host.endswith(".example") or host == "github.com"
        if host == "github.com":
            assert "/example/" in item.url
    claims = [c.text for c in briefing.kept_claims()]
    assert claims
    assert all(len(text) <= 220 for text in claims)
    assert not any("Tripled shipping rate" in text and "Two-person" in text for text in claims)


def test_run_pipeline_accepts_now_kw() -> None:
    import inspect

    from shipwatch.pipeline.run import run_brief

    assert "now" in inspect.signature(run_brief).parameters
    assert Path(__file__).exists()
