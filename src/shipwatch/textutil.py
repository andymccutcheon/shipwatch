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


_SENT_END = re.compile(r"(?<=[.!?])\s+")
# Marketing pages often glue card titles together without periods:
# "…on Atlas Two-person team closed 800+ tickets…"
_MASHED = re.compile(
    r"(?<=[a-z0-9)])\s+(?=[A-Z][\w'-]+(?:-[A-Za-z0-9]+)?(?:\s+[A-Z][\w'-]+){0,2}\s+[a-z])"
)
MAX_CLAIM_CHARS = 220


def sentence_split(text: str) -> list[str]:
    """Split on paragraphs and punctuation; un-mash glued marketing cards."""
    paragraphs = [collapse_ws(p) for p in re.split(r"\n+", text or "") if collapse_ws(p)]
    if not paragraphs and text:
        paragraphs = [collapse_ws(text)]
    out: list[str] = []
    seen: set[str] = set()
    for para in paragraphs:
        for chunk in _SENT_END.split(para):
            pieces = _MASHED.split(chunk) if len(chunk) > 160 else [chunk]
            for piece in pieces:
                cleaned = piece.strip(" -•\t")
                if len(cleaned) < 20:
                    continue
                key = cleaned.lower()
                if key in seen:
                    continue
                seen.add(key)
                out.append(cleaned)
    return out


def clean_claim(text: str) -> str:
    """One extractive sentence, not a mashed card dump."""
    candidates = sentence_split(text)
    if not candidates:
        fallback = collapse_ws(text)
        return fallback[:MAX_CLAIM_CHARS].rstrip()
    for sentence in candidates:
        if 24 <= len(sentence) <= MAX_CLAIM_CHARS:
            return sentence
    first = candidates[0]
    if len(first) <= MAX_CLAIM_CHARS:
        return first
    clipped = first[:MAX_CLAIM_CHARS].rsplit(" ", 1)[0].rstrip(" ,;:")
    return clipped or first[:MAX_CLAIM_CHARS]


def slug(text: str, *, limit: int = 48) -> str:
    words = content_tokens(text)
    if not words:
        return "topic"
    return "-".join(words[:8])[:limit].strip("-") or "topic"
