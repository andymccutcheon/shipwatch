from __future__ import annotations

from pathlib import Path

from shipwatch.cli import main
from shipwatch.storage import Store
from tests.conftest import NOW, make_item


def test_version(capsys) -> None:
    try:
        main(["--version"])
    except SystemExit as exc:
        assert exc.code == 0
    assert "0.1.1" in capsys.readouterr().out


def test_init_sources_check_and_stats(tmp_path: Path, capsys) -> None:
    assert main(["init", "--dir", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "shipwatch.yaml" in out
    assert main(["--config", str(tmp_path / "shipwatch.yaml"), "sources", "check"]) == 0
    check = capsys.readouterr().out
    assert "openai-news" in check
    assert "valid" in check
    data_dir = tmp_path / "data"
    assert (
        main(["--config", str(tmp_path / "shipwatch.yaml"), "--data-dir", str(data_dir), "stats"])
        == 0
    )
    assert '"items"' in capsys.readouterr().out


def test_brief_from_seeded_store(tmp_path: Path, capsys) -> None:
    cfg_dir = tmp_path
    assert main(["init", "--dir", str(cfg_dir)]) == 0
    capsys.readouterr()
    db_dir = tmp_path / "archive"
    store = Store(db_dir / "shipwatch.db")
    store.upsert_item(make_item(), fetched_at=NOW)
    store.close()
    out_dir = tmp_path / "briefs"
    code = main(
        [
            "--config",
            str(cfg_dir / "shipwatch.yaml"),
            "--data-dir",
            str(db_dir),
            "--no-llm",
            "brief",
            "--since",
            "14d",
            "--out",
            str(out_dir),
            "--html",
        ]
    )
    assert code == 0
    assert (out_dir / "briefing.md").exists()
    assert (out_dir / "briefing.json").exists()
    assert (out_dir / "briefings.xml").exists()
    assert (out_dir / "index.html").exists()
    assert "Grounding" in (out_dir / "briefing.md").read_text(encoding="utf-8")
