# Contributing

Thanks for helping! Bug reports, ideas and pull requests are welcome.

## Report a bug or suggest a feature

Use the [issue forms](https://github.com/Jozwiaczek/iphone-alarms-sync/issues/new/choose). For a bug, first try the [Troubleshooting guide](docs/shortcuts.md#troubleshooting): most problems come from the iOS shortcut, not from Home Assistant.

## Set up

You need [uv](https://docs.astral.sh/uv/) and Node.js (only for the commit message hook).

```bash
uv sync
npm install
```

`uv sync` installs Home Assistant and the test tools into `.venv`. `npm install` enables the Git hooks.

## Check your change

```bash
uv run scripts/check.sh
```

It runs the linter and formatter check (ruff), the type check (mypy), the shortcut template check and the tests. The pre-commit hook and CI run the same script. To fix formatting: `uv run ruff format custom_components scripts tests`.

To try the integration in a real Home Assistant, copy `custom_components/iphone_alarms_sync` into its `config/custom_components` folder and restart it.

## Code

- The integration lives in `custom_components/iphone_alarms_sync`, the tests in `tests`.
- Texts shown to users are in `translations/en.json`. Entity names and icons use the entity key (`translations/en.json`, `icons.json`).
- Add a test for a new behavior or a fixed bug.
- Keep it small: no options or abstractions that nobody asked for.

## Commits and pull requests

- A commit subject starts with a [gitmoji](https://gitmoji.dev) and is at most 72 characters, for example `🐛 Fix next alarm after midnight`. The emoji decides the changelog section and the version bump: ✨ is a minor release, everything else a patch. The commit-msg hook checks the format.
- Write the subject for users: it becomes a line in the changelog.
- Open the pull request against `main`. It is merged when the checks pass.

## Releases

Every push to `main` publishes a beta (`vX.Y.Z-beta.N`). A maintainer publishes the stable release by running the **Release** workflow manually; it collects all changes since the last stable release into `CHANGELOG.md`. Nothing is published unless the checks pass.

## Shortcut templates

For maintainers, on a Mac:

1. Edit the template in `shortcuts/*.plist` and run `python3 scripts/shortcuts.py check` (part of `scripts/check.sh`). To catch your own values, list them one per line in `~/.config/iphone-alarms-sync/private.txt`.
2. `python3 scripts/shortcuts.py build` signs the templates into `dist/`.
3. Open each file, add it with the import questions left empty, then **Share → Copy iCloud Link**.
4. `python3 scripts/shortcuts.py verify <link>…` checks what each link really serves. Only then update the links in `const.py`, the README and the [Shortcuts Setup Guide](docs/shortcuts.md).
