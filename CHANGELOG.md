# Changelog

All notable changes to this project are documented here.

## 0.1.0 — 2026-10-11

Initial public release.

- CLI: `init`, `fetch`, `run`, `brief`, `sources check`, `stats`
- Source kinds: RSS/Atom, HTML changelogs, GitHub Releases, docs sitemaps
- Bundled pack of well-known AI and developer-tool changelogs
- Polite HTTP: user agent, robots.txt, ETag/Last-Modified, per-host rate limit
- Pipeline: extract → characterize → dedup → cluster → score → select → synthesize → verify
- `--no-llm` extractive briefing, or OpenAI-compatible JSON with retries
- SQLite archive; Markdown, JSON, RSS, and optional HTML outputs
- Grounding: every claim cites source items; unsupported claims are dropped or flagged
- README sample briefing is `--no-llm` pipeline output from fictional
  fixtures (Acme AI, Contoso Models, …), not live vendor news
- `non_shipment` characterization + configurable penalty so case studies,
  promo, webinars, hiring, and opinion posts rank below real shipments
- Extractive `--no-llm` claims use paragraph/sentence splitting (no mashed cards)
