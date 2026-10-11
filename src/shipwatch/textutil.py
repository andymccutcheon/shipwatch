"""Small text helpers used by fetch, score, dedup, and verify."""

from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+._-]{1,}", re.IGNORECASE)
_WS_RE = re.compile(r"\s+")
_TRACKING = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "ref",
    "fbclid",
    "gclid",
}
_STOP = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "in",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "was",
    "with",
    "you",
    "your",
    "we",
    "our",
    "new",
    "now",
    "also",
}


def sha16(*parts: str) -> str:
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
    return digest[:16]


def collapse_ws(text: str) -> str:
    return _WS_RE.sub(" ", text).strip()


def normalize_url(url: str) -> str:
    split = urlsplit(url.strip())
    query = [
        (k, v)
        for k, v in parse_qsl(split.query, keep_blank_values=True)
        if k.lower() not in _TRACKING
    ]
    path = split.path.rstrip("/") or "/"
    return urlunsplit(
        (split.scheme.lower(), split.netloc.lower(), path, urlencode(query), split.fragment)
    )


def tokenize(text: str) -> list[str]:
    return [m.group(0).lower() for m in _TOKEN_RE.finditer(text)]


def content_tokens(text: str, *, min_len: int = 3) -> list[str]:
    return [t for t in tokenize(text) if len(t) >= min_len and t not in _STOP]


def token_set(text: str) -> set[str]:
    return set(content_tokens(text))


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def sentence_split(text: str) -> list[str]:
    chunks = re.split(r"(?<=[.!?])\s+|\n+", collapse_ws(text))
    return [c.strip(" -•\t") for c in chunks if len(c.strip()) >= 20]


def slug(text: str, *, limit: int = 48) -> str:
    words = content_tokens(text)
    if not words:
        return "topic"
    return "-".join(words[:8])[:limit].strip("-") or "topic"
