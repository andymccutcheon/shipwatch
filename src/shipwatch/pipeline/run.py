"""End-to-end pipeline orchestration."""

from __future__ import annotations

from datetime import datetime

from shipwatch.config import AppConfig
from shipwatch.dates import now_utc, parse_since
from shipwatch.fetch.client import PoliteClient
from shipwatch.fetch.github import parse_github_releases
from shipwatch.fetch.html import parse_html
from shipwatch.fetch.rss import parse_rss
from shipwatch.fetch.sitemap import parse_sitemap
from shipwatch.llm import (
    BriefingOut,
    CharacterizationOut,
    FactsOut,
    LLMClient,
    LLMError,
    briefing_messages,
    characterization_messages,
    facts_messages,
)
from shipwatch.models import (
    Briefing,
    FetchOutcome,
    Item,
    ItemKind,
    RawItem,
    RunStats,
    SourceKind,
    SourceSpec,
)
from shipwatch.output.render import write_outputs
from shipwatch.pipeline.characterize import apply_characterization
from shipwatch.pipeline.cluster import cluster_items
from shipwatch.pipeline.dedup import dedup_items
from shipwatch.pipeline.extract import extract_facts, extract_facts_llm
from shipwatch.pipeline.score import score_clusters, score_items, select_top
from shipwatch.pipeline.synthesize import briefing_from_llm_payload, synthesize_extractive
from shipwatch.pipeline.verify import empty_sections_note, verify_briefing
from shipwatch.storage import Store
from shipwatch.textutil import normalize_url, sha16


def raw_to_item(raw: RawItem) -> Item:
    url = normalize_url(raw.url)
    return Item(
        id=sha16(raw.source_id, url),
        source_id=raw.source_id,
        source_name=raw.source_name,
        url=url,
        title=raw.title,
        published_at=raw.published_at,
        content=raw.content,
        summary=raw.summary or raw.content[:400],
        tags=list(raw.tags),
    )


def collect_source(
    source: SourceSpec,
    client: PoliteClient,
    store: Store,
    *,
    limit: int,
) -> tuple[list[RawItem], FetchOutcome]:
    url = source.target()
    try:
        resp = client.get(url, source=source)
    except PermissionError as exc:
        client.record_error(source, str(exc), status=None)
        return [], FetchOutcome(source_id=source.id, status="robots", detail=str(exc))
    except Exception as exc:  # network / parse later
        client.record_error(source, f"{type(exc).__name__}: {exc}")
        return [], FetchOutcome(
            source_id=source.id, status="error", detail=f"{type(exc).__name__}: {exc}"
        )

    if resp.not_modified:
        return [], FetchOutcome(source_id=source.id, status="not_modified", http_status=304)
    if resp.status_code >= 400:
        return [], FetchOutcome(
            source_id=source.id,
            status="http_error",
            http_status=resp.status_code,
            detail=f"HTTP {resp.status_code}",
        )
    try:
        items = parse_body(source, resp.content, str(resp.url), store=store, limit=limit)
    except Exception as exc:
        client.record_error(source, f"parse: {exc}", status=resp.status_code)
        return [], FetchOutcome(
            source_id=source.id,
            status="parse_error",
            http_status=resp.status_code,
            detail=str(exc),
        )
    return items, FetchOutcome(
        source_id=source.id,
        status="ok",
        http_status=resp.status_code,
        items=len(items),
    )


def parse_body(
    source: SourceSpec,
    body: bytes,
    final_url: str,
    *,
    store: Store,
    limit: int,
) -> list[RawItem]:
    if source.kind is SourceKind.RSS:
        return parse_rss(body, source, limit=limit)
    if source.kind is SourceKind.HTML:
        return parse_html(body, source, final_url, limit=limit)
    if source.kind is SourceKind.GITHUB:
        return parse_github_releases(body, source, limit=limit)
    if source.kind is SourceKind.SITEMAP:
        seen = store.seen_urls(source.id)
        items, all_locs, children = parse_sitemap(body, source, seen=seen, limit=limit)
        if children and not items:
            return []
        store.mark_seen(source.id, all_locs, first_seen=now_utc())
        return items
    raise ValueError(f"unsupported source kind {source.kind}")


