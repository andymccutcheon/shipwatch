# shipwatch

**Know what AI companies actually shipped this week.**

Changelogs and release notes go in. A scored briefing comes out, with a
source for every claim.

```text
pip install shipwatch
```

shipwatch is a small, local pipeline for people who write (or just read)
weekly notes on the AI and developer-tool ecosystem. It is a clean-room
open "lite" cousin of a private newsletter research stack: fetch, normalize,
extract, characterize, dedup, cluster, score, brief, then **verify every
sentence against the evidence**.

No hosted service. One SQLite file. Works with `--no-llm`, or with any
OpenAI-compatible endpoint.

## 60-second quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install shipwatch
shipwatch init
shipwatch sources check          # offline validation of the YAML pack
shipwatch --no-llm run --since 7d --html
```

Outputs land in `out/`:

| File | What |
| --- | --- |
| `briefing.md` | Cited Markdown briefing |
| `briefing.json` | Same data, machine-readable |
| `briefings.xml` | RSS of stored briefings |
| `index.html` | Optional static page (`--html`) |

`shipwatch fetch` only updates the archive. `shipwatch brief --since 7d`
re-briefs items already in SQLite. `shipwatch stats` prints counts.

## Sample briefing (from recorded fixtures)

The briefing below is **not** a live crawl. It is the extractive `--no-llm`
output of `examples/generate_sample_briefing.py` against the RSS, HTML,
GitHub, and sitemap fixtures in `tests/fixtures/`. Those fixtures are
shaped like real changelogs and dated in the week of 11 Oct 2026.

```markdown
# Shipwatch briefing — 27 Sep 2026 – 11 Oct 2026

Window: `14d` · mode: `heuristic` · generated 2026-10-11 12:00 UTC

Every bullet cites a source item. Flagged claims did not fully match the source text.

## Anthropic News: Claude ships computer use in the EU · score 1.00

