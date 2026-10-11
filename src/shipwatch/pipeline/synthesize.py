"""Extractive and LLM briefing synthesis. Every claim cites item ids."""

from __future__ import annotations

from datetime import datetime

from shipwatch.dates import format_window, now_utc
from shipwatch.models import Briefing, BriefingSection, Claim, Cluster, Fact, Item
from shipwatch.textutil import clean_claim, sentence_split, sha16


def synthesize_extractive(
    clusters: list[Cluster],
    items: list[Item],
    facts: list[Fact],
    *,
    since: str,
    window_start: datetime,
    now: datetime | None = None,
    mode: str = "heuristic",
) -> Briefing:
    stamp = now or now_utc()
    by_id = {i.id: i for i in items}
    facts_by_item: dict[str, list[Fact]] = {}
    for fact in facts:
        facts_by_item.setdefault(fact.item_id, []).append(fact)

    sections: list[BriefingSection] = []
    selected: list[str] = []
    for cluster in clusters:
        members = [by_id[i] for i in cluster.item_ids if i in by_id and not by_id[i].duplicate_of]
        members.sort(key=lambda i: i.score, reverse=True)
        if not members:
            continue
        claims: list[Claim] = []
        for item in members[:3]:
            claim_text = _extractive_claim(item, facts_by_item.get(item.id, []))
            claims.append(
                Claim(
                    text=claim_text,
                    source_item_ids=[item.id],
                    evidence=[item.summary or item.title],
                )
            )
        heading = _heading(cluster, members)
        sections.append(
            BriefingSection(
                heading=heading,
                score=cluster.score,
                item_ids=[m.id for m in members],
                claims=claims,
            )
        )
        selected.extend(m.id for m in members)

    title = f"Shipwatch briefing — {format_window(window_start, stamp)}"
    return Briefing(
        id=sha16("brief", stamp.isoformat(), since),
        title=title,
        generated_at=stamp,
        since=since,
        window_start=window_start,
        mode=mode,
        sections=sections,
        selected_item_ids=selected,
    )


def briefing_from_llm_payload(
    payload: dict,
    clusters: list[Cluster],
    items: list[Item],
    *,
    since: str,
    window_start: datetime,
    now: datetime | None = None,
) -> Briefing:
    """Map a validated LLM JSON object onto the briefing model."""
    stamp = now or now_utc()
    by_id = {i.id: i for i in items}
    known = set(by_id)
    sections: list[BriefingSection] = []
    selected: list[str] = []
    raw_sections = payload.get("sections") or []
    for idx, raw in enumerate(raw_sections):
        if not isinstance(raw, dict):
            continue
        item_ids = [i for i in (raw.get("item_ids") or []) if i in known]
        claims: list[Claim] = []
        for row in raw.get("claims") or []:
            if not isinstance(row, dict):
                continue
            text = str(row.get("text") or "").strip()
            cited = [i for i in (row.get("source_item_ids") or item_ids) if i in known]
            if not text or not cited:
                continue
            claims.append(Claim(text=text, source_item_ids=cited))
        if not claims:
            continue
        cluster = clusters[idx] if idx < len(clusters) else None
        heading = str(raw.get("heading") or (cluster.topic if cluster else "Update"))
        score = float(raw.get("score") or (cluster.score if cluster else 0.0))
        sections.append(
            BriefingSection(
                heading=heading, score=score, item_ids=item_ids or cited_from(claims), claims=claims
            )
        )
        selected.extend(item_ids or cited_from(claims))
    title = str(
        payload.get("title") or f"Shipwatch briefing — {format_window(window_start, stamp)}"
    )
    return Briefing(
        id=sha16("brief", stamp.isoformat(), since, "llm"),
        title=title,
        generated_at=stamp,
        since=since,
        window_start=window_start,
        mode="llm",
        sections=sections,
        selected_item_ids=list(dict.fromkeys(selected)),
    )


def cited_from(claims: list[Claim]) -> list[str]:
    ids: list[str] = []
    for claim in claims:
        ids.extend(claim.source_item_ids)
    return list(dict.fromkeys(ids))


def _extractive_claim(item: Item, facts: list[Fact]) -> str:
    if facts:
        return clean_claim(facts[0].text)
    blob = item.content or item.summary or item.title
    sentences = sentence_split(blob)
    if sentences:
        return clean_claim(sentences[0])
    return clean_claim(item.title)


def _heading(cluster: Cluster, members: list[Item]) -> str:
    lead = members[0]
    return f"{lead.source_name}: {lead.title}"
