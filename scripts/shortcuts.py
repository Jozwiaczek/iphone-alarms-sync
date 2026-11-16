#!/usr/bin/env python3
"""Check, build and verify the iOS shortcut templates in shortcuts/.

check   validate the sources (runs in CI)
build   sign the templates and the bridge into dist/ (macOS only)
verify  check what an iCloud link really serves

On a Mac with the bridge shortcut (scripts/bridge.py) installed:
install   add a .shortcut file, pressing its buttons with Peekaboo if installed
pull      save an installed shortcut as a plist
link      create the iCloud link of an installed, clean template and verify it
delete    delete an installed shortcut, keeping a copy in dist/deleted/
rename    rename an installed shortcut
move      move an installed shortcut into a folder
unfile    take an installed shortcut out of its folder
mkfolder  create a folder
"""

import argparse
import base64
import json
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import bridge

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
    questions = wf.get("WFWorkflowImportQuestions", [])
    ha_index = actions.index(ha[0])
    # Server ids are per installation, so the user picks both at import.
    ha_asked = {q["ParameterKey"] for q in questions if q["ActionIndex"] == ha_index}
    if ha_asked != {"server", "action"}:
        errors.append("Home Assistant step needs server and action questions")
    # Sharing drops asked fields; the source keeps a placeholder for test copies.
    server = params.get("server")
    action = params.get("action")
    if server is not None and (
        server.get("identifier") != SERVER_ID
        or server.get("title", {}).get("key") != SERVER_NAME
    ):
        errors.append(f"server must be the placeholder {SERVER_NAME!r}")
    if action is not None and (
        action.get("identifier") != f"{SERVER_ID}::{DOMAIN}.{service}"
    ):
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
    for q in questions:
        i, key = q["ActionIndex"], q["ParameterKey"]
        if i == ha_index:
            continue
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

    # Local-only setups stop the shortcut away from the home Wi-Fi.
    ids = [a["WFWorkflowActionIdentifier"] for a in actions]
    first = actions[0].get("WFWorkflowActionParameters", {})
    if first.get("CustomOutputName") != "Home Wi-Fi" or 0 not in asked:
        errors.append("first step must be the asked, empty Home Wi-Fi text")
    if "is.workflow.actions.exit" not in ids[:ha_index]:
        errors.append("Home Wi-Fi check must stop the shortcut before Home Assistant")

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
        wf = load(slug)
        errors = check(wf, service)
        ha = next(
            a
            for a in wf["WFWorkflowActions"]
            if a["WFWorkflowActionIdentifier"] == HA_ACTION
        )
        if not {"server", "action"} <= ha["WFWorkflowActionParameters"].keys():
            errors.append("source needs the placeholder server and action")
        failed |= bool(errors)
        print(f"{slug}: {'; '.join(errors) or 'ok'}")
    # A step reading a missing step's output breaks only when run on the Mac.
    steps = {
        a["WFWorkflowActionParameters"].get("UUID")
        for a in bridge.workflow["WFWorkflowActions"]
    }
    refs = set(re.findall(r'"OutputUUID": "([^"]+)"', json.dumps(bridge.workflow)))
    print(f"bridge: {'unknown step outputs' if refs - steps else 'ok'}")
    return int(failed or bool(refs - steps))


def cmd_build(args) -> int:
    if cmd_check(args):
        return 1
    DIST.mkdir(exist_ok=True)
    built = [("bridge", BRIDGE, bridge.workflow)]
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
        built.append((slug, name, wf))
    for slug, name, wf in built:
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


BY_NAME = {name: (slug, service) for slug, (name, service) in TEMPLATES.items()}


def source_errors(wf: dict, slug: str) -> list[str]:
    """Differences between a shared or installed shortcut and its source."""
    errors = []
    src = load(slug)
    ids = [a["WFWorkflowActionIdentifier"] for a in wf["WFWorkflowActions"]]
    if ids != [a["WFWorkflowActionIdentifier"] for a in src["WFWorkflowActions"]]:
        errors.append("steps differ from the source")
    questions = wf.get("WFWorkflowImportQuestions")
    if questions != src.get("WFWorkflowImportQuestions"):
        errors.append("import questions differ from the source")
    return errors


