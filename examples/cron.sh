#!/bin/sh
# Weekly Monday 9:00 local. Point at a checkout that already ran `shipwatch init`.
# 0 9 * * 1 /path/to/examples/cron.sh
set -eu
cd /path/to/your/shipwatch-project
. .venv/bin/activate
shipwatch --no-llm run --since 7d --out briefs --html
