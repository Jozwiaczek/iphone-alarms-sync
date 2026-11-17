# Agent instructions

Follow [CONTRIBUTING.md](CONTRIBUTING.md). In short:

- Before you call a change done, run `uv run scripts/check.sh` and fix what it reports.
- Commit subjects start with a gitmoji, are at most 72 characters and are written for users (they become changelog lines).
  - Pick the most specific gitmoji from the table in CONTRIBUTING.md → Pull request title, not ✨/🐛/🔧 by default: it decides the bump and is shown in Home Assistant. Preview the notes with `node release/gitmoji.js`.
- User-facing text goes in `custom_components/iphone_alarms_sync/translations/en.json`.
- Keep changes small: no options or abstractions that nobody asked for.
- One pull request per change users get. Pull requests are squash-merged into one changelog line, so open separate pull requests for separate fixes or features instead of one combined one.
- Shortcut templates: see CONTRIBUTING.md → Shortcut templates. On a Mac with the helper shortcut you can do the whole loop: edit, `check`, `build --test-phone-id test`, `install` the test copy, `shortcuts run "<name> (test)"`, `pull` it to compare, then `delete` it.
  - `install` presses **Add Shortcut** itself when Peekaboo has permissions in your shell. If it can't, press **Add Shortcut** (or **Replace**) through accessibility, leaving the import questions empty, or ask the maintainer to.
  - macOS consent dialogs may be invisible to you: if `shortcuts run` waits, ask the maintainer to choose **Always Allow**.
  - Create links, and delete anything except your own test copies, only when the maintainer asks.
