#!/usr/bin/env python3
"""Check, build and verify the iOS shortcut templates in shortcuts/.

check   validate the sources (runs in CI)
build   sign the templates into dist/ (macOS only)
verify  check what an iCloud link really serves
"""

import argparse
import json
import plistlib
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "shortcuts"
DIST = ROOT / "dist"
SERVICES = ROOT / "custom_components/iphone_alarms_sync/services.yaml"
DOMAIN = "iphone_alarms_sync"
HA_ACTION = "io.robbie.HomeAssistant.CallServiceIntent"
# No real server in a template: the HA app (2026.9.3+) maps an unknown one
# to the only server set up.
SERVER_ID = "0" * 32
SERVER_NAME = "Home Assistant"
# Local list of your own values that must never be published, one per line.
PRIVATE = Path.home() / ".config/iphone-alarms-sync/private.txt"

TEMPLATES = {
    "sync": ("iPhone Alarms Sync: Sync", "sync_alarms"),
    "device_event": ("iPhone Alarms Sync: Device Event", "report_device_event"),
    "alarm_event": ("iPhone Alarms Sync: Alarm Event", "report_alarm_event"),
}

LEAKS = {
    "hex id": re.compile(r"\b(?!0{32}\b)[0-9a-f]{32}\b", re.I),
    "e-mail": re.compile(r"[\w.+-]+@[\w-]+\.\w+"),
    "IP address": re.compile(r"(?<![\d.])\d{1,3}(?:\.\d{1,3}){3}(?![\d.])"),
    "web URL": re.compile(r"https?://"),
    "shortcut reference": re.compile(r"workflowIdentifier"),
}


def service_events() -> dict[str, set[str]]:
    """Event options per service, read from services.yaml."""
    events: dict[str, set[str]] = {}
    service = None
    for line in SERVICES.read_text().splitlines():
        if m := re.match(r"^(\w+):\s*$", line):
            service = m.group(1)
            events[service] = set()
        elif service and (m := re.match(r"^\s+- (\w+)\s*$", line)):
            events[service].add(m.group(1))
    return events


