"""Markdown, JSON, RSS, and a minimal static HTML page."""

from __future__ import annotations

import json
from datetime import timezone
from email.utils import format_datetime
from html import escape
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring

from shipwatch.models import Briefing, Claim, ClaimCoverage, Item


def coverage_line(coverage: ClaimCoverage) -> str:
    ratio = f"{coverage.coverage_ratio:.0%}" if coverage.total_claims else "n/a"
    return (
        f"{coverage.total_claims} claims · {coverage.supported} supported · "
        f"{coverage.flagged} flagged · {coverage.dropped} dropped · coverage {ratio}"
    )


def render_markdown(briefing: Briefing, items: list[Item]) -> str:
    by_id = {i.id: i for i in items}
    lines = [
        f"# {briefing.title}",
        "",
        f"Window: `{briefing.since}` · mode: `{briefing.mode}` · generated "
        f"{briefing.generated_at.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "Every bullet cites a source item. Flagged claims did not fully match the source text.",
        "",
    ]
    if briefing.notes:
        for note in briefing.notes:
            lines.extend([f"> {note}", ""])
    if not briefing.sections:
        lines.append("_No material stories in this window._")
        lines.append("")
    for section in briefing.sections:
        lines.append(f"## {section.heading} · score {section.score:.2f}")
        lines.append("")
        if not section.claims:
            lines.append("_No grounded claims remained after verification._")
            lines.append("")
            continue
        for claim in section.claims:
            flag = " *(flagged)*" if claim.status == "flagged" else ""
            cites = _cite_md(claim, by_id)
            lines.append(f"- {claim.text}{flag} {cites}")
        lines.append("")
    lines.extend(
        [
            "---",
            "",
            f"**Grounding:** {coverage_line(briefing.coverage)}",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def render_json(briefing: Briefing, items: list[Item]) -> str:
    by_id = {i.id: i for i in items}
    payload = briefing.model_dump(mode="json")
    payload["coverage"]["coverage_ratio"] = briefing.coverage.coverage_ratio
    payload["sources"] = [
        {
            "id": item.id,
            "source_id": item.source_id,
            "source_name": item.source_name,
            "url": item.url,
            "title": item.title,
            "kind": item.kind.value,
            "score": item.score,
        }
        for item in (by_id[i] for i in briefing.selected_item_ids if i in by_id)
    ]
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def render_rss(briefings: list[Briefing], items: list[Item], *, feed_url: str = "") -> str:
    by_id = {i.id: i for i in items}
    rss = Element("rss", attrib={"version": "2.0"})
    channel = SubElement(rss, "channel")
    SubElement(channel, "title").text = "Shipwatch briefings"
    SubElement(channel, "link").text = feed_url or "https://github.com/andymccutcheon/shipwatch"
    SubElement(
        channel, "description"
    ).text = "Cited, scored briefings of what AI companies shipped."
    SubElement(channel, "generator").text = "shipwatch"
    for briefing in briefings:
        item = SubElement(channel, "item")
        SubElement(item, "title").text = briefing.title
        SubElement(item, "guid", attrib={"isPermaLink": "false"}).text = briefing.id
        SubElement(item, "pubDate").text = format_datetime(briefing.generated_at)
        md = render_markdown(briefing, list(by_id.values()))
        SubElement(item, "description").text = md
    return tostring(rss, encoding="unicode") + "\n"


def render_html(briefing: Briefing, items: list[Item]) -> str:
    by_id = {i.id: i for i in items}
    blocks: list[str] = []
    for section in briefing.sections:
        claims_html = "".join(_claim_li(claim, by_id) for claim in section.claims)
        blocks.append(
            f"<section><h2>{escape(section.heading)} "
            f"<small>score {section.score:.2f}</small></h2><ul>{claims_html}</ul></section>"
        )
    body = "\n".join(blocks) or "<p>No material stories in this window.</p>"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(briefing.title)}</title>
  <style>
    body {{ font-family: Georgia, serif; max-width: 720px; margin: 2rem auto;
           padding: 0 1rem; line-height: 1.5; }}
    h1 {{ font-size: 1.6rem; }}
    h2 {{ font-size: 1.15rem; margin-top: 1.8rem; }}
    small {{ color: #555; font-weight: normal; }}
    .meta {{ color: #444; }}
    .flag {{ color: #8a4b08; }}
    footer {{ margin-top: 2rem; border-top: 1px solid #ddd; padding-top: 1rem; color: #444; }}
    a {{ color: #0b57d0; }}
  </style>
</head>
<body>
  <h1>{escape(briefing.title)}</h1>
  <p class="meta">Window <code>{escape(briefing.since)}</code>
     · mode <code>{escape(briefing.mode)}</code></p>
  {body}
  <footer>Grounding: {escape(coverage_line(briefing.coverage))}</footer>
</body>
</html>
"""


def write_outputs(
    briefing: Briefing,
    items: list[Item],
    output_dir: Path,
    *,
    html: bool = False,
    archive: list[Briefing] | None = None,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written = [
        _write(output_dir / "briefing.md", render_markdown(briefing, items)),
        _write(output_dir / "briefing.json", render_json(briefing, items)),
        _write(
            output_dir / "briefings.xml",
            render_rss(archive or [briefing], items),
        ),
    ]
    if html:
        written.append(_write(output_dir / "index.html", render_html(briefing, items)))
    return written


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def _cite_md(claim: Claim, items: dict[str, Item]) -> str:
    parts: list[str] = []
    for item_id in claim.source_item_ids:
        item = items.get(item_id)
        if item:
            parts.append(f"[{item.source_name}]({item.url})")
        else:
            parts.append(f"`{item_id}`")
    return "(" + ", ".join(parts) + ")" if parts else ""


def _claim_li(claim: Claim, items: dict[str, Item]) -> str:
    cites = []
    for item_id in claim.source_item_ids:
        item = items.get(item_id)
        if item:
            cites.append(f'<a href="{escape(item.url)}">{escape(item.source_name)}</a>')
    flag = ' <span class="flag">(flagged)</span>' if claim.status == "flagged" else ""
    suffix = f" ({', '.join(cites)})" if cites else ""
    return f"<li>{escape(claim.text)}{flag}{suffix}</li>"
