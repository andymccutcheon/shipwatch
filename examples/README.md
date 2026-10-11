# Examples

- `shipwatch.yaml` — default config (`shipwatch init` writes the same file)
- `sources.yaml` — copy of the bundled source pack
- `freewhirr.yaml` / `openrouter.yaml` / `openai.yaml` — LLM endpoint snippets
- `cron.sh` — weekly cron
- `weekly-briefing.yml` — GitHub Actions job (also lives in `.github/workflows/`)
- `briefing.md` / `briefing.json` — extractive briefing generated from the
  recorded test fixtures (not a live fetch)

Regenerate the fixture briefing after changing synthesis or scoring:

```bash
python examples/generate_sample_briefing.py
```