def cmd_verify(args) -> int:
    failed = False
    for url in args.urls:
        record_id = url.rstrip("/").rsplit("/", 1)[-1]
        api = f"https://www.icloud.com/shortcuts/api/records/{record_id}"
        fields = json.loads(fetch(api))["fields"]
        name = fields["name"]["value"]
        if name not in BY_NAME:
            print(f"{url}: unexpected name {name!r}")
            failed = True
            continue
        slug, service = BY_NAME[name]
        wf = plistlib.loads(fetch(fields["shortcut"]["value"]["downloadURL"]))
        errors = check(wf, service) + source_errors(wf, slug)
        failed |= bool(errors)
        print(f"{name}: {'; '.join(errors) or 'ok'}")
    return int(failed)


BRIDGE = "iPhone Alarms Sync: Bridge"
# DER header of a P-256 public key; the bridge's exports carry only the raw key.
P256_SPKI = "3059301306072a8648ce3d020106082a8648ce3d030107034200"


def installed_count(name: str) -> int:
    listed = subprocess.run(
        ["shortcuts", "list"], capture_output=True, text=True, check=True
    ).stdout.splitlines()
    # The bridge may match names ignoring case, so count them that way.
    return [n.lower() for n in listed].count(name.lower())


def one_installed(name: str) -> None:
    if (count := installed_count(name)) != 1:
        raise SystemExit(f"{name!r}: {count} installed, need exactly 1")


def run_bridge(op: str, name: str, arg: str = "") -> bytes:
    """Run one bridge operation on exactly one installed shortcut."""
    if "|" in name + arg:  # the bridge splits its input on "|"
        raise SystemExit(f"{name!r} {arg!r}: names with | are not supported")
    if op != "mkfolder":
        one_installed(name)
    with tempfile.TemporaryDirectory() as tmp:
        inp, out = Path(tmp, "in.txt"), Path(tmp, "out")
        inp.write_text(f"{op}|{name}|{arg}")
        # First runs of a new bridge wait for "Always Allow" on the Mac.
        subprocess.run(
            ["shortcuts", "run", BRIDGE, "-i", inp, "-o", out], check=True, timeout=300
        )
        return out.read_bytes() if out.exists() else b""


def unwrap(signed: bytes) -> dict:
    """Workflow plist inside a .shortcut exported by the bridge."""
    size = int.from_bytes(signed[8:12], "little")
    key = plistlib.loads(signed[12 : 12 + size])["SigningPublicKey"]
    pem = base64.encodebytes(bytes.fromhex(P256_SPKI) + key).decode()
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        (t / "in").write_bytes(signed)
        (t / "key.pem").write_text(
            f"-----BEGIN PUBLIC KEY-----\n{pem}-----END PUBLIC KEY-----\n"
        )
        subprocess.run(
            ["aea", "decrypt", "-i", t / "in", "-o", t / "a.aar"]
            + ["-sign-pub", t / "key.pem"],
            check=True,
        )
        subprocess.run(["aa", "extract", "-i", t / "a.aar", "-d", t], check=True)
        return plistlib.loads((t / "Shortcut.wflow").read_bytes())


def cmd_pull(args) -> int:
    data = plistlib.dumps(unwrap(run_bridge("export", args.name)))
    if args.output:
        Path(args.output).write_bytes(data)
    else:
        sys.stdout.write(data.decode())
    return 0


