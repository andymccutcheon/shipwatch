"""URL-exact and semantic near-duplicate detection."""

from __future__ import annotations

from shipwatch.models import Item
from shipwatch.textutil import jaccard, normalize_url, token_set


def dedup_items(items: list[Item], *, threshold: float = 0.62) -> list[Item]:
    """Mark near-duplicates. Survivors keep the richest content."""
    by_url: dict[str, Item] = {}
    ordered: list[Item] = []
    for item in items:
        key = normalize_url(item.url)
        prior = by_url.get(key)
        if prior is None:
            by_url[key] = item
            ordered.append(item)
            continue
        winner, loser = _prefer(prior, item)
        if winner.id != prior.id:
            _rewire(ordered, prior, winner)
            by_url[key] = winner
        loser.duplicate_of = winner.id
        if loser not in ordered:
            ordered.append(loser)

    survivors = [i for i in ordered if not i.duplicate_of]
    tokens = {
        item.id: token_set(f"{item.title} {item.summary} {item.content[:800]}")
        for item in survivors
    }
    for i, left in enumerate(survivors):
        if left.duplicate_of:
            continue
        for right in survivors[i + 1 :]:
            if right.duplicate_of:
                continue
            if jaccard(tokens[left.id], tokens[right.id]) >= threshold:
                winner, loser = _prefer(left, right)
                loser.duplicate_of = winner.id
    return items


def _prefer(a: Item, b: Item) -> tuple[Item, Item]:
    a_len = len(a.content)
    b_len = len(b.content)
    if b_len > a_len + 40:
        return b, a
    if a.published_at and b.published_at and b.published_at > a.published_at and b_len >= a_len:
        return b, a
    return a, b


def _rewire(ordered: list[Item], old: Item, new: Item) -> None:
    for idx, item in enumerate(ordered):
        if item.id == old.id:
            ordered[idx] = new
            old.duplicate_of = new.id
            return
