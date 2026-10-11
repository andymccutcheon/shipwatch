"""Item characterization: shipments vs promo, case studies, and the rest."""

from __future__ import annotations

import re

from shipwatch.models import Item, ItemKind

# Non-shipment first so a customer story that mentions an API does not
# get tagged as a launch or API change.
_NON_SHIPMENT = re.compile(
    r"(?:"
    r"\bhow\s+\w[\w'’.-]*\s+ships?\b"
    r"|\bships?\s+(?:faster|3×|3x|3 times)\b"
    r"|\bcase\s+stud(?:y|ies)\b"
    r"|\bcustomer\s+(?:stor(?:y|ies)|spotlight)\b"
    r"|\bpartner\s+spotlight\b"
    r"|\bwebinars?\b"
    r"|\b(?:we(?:'re| are)|now)\s+hiring\b"
    r"|\bjoin\s+(?:our|the)\s+team\b"
    r"|\bopen\s+roles?\b"
    r"|\b(?:opinion|commentary|editorial)\b"
    r"|\bour\s+take\b"
    r"|\bthoughts\s+on\b"
    r"|\bwhy\s+we\s+(?:believe|think)\b"
    r"|\bregister\s+now\b"
    r"|\bsave\s+the\s+date\b"
    r"|\bpromotional\b"
    r")",
    re.I,
)

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


_SHIPMENT_TITLE = re.compile(
    r"\b(introduc(?:e|ing)|launch(?:ed|ing)?|now available|generally available|"
    r"\bga\b|deprecat|sunset|pric(?:e|ing)|cve-\d)\b",
    re.I,
)


def characterize(item: Item) -> ItemKind:
    title = item.title or ""
    blob = f"{title}\n{item.summary}\n{item.content[:2000]}"
    # Title match wins: "How X ships faster" is a story even if the body
    # mentions an API. A real launch title is not demoted for a footer webinar.
    if _NON_SHIPMENT.search(title):
        return ItemKind.NON_SHIPMENT
    for kind, pattern in _RULES:
        if pattern.search(blob):
            return kind
    if _NON_SHIPMENT.search(blob) and not _SHIPMENT_TITLE.search(title):
        return ItemKind.NON_SHIPMENT
    return ItemKind.OTHER


def apply_characterization(
    items: list[Item], overrides: dict[str, ItemKind] | None = None
) -> list[Item]:
    overrides = overrides or {}
    for item in items:
        item.kind = overrides.get(item.id, characterize(item))
    return items
