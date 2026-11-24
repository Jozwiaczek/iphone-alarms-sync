"""Every translation has the keys and placeholders of en.json.

Home Assistant shows English for a missing key without a warning, and hassfest
doesn't check languages other than English.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

FOLDER = (
    Path(__file__).parent.parent / "custom_components/iphone_alarms_sync/translations"
)
PLACEHOLDER = re.compile(r"\{\w+\}")
OTHERS = sorted(p for p in FOLDER.glob("*.json") if p.name != "en.json")


def _flatten(data: dict, prefix: str = "") -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in data.items():
        if isinstance(value, dict):
            out |= _flatten(value, f"{prefix}{key}.")
        else:
            out[prefix + key] = value
    return out


def _load(path: Path) -> dict[str, str]:
    return _flatten(json.loads(path.read_text(encoding="utf-8")))


@pytest.mark.parametrize("path", OTHERS, ids=lambda p: p.stem)
def test_translation_matches_english(path: Path) -> None:
    english = _load(FOLDER / "en.json")
    other = _load(path)
    assert other.keys() == english.keys()
    for key, text in english.items():
        found = set(PLACEHOLDER.findall(other[key]))
        assert found == set(PLACEHOLDER.findall(text)), key