- Anthropic expanded computer use for Claude to customers in the European Union. ([Anthropic News](https://anthropic.example/news#claude-ships-computer-use))

## OpenAI News: OpenAI cuts API prices for GPT-5 mini · score 0.96

- OpenAI announced a 50% price reduction for GPT-5 mini input tokens in the API, effective immediately for all prepaid and monthly billing accounts. ([OpenAI News](https://openai.example/index/gpt-5-mini-price-cut))

## Anthropic News: Legacy Completions API sunset date · score 0.95

- Anthropic will deprecate the legacy Completions API on 15 January 2027. ([Anthropic News](https://anthropic.example/news#legacy-completions-api-sunset-date))

## Gemini docs: New docs page: batch · score 0.85

- New page listed on the Gemini docs sitemap: https://ai.example/gemini-api/docs/batch ([Gemini docs](https://ai.example/gemini-api/docs/batch))

## LangChain: langchain 1.2.0 · score 0.76

- LangChain 1.2.0 adds a stable tool-calling interface and removes the deprecated ConversationalRetrievalChain. ([LangChain](https://github.com/langchain-ai/langchain/releases/tag/v1.2.0))

## OpenAI News: New fine-tuning recipes for structured outputs · score 0.70

- The API now ships official fine-tuning recipes for structured outputs so teams can keep JSON schemas stable across model upgrades. ([OpenAI News](https://openai.example/index/structured-outputs-recipes))

---

**Grounding:** 6 claims · 6 supported · 0 flagged · 0 dropped · coverage 100%
```

Full JSON and HTML live in `examples/`.

## How scoring works

Each item (and then each topic cluster) gets a 0–1 materiality score from
a configurable rubric in `shipwatch.yaml`:

| Signal | Default weight | What it measures |
| --- | --- | --- |
| Novelty | 0.25 | How distinct the title is from other items in the window |
| Impact | 0.30 | Characterization (model release / launch / …) plus keyword cues |
| Breadth | 0.20 | API / enterprise / “all customers” style audience |
| Recency | 0.25 | Exponential decay; default half-life 7 days |

Pricing changes, deprecations, and security items get an extra boost
(defaults 0.15 / 0.15 / 0.10) so a quiet price cut does not lose to a
generic blog post. Tune the weights; do not treat the number as a
universal “importance” unit.

Kinds: `launch`, `model_release`, `pricing_change`, `deprecation`,
`api_change`, `availability`, `security`, `other`.

## How grounding works

This is the product.

1. Synthesis may only emit claims that cite one or more **item ids**.
2. The verifier walks each claim, loads the cited source text, and checks
   content-word overlap.
3. ≥50% overlap → **supported**. 25–49% → **flagged** (kept, marked).
   below that, or a missing citation → **dropped**.
4. The briefing footer reports
   `N claims · supported · flagged · dropped · coverage`.

`--no-llm` is extractive: claims are sentences already in the source, so
they almost always verify. An LLM brief is more readable and more likely
to drift — that is why the verifier runs either way.

No accuracy or quality percentages are published here. None have been
measured on a labeled set. If you add an eval, say what the labels were
and how the score was computed.

## LLM layer (optional)

Default docs point at **[freewhirr](https://github.com/andymccutcheon/freewhirr)**
(`pip install freewhirr`), Andy's free-first OpenRouter router.

```bash
pip install freewhirr
# needs an OpenRouter key only so freewhirr can see the free catalog
export OPENROUTER_API_KEY=...
freewhirr serve --port 8787
```

```bash
export SHIPWATCH_BASE_URL=http://127.0.0.1:8787/v1
export SHIPWATCH_MODEL=freewhirr
export SHIPWATCH_API_KEY=not-used
shipwatch run --since 7d
```

**Cost note:** shipwatch does not bill you. Tokens go to whatever endpoint
you configured. Through freewhirr, that is free OpenRouter models until
you opt into paid fallback in *freewhirr's* config. Direct OpenRouter or
OpenAI is billed by those providers. shipwatch still runs without any of
this via `--no-llm`.

Plain OpenRouter:

```bash
export SHIPWATCH_BASE_URL=https://openrouter.ai/api/v1
export SHIPWATCH_MODEL=meta-llama/llama-3.3-70b-instruct:free
export OPENROUTER_API_KEY=...
```

Plain OpenAI:

```bash
export SHIPWATCH_BASE_URL=https://api.openai.com/v1
export SHIPWATCH_MODEL=gpt-4o-mini
export OPENAI_API_KEY=...
```

Calls use `response_format=json_object`. The client validates the payload
with Pydantic and retries with the validator error. After retries it falls
back to the extractive brief.

## Adding sources

`shipwatch init` copies the bundled pack to `sources.yaml`. Kinds:

| `kind` | Required | Notes |
| --- | --- | --- |
| `rss` | `url` | RSS or Atom (`feedparser`) |
| `html` | `url` | Optional `selector`; else heading-split / readability |
| `github` | `repo` | `owner/name` via the Releases API |
| `sitemap` | `url` | New `loc` values become “new docs page” items |

The shipped pack is ~26 AI and developer-tool changelogs (OpenAI,
Anthropic, Google AI / Gemini, Mistral, Cursor, Vercel, Hugging Face,
LangChain, OpenRouter, LlamaIndex, Groq, Cohere, Pinecone, Replicate,
Cloudflare, Next.js, FastAPI, Pydantic, Supabase, GitHub, xAI, DeepSeek,
Together). Each URL returned HTTP 200 on 2026-10-11 with the shipwatch
user agent. Some HTML marketing pages are JS-rendered and will extract
thinly; prefer RSS or GitHub when a site offers them.

```bash
shipwatch sources check          # schema / URL shape
shipwatch sources check --live   # polite HEAD/GET; not used in CI
```

## Fetch manners

Every request sends
`User-Agent: shipwatch/0.1.0 (+https://github.com/andymccutcheon/shipwatch)`.
Conditional GET uses stored `ETag` / `Last-Modified`. Hosts are paced
(`min_interval_seconds`, default 1s). `robots.txt` is checked unless you
turn it off. GitHub Releases send `GITHUB_TOKEN` when present.

## Scheduling

Cron (see `examples/cron.sh`):

```cron
0 9 * * 1  cd /path/to/project && .venv/bin/shipwatch --no-llm run --since 7d --out briefs
```

A GitHub Actions workflow that runs weekly and commits `briefs/` lives at
`.github/workflows/weekly-briefing.yml`. `examples/weekly-briefing.yml`
shows the same job plus a GitHub Pages sketch.

## Storage

`.shipwatch/shipwatch.db` holds items, facts, clusters, briefings, fetch
state, and sitemap URL history. Nothing else is required.

## CLI

```text
shipwatch init
shipwatch fetch [--source ID]
shipwatch run [--since 7d] [--top 12] [--out DIR] [--html]
shipwatch brief --since 7d
shipwatch sources check [--live]
shipwatch stats
```

`--no-llm` is a global flag.

## Limitations

- HTML extraction loses to client-rendered changelog UIs.
- Heuristic characterization and scoring are keyword-based. They will
  mis-tag some posts.
- Semantic near-dup uses token Jaccard, not embeddings.
- Sitemap mode records new URLs; it does not fetch each new page body.
- The verifier is lexical overlap, not a human editor. Flagged is not
  “wrong”; dropped is “we would not stand behind this sentence.”
- Live source URLs rot. Re-run `sources check --live` when you edit the pack.

## Development

```bash
pip install -e ".[dev]"
ruff check src tests examples
ruff format src tests examples
pytest
python -m build && twine check --strict dist/*
```

See [CONTRIBUTING.md](CONTRIBUTING.md) and [RELEASING.md](RELEASING.md).
Version is single-sourced in `src/shipwatch/_version.py` (`0.1.0`).
Publishing is PyPI Trusted Publishing only.

## License

MIT. © 2026 Andy McCutcheon.
