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

## Sample briefing (live extractive run)

Unmodified output of `shipwatch --no-llm run --since 14d` against the
bundled source pack on **11 Oct 2026, 02:18 UTC**. Fetched **26 sources,
all HTTP 200** (the optional Gemini docs sitemap stayed disabled so a
first-run “every unseen URL is new” flood did not drown the window).
CLI log: `examples/live-run.txt`. Claims were not edited.

```
fetched 26 sources · 503 items (705 new)
21 claims · 21 supported · 0 flagged · 0 dropped · coverage 100%
```

```markdown
# Shipwatch briefing — 27 Sep 2026 – 11 Oct 2026

Window: `14d` · mode: `heuristic` · generated 2026-10-11 02:18 UTC

Every bullet cites a source item. Flagged claims did not fully match the source text.

## Vercel: How Rillet ships 3× faster with AI agents on Vercel · score 0.99

- Rillet on Vercel Tripled shipping rate in three months with eve agents deployed on Vercel Two-person team closed 800+ Linear tickets in its first 4 months Builder access via Enterprise Managed Users, SSO, and Directory Sync Ships customer-requested changes to production in as little as two hours Gives every builder access to models through AI Gateway Rillet is an AI-native enterprise resource planning (ERP) platform. ([Vercel](https://vercel.com/blog/how-rillet-ships-3-faster-with-ai-agents-on-vercel))

## Vercel: Step 5 Preview now available on AI Gateway · score 0.98

- Step 5 Preview , StepFun's flagship model, is now available on AI Gateway . ([Vercel](https://vercel.com/changelog/step-5-preview-now-available-on-ai-gateway))
- Rerank 3 and Rerank 3 Lite from Voyage AI by MongoDB are now available on AI Gateway. ([Vercel](https://vercel.com/changelog/voyage-rerank-3-and-rerank-3-lite-are-now-available-on-ai-gateway))
- Ling 3.1 Flash from InclusionAI is now available on AI Gateway. ([Vercel](https://vercel.com/changelog/ling-3-1-flash-is-now-available-on-ai-gateway))

## GitHub Changelog: Claude Haiku 5.5 in GitHub Copilot · score 0.95

- Claude Haiku 5.5, Anthropic’s newest lightweight model, is now generally available in GitHub Copilot. ([GitHub Changelog](https://github.blog/changelog/2026-10-07-claude-haiku-5-5-in-github-copilot))
- Local sandboxing for GitHub Copilot is now generally available in GitHub Copilot CLI, the GitHub Copilot app, and VS Code sessions using Agent Host. ([GitHub Changelog](https://github.blog/changelog/2026-10-07-local-sandboxing-for-github-copilot-now-generally-available))

## OpenAI API Changelog: August, 2026 · score 0.94

- Mutual TLS (mTLS) and X.509 workload identity federation are now generally available for the OpenAI API. ([OpenAI API Changelog](https://developers.openai.com/api/docs/guides/mutual-tls))

## Vercel: Agents can now buy domains with the Vercel CLI · score 0.94

- Your agent can now use the Vercel CLI to buy a domain. ([Vercel](https://vercel.com/changelog/agents-can-now-buy-domains-with-the-vercel-cli))

## GitHub Changelog: Copilot code review: New organization billing options and controls · score 0.93

- This release adds new billing and license controls for Copilot code review admins: Billing: Organization owners can bill Copilot code reviews from members with a Copilot license to the organization’s cost center instead of using up those members’ Copilot quotas. ([GitHub Changelog](https://github.blog/changelog/2026-10-08-copilot-code-review-new-organization-billing-options-and-controls))
- This update brings more control over default models and MCP server in GitHub Copilot for JetBrains. ([GitHub Changelog](https://github.blog/changelog/2026-10-10-new-controls-and-chat-improvements-in-copilot-for-jetbrains))
- This week’s updates make Copilot easier to use across accounts and environments, with more control over what agents can access and how you manage their work. ([GitHub Changelog](https://github.blog/changelog/2026-10-09-github-copilot-weekly-releases-october-5))

## Cloudflare Blog: Introducing Clef-omni with full multimodality, plus a faster Clef and a cheaper Clef-flash · score 0.90

- Following last week’s release of Clef and Clef-flash , Cloudflare’s open-weight decision models, we decided to bring forth more gifts. ([Cloudflare Blog](https://blog.cloudflare.com/clef-faster-cheaper-multimodal))

## Pinecone Release Notes: ​ Cohere Rerank 4.0 Fast is generally available, and cohere-rerank-3.5 is deprecated · score 0.90

- Through August 30, 2026 : cohere-rerank-3.5 continues to serve requests as before. ([Pinecone Release Notes](https://docs.pinecone.io/release-notes/2026#cohere-rerank-4-0-fast-is-generally-available-and-cohere-rerank-3-5-is-deprecated))

## Gemini API Changelog: August 13, 2026 · score 0.90

- Gemini 3.7 Flash generally available (GA) : Released our most intelligent workhorse model yet for coding and agents: Gemini 3.7 Flash ( gemini-3.7-flash ): Substantial improvements across software engineering, web development, and agentic workflows, available at an introductory price through December 31, 2026. ([Gemini API Changelog](https://ai.google.dev/gemini-api/docs/models/gemini-3.7-flash))
- Gemini 3.8 Flash generally available (GA) : Released gemini-3.8-flash , our most intelligent Flash model, engineered for long-horizon software engineering, autonomous agents, and complex enterprise workflows. ([Gemini API Changelog](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash))
- Agentic video understanding : Released agentic video understanding for Gemini 3.7 Flash, 3.6 Flash, and 3.5 Flash-Lite across the Interactions and GenerateContent APIs. ([Gemini API Changelog](https://ai.google.dev/gemini-api/docs/video-understanding#agentic-video-understanding))

## Gemini API Changelog: July 21, 2026 · score 0.90

- Gemini 3.6 Flash and Gemini 3.5 Flash-Lite generally available (GA) : Released stable, production-ready versions of our latest 3.x Flash models: Gemini 3.6 Flash ( gemini-3.6-flash ): Features improved token efficiency and code/agentic planning capabilities at a lower price point than 3.5 Flash, resolving developer feedback around output verbosity. ([Gemini API Changelog](https://ai.google.dev/gemini-api/docs/latest-model))

## Vercel: AI Gateway adds Browserbase Search and Fetch tools · score 0.89

- Browserbase Search and Fetch are now available through AI Gateway . ([Vercel](https://vercel.com/changelog/ai-gateway-adds-browserbase-search-and-fetch-tools))
- Grok Imagine Video 1.5 Lite from xAI is now available on AI Gateway. ([Vercel](https://vercel.com/changelog/grok-imagine-video-1-5-lite-on-ai-gateway))
- Nano Banana 2.1 from Google is now available on AI Gateway as google/gemini-nano-banana-2.1 . ([Vercel](https://vercel.com/changelog/nano-banana-2-1-now-available-on-ai-gateway))

## Pinecone Release Notes: ​ Released Python SDK v10.0.0 · score 0.89

- pinecone.preview is removed. ([Pinecone Release Notes](https://docs.pinecone.io/release-notes/2026#released-python-sdk-v10-0-0))

---

**Grounding:** 21 claims · 21 supported · 0 flagged · 0 dropped · coverage 100%
```

JSON, HTML, and RSS copies live in `examples/`. Test fixtures in
`tests/fixtures/` use invented companies (Acme AI, Contoso Models) so CI
never invents news about real vendors.

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
