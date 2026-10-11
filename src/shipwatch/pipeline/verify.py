"""Ground every claim in cited source text."""

from __future__ import annotations

from shipwatch.models import Briefing, BriefingSection, Claim, ClaimCoverage, Item
from shipwatch.textutil import content_tokens


def verify_briefing(briefing: Briefing, items: list[Item]) -> Briefing:
    by_id = {i.id: i for i in items}
    supported = flagged = dropped = 0
    total = 0
    for section in briefing.sections:
        kept: list[Claim] = []
        for claim in section.claims:
            total += 1
            checked = verify_claim(claim, by_id)
            if checked.status == "dropped":
                dropped += 1
                continue
            if checked.status == "flagged":
                flagged += 1
            else:
                supported += 1
            kept.append(checked)
        section.claims = kept
    briefing.coverage = ClaimCoverage(
        total_claims=total,
        supported=supported,
        flagged=flagged,
        dropped=dropped,
    )
    return briefing


def verify_claim(claim: Claim, items: dict[str, Item]) -> Claim:
    sources = [items[i] for i in claim.source_item_ids if i in items]
    if not sources:
        claim.status = "dropped"
        claim.supported = False
        claim.note = "no cited source item"
        return claim
    evidence_text = "\n".join(_item_blob(item) for item in sources)
    claim_tokens = content_tokens(claim.text, min_len=4)
    if not claim_tokens:
        claim.status = "flagged"
        claim.supported = False
        claim.note = "claim has no content words to check"
        claim.evidence = [_snippet(sources[0])]
        return claim
    evidence_tokens = set(content_tokens(evidence_text, min_len=4))
    hits = [t for t in claim_tokens if t in evidence_tokens]
    ratio = len(hits) / len(claim_tokens)
    claim.evidence = [_snippet(item) for item in sources[:3]]
    if ratio >= 0.5:
        claim.status = "supported"
        claim.supported = True
        claim.note = None
    elif ratio >= 0.25:
        claim.status = "flagged"
        claim.supported = False
        claim.note = f"weak overlap ({len(hits)}/{len(claim_tokens)} content words in sources)"
    else:
        claim.status = "dropped"
        claim.supported = False
        claim.note = f"unsupported ({len(hits)}/{len(claim_tokens)} content words in sources)"
    return claim


def _item_blob(item: Item) -> str:
    return f"{item.title}\n{item.summary}\n{item.content}"


def _snippet(item: Item, limit: int = 220) -> str:
    text = item.summary or item.content or item.title
    text = " ".join(text.split())
    return text[:limit]


def coverage_line(coverage: ClaimCoverage) -> str:
    ratio = f"{coverage.coverage_ratio:.0%}" if coverage.total_claims else "n/a"
    return (
        f"{coverage.total_claims} claims · {coverage.supported} supported · "
        f"{coverage.flagged} flagged · {coverage.dropped} dropped · coverage {ratio}"
    )


def empty_sections_note(sections: list[BriefingSection]) -> list[str]:
    notes: list[str] = []
    if not any(s.claims for s in sections):
        notes.append("Verifier dropped every claim; nothing left to publish from this window.")
    return notes
