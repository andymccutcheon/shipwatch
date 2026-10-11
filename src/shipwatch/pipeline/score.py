"""Configurable materiality scoring."""

from __future__ import annotations

import math
from datetime import datetime

from shipwatch.config import ScoringSettings
from shipwatch.dates import ensure_aware
from shipwatch.models import Cluster, Item, ItemKind
from shipwatch.textutil import content_tokens, token_set

IMPACT = {
    ItemKind.MODEL_RELEASE: 0.92,
    ItemKind.LAUNCH: 0.88,
    ItemKind.DEPRECATION: 0.86,
    ItemKind.PRICING_CHANGE: 0.84,
    ItemKind.SECURITY: 0.80,
    ItemKind.API_CHANGE: 0.62,
    ItemKind.AVAILABILITY: 0.58,
    ItemKind.OTHER: 0.32,
}

_IMPACT_WORDS = (
    "breaking",
    "generally available",
    "ga",
    "major",
    "preview",
    "enterprise",
    "all customers",
    "price",
    "deprecat",
    "cve",
)


def score_items(items: list[Item], settings: ScoringSettings, *, now: datetime) -> list[Item]:
    now = ensure_aware(now)
    active = [i for i in items if not i.duplicate_of]
    universe: list[str] = []
    for item in active:
        universe.extend(content_tokens(f"{item.title} {item.summary}"))
    freq: dict[str, int] = {}
    for token in universe:
        freq[token] = freq.get(token, 1) + 1
    total = max(len(active), 1)

    for item in active:
        novelty = _novelty(item, active, freq, total)
        impact = _impact(item)
        breadth = _breadth(item)
        recency = _recency(item, settings, now)
        boost = _boost(item, settings)
        raw = (
            settings.novelty * novelty
            + settings.impact * impact
            + settings.breadth * breadth
            + settings.recency * recency
            + boost
        )
        item.score = max(0.0, min(1.0, raw))
        item.score_breakdown = {
            "novelty": round(novelty, 4),
            "impact": round(impact, 4),
            "breadth": round(breadth, 4),
            "recency": round(recency, 4),
            "boost": round(boost, 4),
        }
    return items


def score_clusters(clusters: list[Cluster], items: list[Item]) -> list[Cluster]:
    by_id = {i.id: i for i in items}
    for cluster in clusters:
        members = [by_id[i] for i in cluster.item_ids if i in by_id]
        if not members:
            cluster.score = 0.0
            continue
        scores = [m.score for m in members]
        mean = sum(scores) / len(scores)
        peak = max(scores)
        size_bonus = min(0.12, 0.04 * math.log(len(members) + 1, 2))
        cluster.score = max(0.0, min(1.0, 0.7 * peak + 0.3 * mean + size_bonus))
    return clusters


def select_top(clusters: list[Cluster], *, top_n: int) -> list[Cluster]:
    ranked = sorted(clusters, key=lambda c: c.score, reverse=True)
    return ranked[: max(1, top_n)]


def _novelty(item: Item, peers: list[Item], freq: dict[str, int], total: int) -> float:
    tokens = token_set(f"{item.title} {item.summary}")
    if not tokens:
        return 0.4
    rarity = sum(1.0 / freq.get(tok, total) for tok in tokens) / len(tokens)
    others = [p for p in peers if p.id != item.id]
    if not others:
        return min(1.0, 0.55 + rarity)
    # Distinct from the closest peer title.
    from shipwatch.textutil import jaccard

    closest = max(jaccard(tokens, token_set(p.title)) for p in others)
    return max(0.15, min(1.0, (1.0 - closest) * 0.7 + rarity * 0.3))


def _impact(item: Item) -> float:
    base = IMPACT.get(item.kind, 0.32)
    blob = f"{item.title} {item.summary}".lower()
    bump = 0.06 * sum(1 for word in _IMPACT_WORDS if word in blob)
    return min(1.0, base + bump)


def _breadth(item: Item) -> float:
    blob = f"{item.title} {item.summary} {item.content[:400]}".lower()
    score = 0.35
    if any(w in blob for w in ("api", "sdk", "developers", "platform")):
        score += 0.2
    if any(w in blob for w in ("enterprise", "all users", "all customers", "generally available")):
        score += 0.25
    if any(w in blob for w in ("region", "europe", "japan", "india", "available in")):
        score += 0.1
    return min(1.0, score)


def _recency(item: Item, settings: ScoringSettings, now: datetime) -> float:
    if item.published_at is None:
        return 0.45
    published = ensure_aware(item.published_at)
    age_days = max(0.0, (now - published).total_seconds() / 86400)
    half = max(settings.recency_half_life_days, 0.5)
    return 0.5 ** (age_days / half)


def _boost(item: Item, settings: ScoringSettings) -> float:
    if item.kind is ItemKind.PRICING_CHANGE:
        return settings.pricing_boost
    if item.kind is ItemKind.DEPRECATION:
        return settings.deprecation_boost
    if item.kind is ItemKind.SECURITY:
        return settings.security_boost
    return 0.0
