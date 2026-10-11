# Contributing to shipwatch

Thanks for helping keep the briefing honest.

## Setup

Python 3.10+ is required.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Do not put a real `SHIPWATCH_API_KEY`, `OPENROUTER_API_KEY`, or `OPENAI_API_KEY`
in the repository, in fixtures, or in CI. The test suite uses recorded fixtures
and must stay green without a key and without the public internet.

## Checks

Run the same checks CI runs:

```bash
ruff check src tests examples
ruff format src tests examples
pytest
```

CI is GitHub Actions (`.github/workflows/ci.yml`) on Python 3.10 and 3.12: lint,
format, then pytest. No live fetches.

## Design notes

- Import, CLI, and PyPI name are all `shipwatch`.
- Fetch parsers stay pure: bytes in, `RawItem` list out. HTTP lives in
  `shipwatch.fetch.client`.
- Scoring knobs belong in config. Grounding belongs in `pipeline.verify`.
  Persistence belongs in `shipwatch.storage`.
- Prefer a recorded fixture over hitting the network.
- Config is env vars + YAML. Do not add an external service.

## Releasing

Maintainers: see [RELEASING.md](RELEASING.md). Publishing is Trusted
Publishing only — do not add a PyPI API token to GitHub secrets.

## Pull requests

- Small, focused diffs with a short rationale.
- Update the README when you change user-facing behavior (CLI, scoring, env vars).
- Never commit `.env`, SQLite archives, or API keys.
