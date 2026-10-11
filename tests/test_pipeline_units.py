from __future__ import annotations

from datetime import datetime, timedelta, timezone

from shipwatch.config import ScoringSettings
from shipwatch.models import Claim, ItemKind
from shipwatch.pipeline.characterize import characterize
from shipwatch.pipeline.cluster import cluster_items
from shipwatch.pipeline.dedup import dedup_items
from shipwatch.pipeline.extract import extract_facts
from shipwatch.pipeline.score import score_items
from shipwatch.pipeline.verify import verify_claim
from tests.conftest import NOW, make_item


def test_characterize_kinds() -> None:
    assert characterize(make_item()) is ItemKind.PRICING_CHANGE
    assert (
        characterize(
            make_item(
                title="Legacy Completions API sunset",
                content="We will deprecate the Completions API on 15 January 2027.",
            )
        )
        is ItemKind.DEPRECATION
    )
    assert (
        characterize(
            make_item(
                title="Security advisory CVE-2026-1",
                content="A vulnerability in the SDK was patched.",
            )
        )
        is ItemKind.SECURITY
    )
    assert (
        characterize(
            make_item(
                title="Introducing Mistral Large 4",
                content="We are launching Mistral Large 4 weights.",
            )
        )
        is ItemKind.MODEL_RELEASE
    )
    assert (
        characterize(
            make_item(
                title="Introducing the new dashboard",
                content="We are launching a workspace dashboard for all customers.",
            )
        )
        is ItemKind.LAUNCH
    )


def test_dedup_url_and_near_dup() -> None:
    a = make_item(item_id="a", url="https://openai.example/price-cut?utm_source=rss")
    b = make_item(
        item_id="b",
        url="https://openai.example/price-cut/",
        content=a.content + " Extra sentence about prepaid accounts.",
    )
    c = make_item(
        item_id="c",
        url="https://mirror.example/openai-price-cut",
        title="OpenAI reduces GPT-5 mini API pricing by 50%",
        content="OpenAI announced a 50% price reduction for GPT-5 mini input tokens in the API.",
    )
    items = [a, b, c]
    dedup_items(items)
    survivors = [i for i in items if not i.duplicate_of]
    assert len(survivors) == 1
    assert {i.duplicate_of for i in items if i.duplicate_of} == {survivors[0].id}


def test_cluster_groups_related_titles() -> None:
    items = [
        make_item(item_id="p1", title="OpenAI cuts API prices for GPT-5 mini"),
        make_item(
            item_id="p2",
            source_id="mirror",
            url="https://mirror.example/x",
            title="OpenAI reduces GPT-5 mini API prices",
        ),
        make_item(
            item_id="d1",
            source_id="anthropic",
            url="https://anthropic.example/sunset",
            title="Completions API sunset",
            content="Anthropic will deprecate Completions.",
            kind=ItemKind.DEPRECATION,
        ),
    ]
    clusters = cluster_items(items, threshold=0.2)
    assert len(clusters) >= 2


def test_score_boosts_pricing_and_recency() -> None:
    settings = ScoringSettings()
    fresh = make_item(item_id="fresh", published_at=NOW)
    old = make_item(
        item_id="old",
        url="https://openai.example/old",
        title="Old SDK tweak",
        content="Minor SDK docs wording.",
        kind=ItemKind.OTHER,
        published_at=NOW - timedelta(days=30),
    )
    score_items([fresh, old], settings, now=NOW)
    assert fresh.score > old.score
    assert fresh.score_breakdown["boost"] == settings.pricing_boost


def test_extract_and_verify_supported_claim() -> None:
    item = make_item()
    facts = extract_facts(item)
    assert facts
    claim = Claim(text=facts[0].text, source_item_ids=[item.id])
    checked = verify_claim(claim, {item.id: item})
    assert checked.status == "supported"


def test_verify_drops_unsupported_claim() -> None:
    item = make_item()
    claim = Claim(
        text="Anthropic acquired a semiconductor company in Austin yesterday.",
        source_item_ids=[item.id],
    )
    checked = verify_claim(claim, {item.id: item})
    assert checked.status == "dropped"


def test_verify_drops_missing_source() -> None:
    claim = Claim(text="Something happened.", source_item_ids=["missing"])
    assert verify_claim(claim, {}).status == "dropped"


def test_parse_since_units() -> None:
    from shipwatch.dates import parse_since

    start = parse_since("7d", now=NOW)
    assert start == NOW - timedelta(days=7)
    assert parse_since("2w", now=NOW) == NOW - timedelta(weeks=2)
    iso = parse_since("2026-10-01T00:00:00+00:00")
    assert iso == datetime(2026, 10, 1, tzinfo=timezone.utc)
