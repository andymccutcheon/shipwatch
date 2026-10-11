"""Command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from shipwatch._version import __version__
from shipwatch.config import (
    AppConfig,
    bundled_sources_path,
    load_config,
    load_yaml,
    parse_sources,
    write_init_files,
)
from shipwatch.fetch.client import PoliteClient, check_url
from shipwatch.models import SourceKind
from shipwatch.output.render import coverage_line, write_outputs
from shipwatch.pipeline.run import run_brief, run_fetch, run_pipeline
from shipwatch.storage import Store


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="shipwatch",
        description="Know what AI companies actually shipped this week.",
    )
    parser.add_argument("--version", action="version", version=f"shipwatch {__version__}")
    parser.add_argument("--config", type=Path, help="Path to shipwatch.yaml")
    parser.add_argument("--data-dir", type=Path, help="Override SQLite data directory")
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Heuristic characterization, scoring, and extractive brief",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Write sample config and source pack")
    init.add_argument("--force", action="store_true")
    init.add_argument("--dir", type=Path, default=Path("."))

    fetch = sub.add_parser("fetch", help="Fetch sources into SQLite")
    fetch.add_argument("--source", help="Fetch a single source id")

    run = sub.add_parser("run", help="Fetch + score + brief")
    _brief_flags(run)

    brief = sub.add_parser("brief", help="Brief from items already in SQLite")
    _brief_flags(brief)

    sources = sub.add_parser("sources", help="Inspect the source pack")
    src_sub = sources.add_subparsers(dest="sources_command", required=True)
    check = src_sub.add_parser("check", help="Validate sources (add --live to hit the network)")
    check.add_argument("--live", action="store_true")

    sub.add_parser("stats", help="Show archive counts")
    return parser


def _brief_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--since", help="Window such as 7d, 2w, or an ISO timestamp")
    parser.add_argument("--top", type=int, dest="top_n", help="How many stories to keep")
    parser.add_argument("--out", type=Path, help="Output directory")
    parser.add_argument("--html", action="store_true", help="Also write a minimal index.html")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return _dispatch(args)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _dispatch(args: argparse.Namespace) -> int:
    if args.command == "init":
        written = write_init_files(args.dir, force=args.force)
        for path in written:
            print(f"wrote {path}")
        print("Edit sources.yaml, then run: shipwatch fetch && shipwatch run --no-llm")
        return 0

    cfg = _config(args)
    if args.command == "sources":
        return _sources_check(cfg, live=args.live)

    store = Store(cfg.db_path)
    try:
        if args.command == "fetch":
            stats = run_fetch(cfg, store, source_id=args.source)
            _print_fetch(stats)
            return 0
        if args.command == "run":
            _apply_brief_overrides(cfg, args)
            briefing, items, stats = run_pipeline(
                cfg,
                store,
                since=args.since,
                top_n=args.top_n,
                no_llm=args.no_llm,
                html=args.html or None,
            )
            _print_fetch(stats)
            _print_brief(briefing, cfg)
            return 0
        if args.command == "brief":
            _apply_brief_overrides(cfg, args)
            briefing, items, _stats = run_brief(
                cfg,
                store,
                since=args.since,
                top_n=args.top_n,
                no_llm=args.no_llm,
                html=args.html or None,
            )
            write_outputs(
                briefing,
                items,
                cfg.brief.output_dir,
                html=args.html or cfg.brief.html,
                archive=store.list_briefings(limit=20),
            )
            _print_brief(briefing, cfg)
            return 0
        if args.command == "stats":
            print(json.dumps(store.stats(), indent=2))
            return 0
    finally:
        store.close()
    return 1


def _config(args: argparse.Namespace) -> AppConfig:
    path = args.config
    if path is None:
        candidate = Path("shipwatch.yaml")
        path = candidate if candidate.exists() else None
    cfg = load_config(path)
    if getattr(args, "data_dir", None):
        cfg.data_dir = args.data_dir
    if getattr(args, "no_llm", False):
        pass
    return cfg


def _apply_brief_overrides(cfg: AppConfig, args: argparse.Namespace) -> None:
    if getattr(args, "out", None):
        cfg.brief.output_dir = args.out
    if getattr(args, "html", False):
        cfg.brief.html = True
    if getattr(args, "since", None):
        cfg.brief.since = args.since
    if getattr(args, "top_n", None):
        cfg.brief.top_n = args.top_n


def _print_fetch(stats) -> None:
    print(
        f"fetched {stats.fetched} sources · {stats.items_considered} items ({stats.items_new} new)"
    )
    for outcome in stats.outcomes:
        extra = f" HTTP {outcome.http_status}" if outcome.http_status else ""
        detail = f" — {outcome.detail}" if outcome.detail else ""
        print(f"  {outcome.source_id}: {outcome.status}{extra}{detail}")


def _print_brief(briefing, cfg: AppConfig) -> None:
    print(f"{briefing.title}")
    print(coverage_line(briefing.coverage))
    print(f"wrote {cfg.brief.output_dir / 'briefing.md'}")
    print(f"wrote {cfg.brief.output_dir / 'briefing.json'}")
    print(f"wrote {cfg.brief.output_dir / 'briefings.xml'}")
    if cfg.brief.html:
        print(f"wrote {cfg.brief.output_dir / 'index.html'}")


def _sources_check(cfg: AppConfig, *, live: bool) -> int:
    sources = cfg.sources or parse_sources(load_yaml(bundled_sources_path()))
    errors = 0
    for source in sources:
        problems: list[str] = []
        if source.kind is SourceKind.GITHUB and not source.repo:
            problems.append("missing repo")
        if source.kind is not SourceKind.GITHUB and not source.url:
            problems.append("missing url")
        if source.url and not source.url.startswith(("http://", "https://")):
            problems.append("url must be http(s)")
        status = "ok" if not problems else "invalid"
        if problems:
            errors += 1
        extra = f" ({'; '.join(problems)})" if problems else ""
        target = source.repo or source.url or ""
        print(f"{source.id:24} {source.kind.value:8} {status:8} {target}{extra}")
    print(f"{len(sources)} sources · {len(sources) - errors} valid · {errors} errors")
    if not live:
        return 1 if errors else 0

    client = PoliteClient(cfg.fetch, store=None)
    failed = 0
    try:
        for source in sources:
            if not source.enabled:
                print(f"{source.id:24} skipped (disabled)")
                continue
            result = check_url(client, source.target())
            mark = "ok" if result["ok"] else "FAIL"
            if not result["ok"]:
                failed += 1
            print(f"{source.id:24} {mark:8} {result.get('status')} {result['detail']}")
    finally:
        client.close()
    print(f"live check: {len(sources) - failed} reachable · {failed} failed")
    return 1 if failed or errors else 0
