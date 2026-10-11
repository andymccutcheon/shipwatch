"""Item characterization: launch, model, pricing, deprecation, and the rest."""

from __future__ import annotations

import re

from shipwatch.models import Item, ItemKind

_RULES: list[tuple[ItemKind, re.Pattern[str]]] = [
    (
        ItemKind.SECURITY,
        re.compile(r"\b(cve-\d|security advisory|vulnerabilit|security patch|incident)\b", re.I),
    ),
    (
        ItemKind.DEPRECATION,
        re.compile(
            r"\b(deprecat|sunset|end of life|end-of-life|\beol\b|retir(e|ing)|removed)\b", re.I
        ),
    ),
    (
        ItemKind.PRICING_CHANGE,
        re.compile(r"\b(pric(?:e|ing)|cheaper|discount|cost per|tokens? per|billing)\b", re.I),
    ),
    (
        ItemKind.MODEL_RELEASE,
        re.compile(
            r"\b(gpt-|claude|gemini|llama|mistral|grok|"
            r"model (?:card|release|weights)|foundation model)\b",
            re.I,
        ),
    ),
    (
        ItemKind.LAUNCH,
        re.compile(
            r"\b(introduc(?:e|ing)|launch(?:ed|ing)?|announc(?:e|ing)|"
            r"now available|generally available|\bga\b)\b",
            re.I,
        ),
    ),
    (
        ItemKind.AVAILABILITY,
        re.compile(
            r"\b(region|available in|rollout|waitlist|generally available|expanding to)\b", re.I
        ),
    ),
    (
        ItemKind.API_CHANGE,
        re.compile(r"\b(api|endpoint|sdk|breaking change|openapi|function call|tool call)\b", re.I),
    ),
]


def characterize(item: Item) -> ItemKind:
    blob = f"{item.title}\n{item.summary}\n{item.content[:2000]}"
    for kind, pattern in _RULES:
        if pattern.search(blob):
            return kind
    return ItemKind.OTHER


def apply_characterization(
    items: list[Item], overrides: dict[str, ItemKind] | None = None
) -> list[Item]:
    overrides = overrides or {}
    for item in items:
        item.kind = overrides.get(item.id, characterize(item))
    return items