def run_fetch(
    cfg: AppConfig,
    store: Store,
    *,
    client: PoliteClient | None = None,
    source_id: str | None = None,
) -> RunStats:
    own_client = client is None
    client = client or PoliteClient(cfg.fetch, store)
    stats = RunStats()
    try:
        sources = cfg.enabled_sources()
        if source_id:
            sources = [s for s in sources if s.id == source_id]
            if not sources:
                raise ValueError(f"unknown or disabled source: {source_id}")
        fetched_at = now_utc()
        for source in sources:
            raws, outcome = collect_source(
                source, client, store, limit=cfg.fetch.max_items_per_source
            )
            if source.kind is SourceKind.SITEMAP and outcome.status == "ok" and not raws:
                raws = _expand_sitemap(source, client, store, cfg.fetch.max_items_per_source)
                outcome.items = len(raws)
            new = 0
            for raw in raws:
                item = raw_to_item(raw)
                if store.upsert_item(item, fetched_at=fetched_at):
                    new += 1
            outcome.new_items = new
            stats.outcomes.append(outcome)
            stats.fetched += 1
            stats.items_considered += outcome.items
            stats.items_new += new
        return stats
    finally:
        if own_client:
            client.close()


def _expand_sitemap(
    source: SourceSpec, client: PoliteClient, store: Store, limit: int
) -> list[RawItem]:
    # Re-fetch already stored last body is not available; collect_source already parsed.
    # This helper is used when the first response was a sitemapindex (no urlset items).
    # We try the original URL body is gone, so we re-get without conditional.
    try:
        resp = client.get(source.target(), source=source, conditional=False)
        items, _locs, children = parse_sitemap(
            resp.content, source, seen=store.seen_urls(source.id), limit=limit
        )
        if items:
            store.mark_seen(source.id, [i.url for i in items], first_seen=now_utc())
            return items
        collected: list[RawItem] = []
        seen = store.seen_urls(source.id)
        for child in children[:5]:
            child_resp = client.get(child, source=source, conditional=False)
            child_items, child_locs, _more = parse_sitemap(
                child_resp.content, source, seen=seen, limit=limit - len(collected)
            )
            store.mark_seen(source.id, child_locs, first_seen=now_utc())
            seen.update(child_locs)
            collected.extend(child_items)
            if len(collected) >= limit:
                break
        return collected[:limit]
    except Exception:
        return []


def _maybe_llm(cfg: AppConfig, no_llm: bool) -> LLMClient | None:
    if no_llm:
        return None
    return LLMClient(cfg.llm)


