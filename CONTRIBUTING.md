# Contributing

Thanks for helping! Bug reports, ideas and pull requests are welcome.

## Found a bug?

1. Try the [Troubleshooting guide](docs/shortcuts.md#troubleshooting) first: most problems come from the iOS shortcut, not from Home Assistant.
2. Still broken? Open a [bug report](https://github.com/Jozwiaczek/iphone-alarms-sync/issues/new?template=bug_report.yml).

## Have an idea or a question?

- Question about setup: ask in [Discussions](https://github.com/Jozwiaczek/iphone-alarms-sync/discussions/categories/q-a).
- Idea: open a [feature request](https://github.com/Jozwiaczek/iphone-alarms-sync/issues/new?template=feature_request.yml). For a bigger change, agree on it in an issue before you write the code.
- Security problem: see [SECURITY.md](SECURITY.md), not a public issue.

## Want to send a pull request?

You need [uv](https://docs.astral.sh/uv/).

1. Fork the repository and clone your fork.
2. `uv sync` installs Home Assistant and the test tools into `.venv`.
3. Make the change and add a test for the new behavior or the fixed bug.
4. `uv run scripts/check.sh` runs the linter and formatter check (ruff), the type check (mypy), the shortcut template check and the tests. Test coverage must stay at 95% or more; the report lists the lines without tests. To fix formatting: `uv run ruff format custom_components scripts tests`.
5. Try it in a real Home Assistant: copy `custom_components/iphone_alarms_sync` into its `config/custom_components` folder and restart it.
6. Open the pull request against `main` and fill in the template. Add screenshots if something visible changes (setup dialog, entities, options).

Optional: `npm install` (needs Node.js) enables Git hooks that run the checks before each commit and check the commit message.

### What happens next

CI runs the same checks. The maintainer reviews the pull request and squash-merges it once the checks pass. Your change ships in the next beta (`vX.Y.Z-beta.N`), then in the next stable release.

## Code

- The integration lives in `custom_components/iphone_alarms_sync`, the tests in `tests`.
- Texts shown to users are in `translations/en.json`. Entity names and icons use the entity key (`translations/en.json`, `icons.json`).
- Keep it small: no options or abstractions that nobody asked for.

## Pull request title

The pull request is squash-merged, so its title becomes the commit and a line in the changelog. Write it for users, start it with a [gitmoji](https://gitmoji.dev) and keep it at most 72 characters, for example `🐛 Fix next alarm after midnight`. The emoji decides the changelog section and the version bump: ✨ is a minor release, everything else a patch. The maintainer fixes the title on merge if needed.

## Releases

Every push to `main` publishes a beta (`vX.Y.Z-beta.N`). A maintainer publishes the stable release by running the **Release** workflow manually; it collects all changes since the last stable release into `CHANGELOG.md`. Nothing is published unless the checks pass.

## Shortcut templates

For maintainers, on a Mac:

1. Edit the template in `shortcuts/*.plist` and run `python3 scripts/shortcuts.py check` (part of `scripts/check.sh`). To catch your own values, list them one per line in `~/.config/iphone-alarms-sync/private.txt`.
2. `python3 scripts/shortcuts.py build` signs the templates into `dist/`.
3. Open each file, add it with the import questions left empty, then **Share → Copy iCloud Link**.
4. `python3 scripts/shortcuts.py verify <link>…` checks what each link really serves. Only then update the links in `const.py`, the README and the [Shortcuts Setup Guide](docs/shortcuts.md).
