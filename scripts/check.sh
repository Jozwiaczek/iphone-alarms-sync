#!/bin/sh
# Every check, as run by the pre-commit hook and CI: uv run scripts/check.sh
set -e
cd "$(dirname "$0")/.."

ruff check custom_components scripts tests
ruff format --check custom_components scripts tests
mypy custom_components/iphone_alarms_sync
python scripts/shortcuts.py check
pytest -q --cov=custom_components.iphone_alarms_sync --cov-report=term-missing:skip-covered --cov-fail-under=95
# JavaScript: the release notes and the dashboard card. CI runs these in pr.yml,
# where the npm packages are installed.
if [ -d node_modules ]; then node --test release/ tests/frontend/; else echo "Skipping JS tests: run npm ci"; fi
