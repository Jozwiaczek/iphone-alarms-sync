# Agent instructions

Follow [CONTRIBUTING.md](CONTRIBUTING.md). In short:

- Before you call a change done, run `uv run scripts/check.sh` and fix what it reports.
- Commit subjects start with a gitmoji, are at most 72 characters and are written for users (they become changelog lines).
- User-facing text goes in `custom_components/iphone_alarms_sync/translations/en.json`.
- Keep changes small: no options or abstractions that nobody asked for.
