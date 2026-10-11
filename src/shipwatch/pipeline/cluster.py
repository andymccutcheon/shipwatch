"""Greedy topic clustering by token overlap."""

from __future__ import annotations

from collections import Counter

from shipwatch.models import Cluster, Item
from shipwatch.textutil import jaccard, sha16, slug, token_set


def cluster_items(items: list[Item], *, threshold: float = 0.28) -> list[Cluster]:
    active = [i for i in items if not i.duplicate_of]
    tokens = {item.id: token_set(f"{item.title} {item.summary}") for item in active}
    groups: list[list[Item]] = []
    for item in active:
        placed = False
        for group in groups:
            seed = group[0]
            if jaccard(tokens[item.id], tokens[seed.id]) >= threshold:
                group.append(item)
                placed = True
                break
            company_match = (
                item.source_id == seed.source_id
                and jaccard(tokens[item.id], tokens[seed.id]) >= threshold * 0.6
            )
            if company_match:
                group.append(item)
                placed = True
                break
        if not placed:
            groups.append([item])

    clusters: list[Cluster] = []
    for group in groups:
        topic = _topic(group)
        cluster = Cluster(
            id=sha16("cluster", *(sorted(i.id for i in group))),
            topic=topic,
            item_ids=[i.id for i in group],
        )
        for item in group:
            item.cluster_id = cluster.id
        clusters.append(cluster)
    return clusters


def _topic(group: list[Item]) -> str:
    bag: Counter[str] = Counter()
    for item in group:
        bag.update(token_set(item.title))
    common = [w for w, _n in bag.most_common(6) if len(w) > 3]
    if common:
        return " ".join(common[:4])
    return slug(group[0].title)
