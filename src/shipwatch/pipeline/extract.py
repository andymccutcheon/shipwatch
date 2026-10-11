"""Fact extraction from normalized items."""

from __future__ import annotations

from shipwatch.models import Fact, Item, ItemKind
from shipwatch.textutil import collapse_ws, sentence_split, sha16


def extract_facts(item: Item, *, limit: int = 8) -> list[Fact]:
    text = item.content or item.summary or item.title
    sentences = sentence_split(text)
    if not sentences:
        sentences = [collapse_ws(item.title)]
    facts: list[Fact] = []
    seen: set[str] = set()
    for sentence in sentences:
        key = sentence.lower()
        if key in seen:
            continue
        seen.add(key)
        facts.append(
            Fact(
                id=sha16(item.id, sentence),
                item_id=item.id,
                text=sentence,
                kind=item.kind,
                evidence=sentence,
            )
        )
        if len(facts) >= limit:
            break
    return facts


def extract_facts_llm(item: Item, drafts: list[dict], *, limit: int = 8) -> list[Fact]:
    facts: list[Fact] = []
    for row in drafts[:limit]:
        text = collapse_ws(str(row.get("text") or ""))
        evidence = collapse_ws(str(row.get("evidence") or text))
        if not text:
            continue
        kind_raw = str(row.get("kind") or item.kind.value)
        try:
            kind = ItemKind(kind_raw)
        except ValueError:
            kind = item.kind
        facts.append(
            Fact(
                id=sha16(item.id, text),
                item_id=item.id,
                text=text,
                kind=kind,
                evidence=evidence,
            )
        )
    return facts or extract_facts(item)