def strings(obj):
    """Every string in a shortcut, including nested binary plists."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield str(key)
            yield from strings(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from strings(value)
    elif isinstance(obj, bytes):
        try:
            yield from strings(plistlib.loads(obj))
        except Exception:
            yield obj.decode("latin-1")
    elif isinstance(obj, str):
        yield obj


def check(wf: dict, service: str) -> list[str]:
    errors = []
    actions = wf["WFWorkflowActions"]
    events = service_events()
    if service not in events:
        errors.append(f"service {service} is not in services.yaml")

    ha = [a for a in actions if a["WFWorkflowActionIdentifier"] == HA_ACTION]
    if len(ha) != 1:
        return [*errors, f"expected 1 Home Assistant step, found {len(ha)}"]
    params = ha[0]["WFWorkflowActionParameters"]
    server = params.get("server", {})
    action = params.get("action", {})
    if server.get("identifier") != SERVER_ID:
        errors.append("server must be the placeholder id")
    if server.get("title", {}).get("key") != SERVER_NAME:
        errors.append(f"server name must be {SERVER_NAME!r}")
    if action.get("identifier") != f"{SERVER_ID}::{DOMAIN}.{service}":
        errors.append(f"action must be {DOMAIN}.{service} on the placeholder")
    if params.get("service") != f"{DOMAIN}.{service}":
        errors.append(f"service must be {DOMAIN}.{service}")

    for a in actions:
        p = a.get("WFWorkflowActionParameters", {})
        if p.get("CustomOutputName") == "Event Types":
            items = p["WFItems"]["Value"]["WFDictionaryFieldValueItems"]
            values = {i["WFValue"]["Value"]["string"] for i in items}
            if unknown := values - events.get(service, set()):
                errors.append(f"unknown events {sorted(unknown)}")

    asked = set()
    for q in wf.get("WFWorkflowImportQuestions", []):
        i, key = q["ActionIndex"], q["ParameterKey"]
        asked.add(i)
        value = actions[i].get("WFWorkflowActionParameters", {}).get(key)
        if value is None:
            errors.append(f"import question {q['Text']!r} points to no field")
        elif value != q.get("DefaultValue", ""):
            errors.append(f"import question {q['Text']!r} field must be empty")
    for i, a in enumerate(actions):
        if a["WFWorkflowActionIdentifier"] == "is.workflow.actions.gettext":
            if i not in asked:
                errors.append(f"text step {i} has no import question")

    private = []
    if PRIVATE.exists():
        private = [s for s in PRIVATE.read_text().splitlines() if s.strip()]
    for text in strings(wf):
        for name, pattern in LEAKS.items():
            if pattern.search(text):
                errors.append(f"{name} in {text[:60]!r}")
        for value in private:
            if value.lower() in text.lower():
                errors.append(f"private value {value[:3]}… found")
    return errors


def load(slug: str) -> dict:
    with (SRC / f"{slug}.plist").open("rb") as f:
        return plistlib.load(f)


def cmd_check(_args) -> int:
    failed = False
    for slug, (_name, service) in TEMPLATES.items():
        errors = check(load(slug), service)
        failed |= bool(errors)
        print(f"{slug}: {'; '.join(errors) or 'ok'}")
    return int(failed)


def cmd_build(args) -> int:
    if cmd_check(args):
        return 1
    DIST.mkdir(exist_ok=True)
    for slug, (name, _service) in TEMPLATES.items():
        wf = load(slug)
        if args.test_phone_id:
            # Throwaway copy that HA rejects: tests the app without side effects.
            name += " (test)"
            for a in wf["WFWorkflowActions"]:
                p = a.get("WFWorkflowActionParameters", {})
                if p.get("CustomOutputName") == "Device ID":
                    p["WFTextActionText"] = args.test_phone_id
            wf["WFWorkflowImportQuestions"] = []
        unsigned = DIST / f"{slug}.unsigned.shortcut"
        unsigned.write_bytes(plistlib.dumps(wf, fmt=plistlib.FMT_BINARY))
        out = DIST / f"{name}.shortcut"
        subprocess.run(
            ["shortcuts", "sign", "--mode", "anyone", "-i", unsigned, "-o", out],
            check=True,
        )
        unsigned.unlink()
        print(out)
    return 0


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read()


def cmd_verify(args) -> int:
    by_name = {name: (slug, service) for slug, (name, service) in TEMPLATES.items()}
    failed = False
    for url in args.urls:
        record_id = url.rstrip("/").rsplit("/", 1)[-1]
        api = f"https://www.icloud.com/shortcuts/api/records/{record_id}"
        fields = json.loads(fetch(api))["fields"]
        name = fields["name"]["value"]
        if name not in by_name:
            print(f"{url}: unexpected name {name!r}")
            failed = True
            continue
        slug, service = by_name[name]
        wf = plistlib.loads(fetch(fields["shortcut"]["value"]["downloadURL"]))
        errors = check(wf, service)
        src = load(slug)
        ids = [a["WFWorkflowActionIdentifier"] for a in wf["WFWorkflowActions"]]
        if ids != [a["WFWorkflowActionIdentifier"] for a in src["WFWorkflowActions"]]:
            errors.append("steps differ from the source")
        questions = wf.get("WFWorkflowImportQuestions")
        if questions != src.get("WFWorkflowImportQuestions"):
            errors.append("import questions differ from the source")
        failed |= bool(errors)
        print(f"{name}: {'; '.join(errors) or 'ok'}")
    return int(failed)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(required=True)
    sub.add_parser("check").set_defaults(func=cmd_check)
    build = sub.add_parser("build")
    build.add_argument("--test-phone-id", help="build test copies with this ID")
    build.set_defaults(func=cmd_build)
    verify = sub.add_parser("verify")
    verify.add_argument("urls", nargs="+")
    verify.set_defaults(func=cmd_verify)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
