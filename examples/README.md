# Examples

- `shipwatch.yaml` — default config (`shipwatch init` writes the same file)
- `sources.yaml` — copy of the bundled source pack
- `freewhirr.yaml` / `openrouter.yaml` / `openai.yaml` — LLM endpoint snippets
- `cron.sh` — weekly cron
- `weekly-briefing.yml` — GitHub Actions job (also lives in `.github/workflows/`)
- `briefing.md` / `briefing.json` / `briefings.xml` / `index.html` — **live**
  extractive briefing from `shipwatch --no-llm run --since 14d` on
  2026-10-11 02:18 UTC. Claims were not edited. See `live-run.txt` for
  the fetch log and grounding line.

CI fixtures are fictional (Acme AI, Contoso Models, …) and live under
`tests/fixtures/`. Do not copy them into this folder.