def cmd_link(args) -> int:
    if args.name not in BY_NAME:
        raise SystemExit(f"only templates get public links: {sorted(BY_NAME)}")
    slug, service = BY_NAME[args.name]
    # Links are public and can't be withdrawn: share only a clean template.
    wf = unwrap(run_bridge("export", args.name))
    if errors := check(wf, service) + source_errors(wf, slug):
        print(f"{args.name}: {'; '.join(errors)}")
        return 1
    # An old link left on the clipboard must not pass for the new one.
    subprocess.run(["pbcopy"], input=b"", check=True)
    run_bridge("link", args.name)
    # The bridge leaves the link on the clipboard as a URL.
    raw = subprocess.run(
        ["osascript", "-e", "the clipboard as «class url »"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    url = bytes.fromhex(raw.split()[-1].rstrip("»")).decode()
    print(url)
    record = url.rstrip("/").rsplit("/", 1)[-1]
    api = f"https://www.icloud.com/shortcuts/api/records/{record}"
    if (name := json.loads(fetch(api))["fields"]["name"]["value"]) != args.name:
        print(f"{url}: link is for {name!r}")
        return 1
    return cmd_verify(argparse.Namespace(urls=[url]))


def cmd_delete(args) -> int:
    if args.name.lower() == BRIDGE.lower():
        raise SystemExit("the bridge does not delete itself")
    # Deleting syncs to every device; keep a copy that `open` imports back.
    data = run_bridge("export", args.name)
    if not data:
        raise SystemExit(f"{args.name!r}: export returned nothing, not deleting")
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = DIST / "deleted" / f"{args.name.replace('/', '_')} {stamp}.shortcut"
    backup.parent.mkdir(parents=True, exist_ok=True)
    backup.write_bytes(data)
    run_bridge("delete", args.name)
    print(f"deleted, backup: {backup}")
    return 0


def cmd_rename(args) -> int:
    if BRIDGE.lower() in (args.name.lower(), args.new_name.lower()):
        raise SystemExit("leave the bridge's name alone")
    if installed_count(args.new_name):
        raise SystemExit(f"{args.new_name!r} is taken")
    run_bridge("rename", args.name, args.new_name)
    return 0


def cmd_move(args) -> int:
    one_installed(args.name)
    # The bridge's Move needs a picked folder; AppleScript takes a name.
    script = (
        'on run {s, f}\ntell application "Shortcuts Events"\n'
        "set folder of (first shortcut whose name is s) to "
        "(first folder whose name is f)\nend tell\nend run"
    )
    subprocess.run(["osascript", "-e", script, args.name, args.folder], check=True)
    return 0


def ids() -> set[str]:
    return set(
        subprocess.run(
            ["shortcuts", "list", "--show-identifiers"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
    )


def cmd_install(args) -> int:
    name = Path(args.file).stem  # Shortcuts names the import after the file
    before = ids()
    subprocess.run(["open", args.file], check=True)
    if not shutil.which("peekaboo"):
        print("Press Add Shortcut in the Shortcuts window.")
        return 0
    # Add Shortcut, then Add Shortcut again after import questions, or Replace.
    for _ in range(5):
        time.sleep(1)
        pids = subprocess.run(["pgrep", "-x", "Shortcuts"], capture_output=True)
        if not pids.stdout:
            continue  # the app is still starting
        # A bare "Shortcuts" also matches the shortcuts CLI; the Peekaboo
        # bridge has no Accessibility, so use the caller's own permissions.
        target = ["--app", f"PID:{pids.stdout.split()[0].decode()}", "--no-remote"]
        subprocess.run(["peekaboo", "see", *target, "--json"], capture_output=True)
        for button in ("Replace", "Add Shortcut"):
            click = ["peekaboo", "click", button, *target, "--wait-for", "0"]
            if subprocess.run(click, capture_output=True).returncode == 0:
                break
        time.sleep(1)
        # Each import gets a new identifier, even when it replaces one.
        if added := [line for line in ids() - before if name in line]:
            print(f"added {added[0]}")
            if installed_count(name) > 1:
                print("the older copy gets a new name (… 1): delete it")
            return 0
    print(f"{name!r} not added: check the Shortcuts window and Peekaboo's permissions")
    return 1


def cmd_op(args) -> int:
    """unfile and mkfolder: one bridge step, nothing to guard."""
    run_bridge(args.op, args.name)
    return 0


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
    install = sub.add_parser("install")
    install.add_argument("file")
    install.set_defaults(func=cmd_install)
    pull = sub.add_parser("pull")
    pull.add_argument("name")
    pull.add_argument("-o", "--output", help="file to write, default stdout")
    pull.set_defaults(func=cmd_pull)
    for name, func, extra in (
        ("link", cmd_link, None),
        ("delete", cmd_delete, None),
        ("rename", cmd_rename, "new_name"),
        ("move", cmd_move, "folder"),
        ("unfile", cmd_op, None),
        ("mkfolder", cmd_op, None),
    ):
        p = sub.add_parser(name)
        p.add_argument("name")
        if extra:
            p.add_argument(extra)
        p.set_defaults(func=func, op=name)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