def run_brief(
    cfg: AppConfig,
    store: Store,
    *,
    since: str | None = None,
    top_n: int | None = None,
    no_llm: bool = False,
    now: datetime | None = None,
    llm: LLMClient | None = None,
    write: bool = True,
    html: bool | None = None,
) -> tuple[Briefing, list[Item], RunStats]:
    stamp = now or now_utc()
    since_label = since or cfg.brief.since
    window_start = parse_since(since_label, now=stamp)
    items = store.items_since(window_start)
    stats = RunStats(items_considered=len(items))
    if not items:
        briefing = synthesize_extractive(
            [], [], [], since=since_label, window_start=window_start, now=stamp
        )
        briefing.notes.append("No items in this window. Run `shipwatch fetch` first.")
        if write:
            write_outputs(
                briefing, [], cfg.brief.output_dir, html=cfg.brief.html if html is None else html
            )
        return briefing, [], stats

    own_llm = False
    client = llm
    if client is None and not no_llm:
        client = _maybe_llm(cfg, no_llm)
        own_llm = client is not None

    try:
        overrides: dict[str, ItemKind] = {}
        if client:
            for item in items:
                try:
                    data = client.complete_json(
                        characterization_messages(item.title, item.content or item.summary),
                        CharacterizationOut,
                    )
                    overrides[item.id] = ItemKind(data["kind"])
                except (LLMError, ValueError):
                    continue
        apply_characterization(items, overrides)

        all_facts = []
        for item in items:
            facts = extract_facts(item)
            if client:
                try:
                    data = client.complete_json(
                        facts_messages(item.title, item.content or item.summary),
                        FactsOut,
                    )
                    facts = extract_facts_llm(item, data.get("facts") or [])
                except LLMError:
                    pass
            store.replace_facts(item.id, facts)
            all_facts.extend(facts)
        stats.facts = len(all_facts)

        dedup_items(items, threshold=cfg.scoring.near_dup_threshold)
        for item in items:
            store.upsert_item(item, fetched_at=stamp)

        clusters = cluster_items(items, threshold=cfg.scoring.cluster_threshold)
        score_items(items, cfg.scoring, now=stamp)
        score_clusters(clusters, items)
        selected = select_top(clusters, top_n=top_n or cfg.brief.top_n)
        store.replace_clusters(selected, created_at=stamp)
        stats.clusters = len(clusters)
        stats.selected = len(selected)

        briefing: Briefing
        mode = "heuristic"
        if client:
            payload_items = []
            by_id = {i.id: i for i in items}
            for cluster in selected:
                for item_id in cluster.item_ids:
                    item = by_id.get(item_id)
                    if item and not item.duplicate_of:
                        payload_items.append(
                            {
                                "id": item.id,
                                "source": item.source_name,
                                "title": item.title,
                                "url": item.url,
                                "kind": item.kind.value,
                                "score": item.score,
                                "summary": (item.summary or item.content)[:800],
                            }
                        )
            try:
                data = client.complete_json(briefing_messages(payload_items), BriefingOut)
                briefing = briefing_from_llm_payload(
                    data, selected, items, since=since_label, window_start=window_start, now=stamp
                )
                mode = "llm"
            except LLMError as exc:
                briefing = synthesize_extractive(
                    selected,
                    items,
                    all_facts,
                    since=since_label,
                    window_start=window_start,
                    now=stamp,
                )
                briefing.notes.append(f"LLM synthesis failed; used extractive briefing. ({exc})")
        else:
            briefing = synthesize_extractive(
                selected, items, all_facts, since=since_label, window_start=window_start, now=stamp
            )
        briefing.mode = mode
        verify_briefing(briefing, items)
        briefing.notes.extend(empty_sections_note(briefing.sections))
        store.save_briefing(briefing)
        for item in items:
            store.upsert_item(item, fetched_at=stamp)
        if write:
            write_outputs(
                briefing,
                items,
                cfg.brief.output_dir,
                html=cfg.brief.html if html is None else html,
                archive=store.list_briefings(limit=20),
            )
        return briefing, items, stats
    finally:
        if own_llm and client is not None:
            client.close()


def run_pipeline(
    cfg: AppConfig,
    store: Store,
    *,
    since: str | None = None,
    top_n: int | None = None,
    no_llm: bool = False,
    client: PoliteClient | None = None,
    llm: LLMClient | None = None,
    html: bool | None = None,
    now: datetime | None = None,
) -> tuple[Briefing, list[Item], RunStats]:
    fetch_stats = run_fetch(cfg, store, client=client)
    briefing, items, brief_stats = run_brief(
        cfg,
        store,
        since=since,
        top_n=top_n,
        no_llm=no_llm,
        llm=llm,
        html=html,
        now=now,
    )
    brief_stats.fetched = fetch_stats.fetched
    brief_stats.items_new = fetch_stats.items_new
    brief_stats.outcomes = fetch_stats.outcomes
    return briefing, items, brief_stats
