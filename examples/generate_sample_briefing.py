"""Regenerate examples/briefing.* from fictional fixtures (no network, --no-llm)."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "examples",
        help="Directory for briefing.md / .json / .xml / index.html",
    )
    args = parser.parse_args(argv)
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from tests.fictional_pipeline import SAMPLE_NOTE, run_fictional_pipeline

    data_dir = args.out / ".sample-data"
    if data_dir.exists():
        shutil.rmtree(data_dir)
    briefing, _items = run_fictional_pipeline(data_dir, args.out, sample_note=True, html=True)
    print(SAMPLE_NOTE)
    print(briefing.title)
    print(
        f"{briefing.coverage.total_claims} claims · "
        f"{briefing.coverage.supported} supported · "
        f"{briefing.coverage.flagged} flagged · "
        f"{briefing.coverage.dropped} dropped"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
