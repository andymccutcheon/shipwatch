from __future__ import annotations

from pathlib import Path

from shipwatch.config import (
    bundled_sources_path,
    load_config,
    load_yaml,
    parse_sources,
    write_init_files,
)
from shipwatch.models import SourceKind
from tests.conftest import NOW, make_item


def test_store_roundtrip(store) -> None:
    item = make_item()
    assert store.upsert_item(item, fetched_at=NOW) is True
    assert store.upsert_item(item, fetched_at=NOW) is False
    loaded = store.get_item(item.id)
    assert loaded is not None
    assert loaded.title == item.title
    store.set_fetch_state(item.source_id, etag="abc", last_status=200, last_fetch=NOW)
    state = store.get_fetch_state(item.source_id)
    assert state["etag"] == "abc"
    store.mark_seen("docs", ["https://example.com/a"], first_seen=NOW)
    assert "https://example.com/a" in store.seen_urls("docs")


def test_init_and_bundled_sources(tmp_path: Path) -> None:
    written = write_init_files(tmp_path)
    assert {p.name for p in written} == {"shipwatch.yaml", "sources.yaml"}
    cfg = load_config(tmp_path / "shipwatch.yaml")
    assert len(cfg.sources) >= 20
    kinds = {s.kind for s in cfg.sources}
    assert {SourceKind.RSS, SourceKind.HTML, SourceKind.GITHUB, SourceKind.SITEMAP} <= kinds
    pack = parse_sources(load_yaml(bundled_sources_path()))
    assert any(s.id == "openai-news" for s in pack)


def test_load_config_missing_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    cfg = load_config(None)
    assert cfg.sources
    assert cfg.llm.model
