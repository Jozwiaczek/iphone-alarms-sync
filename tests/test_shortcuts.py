"""The Home Wi-Fi gate at the start of each shortcut template."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))  # shortcuts.py imports bridge.py
_spec = importlib.util.spec_from_file_location(
    "shortcuts_script", ROOT / "scripts/shortcuts.py"
)
assert _spec and _spec.loader
shortcuts = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(shortcuts)

# Conditions whose meaning in Shortcuts is certain. "has any value" (100) is
# not: an empty Text passes it (issue #20), so it is rejected here.
CONDITIONS = {
    2: lambda a, b: float(a) > float(b),
    4: lambda a, b: str(a) == str(b),
    5: lambda a, b: str(a) != str(b),
}


def _value(outputs: dict[str, Any], token: dict) -> Any:
    """Resolve a variable or a text with one variable in it."""
    token = token.get("Variable", token)  # an If input wraps the variable
    if token["WFSerializationType"] == "WFTextTokenAttachment":
        return outputs[token["Value"]["OutputUUID"]]
    value = token["Value"]
    (attachment,) = value["attachmentsByRange"].values()
    assert value["string"] == "￼", "only one-variable texts are modelled"
    return outputs[attachment["OutputUUID"]]


def _mode(action: dict) -> int | None:
    return action.get("WFWorkflowActionParameters", {}).get("WFControlFlowMode")


def _next(actions: list, i: int, group: str, modes: set[int]) -> int:
    """Index of the next step of this If group in one of these modes."""
    return next(
        j
        for j in range(i + 1, len(actions))
        if actions[j].get("WFWorkflowActionParameters", {}).get("GroupingIdentifier")
        == group
        and _mode(actions[j]) in modes
    )


def run_gate(wf: dict, home_wifi: str, network: str) -> str:
    """Run the steps up to the Home Assistant step: "ha" or "stop"."""
    actions = wf["WFWorkflowActions"]
    outputs: dict[str, Any] = {}
    depth = 0
    i = 0
    while i < len(actions):
        kind = actions[i]["WFWorkflowActionIdentifier"]
        p = actions[i].get("WFWorkflowActionParameters", {})
        if kind == shortcuts.HA_ACTION:
            return "ha"
        if kind == "is.workflow.actions.exit":
            return "stop"
        if kind == "is.workflow.actions.gettext" and i == 0:
            outputs[p["UUID"]] = home_wifi  # the answer to the import question
        elif kind == "is.workflow.actions.count":
            assert p["WFCountType"] == "Characters"
            outputs[p["UUID"]] = len(str(_value(outputs, p["Input"])))
        elif kind == "is.workflow.actions.getwifi":
            assert p["WFWiFiDetail"] == "Network Name"
            outputs[p["UUID"]] = network
        elif kind == "is.workflow.actions.conditional":
            mode, group = p["WFControlFlowMode"], p["GroupingIdentifier"]
            if mode == 0:
                condition = p["WFCondition"]
                assert condition in CONDITIONS, (
                    f"step {i}: Shortcuts condition {condition} has no known "
                    "meaning for empty text, use Count and a number check"
                )
                operand = (
                    p["WFNumberValue"]
                    if "WFNumberValue" in p
                    else _value(outputs, p["WFConditionalActionString"])
                )
                depth += 1
                if not CONDITIONS[condition](_value(outputs, p["WFInput"]), operand):
                    i = _next(actions, i, group, {1, 2})  # Otherwise or End If
                    if _mode(actions[i]) == 2:
                        depth -= 1
            elif mode == 1:  # the If branch ran, skip Otherwise
                i = _next(actions, i, group, {2})
                depth -= 1
            else:
                depth -= 1
        elif depth == 0:
            return "ha"  # past the gate; later steps are not modelled
        else:
            raise AssertionError(f"step {i}: {kind} inside the Wi-Fi gate")
        i += 1
    raise AssertionError("no Home Assistant step")


@pytest.mark.parametrize("slug", sorted(shortcuts.TEMPLATES))
@pytest.mark.parametrize(
    ("home_wifi", "network", "expected"),
    [
        ("", "Any Network", "ha"),
        ("Home", "Home", "ha"),
        ("Home", "Cafe", "stop"),
    ],
    ids=["empty", "home", "elsewhere"],
)
def test_home_wifi_gate(slug: str, home_wifi: str, network: str, expected: str) -> None:
    """An empty Home Wi-Fi skips the check; a set one stops elsewhere."""
    assert run_gate(shortcuts.load(slug), home_wifi, network) == expected


def test_has_any_value_gate_is_rejected() -> None:
    """The gate from issue #20 fails both the test model and the check."""
    wf = shortcuts.load("sync")
    for action in wf["WFWorkflowActions"]:
        p = action.get("WFWorkflowActionParameters", {})
        if p.get("WFCondition") == 2:
            p["WFCondition"] = 100
            del p["WFNumberValue"]
            break
    with pytest.raises(AssertionError, match="no known meaning"):
        run_gate(wf, "", "Any Network")
    assert any(
        "value checks pass empty text" in e for e in shortcuts.check(wf, "sync_alarms")
    )
