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
                title="Contoso Large 4 model release",
                content="We are launching Contoso Large 4 model weights.",
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
    assert (
        characterize(
            make_item(
                title="How Northwind ships 3× faster with Acme agents",
                content="Northwind closed 800 tickets. The Acme API is generally available.",
                kind=ItemKind.OTHER,
            )
        )
        is ItemKind.NON_SHIPMENT
    )
    assert (
        characterize(
            make_item(
                title="Join the Contoso webinar next Thursday",
                content="Register now to hear about Atlas.",
                kind=ItemKind.OTHER,
            )
        )
        is ItemKind.NON_SHIPMENT
    )
    assert (
        characterize(
            make_item(
                title="Contoso Models is now hiring",
                content="Open roles on the Atlas research team.",
                kind=ItemKind.OTHER,
            )
        )
        is ItemKind.NON_SHIPMENT
    )
    assert (
        characterize(
            make_item(
                title="Our take on open weights",
                content="Opinion: why we believe smaller models win.",
                kind=ItemKind.OTHER,
            )
        )
        is ItemKind.NON_SHIPMENT
    )
    assert (
        characterize(
            make_item(
                title="Introducing Helio-8, now generally available",
                content="Register now for the launch webinar. Footer: join the team.",
                kind=ItemKind.OTHER,
            )
        )
        is ItemKind.LAUNCH
    )


def test_dedup_url_and_near_dup() -> None:
    a = make_item(item_id="a", url="https://acme.example/price-cut?utm_source=rss")
    b = make_item(
        item_id="b",
        url="https://acme.example/price-cut/",
        content=a.content + " Extra sentence about prepaid accounts.",
    )
    c = make_item(
        item_id="c",
        url="https://mirror.example/acme-price-cut",
        title="Acme AI reduces Helio-7 mini API pricing by 50%",
        content="Acme AI announced a 50% price reduction for Helio-7 mini input tokens in the API.",
    )
    items = [a, b, c]
    dedup_items(items)
    survivors = [i for i in items if not i.duplicate_of]
    assert len(survivors) == 1
    assert {i.duplicate_of for i in items if i.duplicate_of} == {survivors[0].id}


def test_cluster_groups_related_titles() -> None:
    items = [
        make_item(item_id="p1", title="Acme AI cuts API prices for Helio-7 mini"),
        make_item(
            item_id="p2",
            source_id="mirror",
            url="https://mirror.example/x",
            title="Acme AI reduces Helio-7 mini API prices",
        ),
        make_item(
            item_id="d1",
            source_id="contoso",
            url="https://contoso.example/sunset",
            title="Completions API sunset",
            content="Contoso Models will deprecate Completions.",
            kind=ItemKind.DEPRECATION,
        ),
    ]
    clusters = cluster_items(items, threshold=0.2)
    assert len(clusters) >= 2


def test_score_ranks_shipment_above_case_study() -> None:
    settings = ScoringSettings()
    shipment = make_item(
        item_id="ship",
        title="Acme AI cuts API prices for Helio-7 mini",
        content="Acme AI announced a 50% price reduction for Helio-7 mini input tokens.",
        kind=ItemKind.OTHER,
    )
    story = make_item(
        item_id="story",
        source_id="northwind",
        source_name="Northwind Agents",
        url="https://contoso.example/how-northwind-ships",
        title="How Northwind ships 3× faster with Atlas",
        content="Northwind closed 800 tickets. The Atlas API is generally available.",
        kind=ItemKind.OTHER,
    )
    from shipwatch.pipeline.characterize import apply_characterization

    apply_characterization([shipment, story])
    assert shipment.kind is ItemKind.PRICING_CHANGE
    assert story.kind is ItemKind.NON_SHIPMENT
    score_items([shipment, story], settings, now=NOW)
    assert shipment.score > story.score
    assert story.score_breakdown["penalty"] == settings.non_shipment_penalty
    assert story.score_breakdown["boost"] == 0.0
    assert shipment.score_breakdown["penalty"] == 0.0


def test_sentence_split_unmashes_marketing_cards() -> None:
    from shipwatch.textutil import clean_claim, sentence_split

    mashed = (
        "Northwind on Atlas Tripled shipping rate in three months with invented agents "
        "Two-person team closed 800+ tickets in its first 4 months Builder access via SSO "
        "and Directory Sync Ships customer-requested changes to production in as little as "
        "two hours Gives every builder access to models through the Atlas gateway "
        "Northwind Agents is an invented operations platform."
    )
    pieces = sentence_split(mashed)
    assert len(pieces) >= 3
    assert all(len(piece) < 220 for piece in pieces)
    mashed_together = any(
        "Tripled shipping rate" in piece and "Two-person team" in piece for piece in pieces
    )
    assert not mashed_together
    claim = clean_claim(mashed)
    assert 24 <= len(claim) <= 220
    assert "Two-person team closed" not in claim


def test_score_boosts_pricing_and_recency() -> None:
    settings = ScoringSettings()
    fresh = make_item(item_id="fresh", published_at=NOW)
    old = make_item(
        item_id="old",
        url="https://acme.example/old",
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
        text="Contoso Models acquired a semiconductor company in Austin yesterday.",
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
