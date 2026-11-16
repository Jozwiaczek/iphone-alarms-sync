"""The "iPhone Alarms Sync: Bridge" helper shortcut; `shortcuts.py build` signs it.

Input "op|name|arg". After finding the shortcuts named name, one op runs:
export (output the file), link (iCloud link to the clipboard), delete,
rename (to arg), unfile (out of its folder), mkfolder (create folder name).
"""

import uuid


def uid(key: str) -> str:
    # Stable ids: the same source always signs into the same shortcut.
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"ias-bridge/{key}")).upper()


def att(value: dict) -> dict:
    return {"Value": value, "WFSerializationType": "WFTextTokenAttachment"}


def output(name: str, key: str) -> dict:
    return {"OutputName": name, "OutputUUID": uid(key), "Type": "ActionOutput"}


def token(value: dict) -> dict:
    return {
        "Value": {"attachmentsByRange": {"{0, 1}": value}, "string": "￼"},
        "WFSerializationType": "WFTextTokenString",
    }


def text(s: str) -> dict:
    return {
        "Value": {"attachmentsByRange": {}, "string": s},
        "WFSerializationType": "WFTextTokenString",
    }


MATCH = att({"Type": "Variable", "VariableName": "Match"})
REPEAT_ITEM = {"Type": "Variable", "VariableName": "Repeat Item"}


def step(ident: str, **params) -> dict:
    return {"WFWorkflowActionIdentifier": ident, "WFWorkflowActionParameters": params}


def intent(action: str, key: str, **params) -> dict:
    descriptor = {
        "BundleIdentifier": "com.apple.shortcuts",
        "Name": "Shortcuts",
        "TeamIdentifier": "0000000000",
        "AppIntentIdentifier": action,
    }
    return step(
        f"com.apple.shortcuts.{action}",
        AppIntentDescriptor=descriptor,
        UUID=uid(key),
        **params,
    )


def item(key: str, name: str, **where) -> dict:
    return step(
        "is.workflow.actions.getitemfromlist",
        UUID=uid(key),
        CustomOutputName=name,
        WFInput=att(output("Split Text", "split")),
        **where,
    )


def when(op: str, body: list[dict]) -> list[dict]:
    group = uid(f"if-{op}")
    start = step(
        "is.workflow.actions.conditional",
        GroupingIdentifier=group,
        WFControlFlowMode=0,
        WFCondition=4,
        WFInput={"Type": "Variable", "Variable": att(output("Op", "op"))},
        WFConditionalActionString=text(op),
    )
    end = step(
        "is.workflow.actions.conditional",
        GroupingIdentifier=group,
        WFControlFlowMode=2,
    )
    return [start, *body, end]


ARG = att(output("Arg", "arg"))
lookup = [
    step(
        "is.workflow.actions.text.split",
        UUID=uid("split"),
        text=att({"Type": "ExtensionInput"}),
        WFTextSeparator="Custom",
        WFTextCustomSeparator="|",
    ),
    item("op", "Op", WFItemSpecifier="First Item"),
    item("name", "Name", WFItemSpecifier="Item At Index", WFItemIndex=2),
    item("arg", "Arg", WFItemSpecifier="Last Item"),
    step("is.workflow.actions.getmyworkflows", UUID=uid("all")),
    step(
        "is.workflow.actions.repeat.each",
        GroupingIdentifier=uid("each"),
        WFControlFlowMode=0,
        WFInput=att(output("My Shortcuts", "all")),
    ),
    step(
        "is.workflow.actions.gettext",
        UUID=uid("item-name"),
        CustomOutputName="Item Name",
        WFTextActionText=token(REPEAT_ITEM),
    ),
    step(
        "is.workflow.actions.conditional",
        GroupingIdentifier=uid("same"),
        WFControlFlowMode=0,
        WFCondition=4,
        WFInput={"Type": "Variable", "Variable": att(output("Item Name", "item-name"))},
        WFConditionalActionString=token(output("Name", "name")),
    ),
    step(
        "is.workflow.actions.appendvariable",
        WFVariableName="Match",
        WFInput=att(REPEAT_ITEM),
    ),
    step(
        "is.workflow.actions.conditional",
        GroupingIdentifier=uid("same"),
        WFControlFlowMode=2,
    ),
    step(
        "is.workflow.actions.repeat.each",
        GroupingIdentifier=uid("each"),
        WFControlFlowMode=2,
    ),
]
ops = {
    "export": [step("is.workflow.actions.output", WFOutput=token(MATCH["Value"]))],
    "link": [
        intent("CreateShortcutiCloudLinkAction", "link", shortcut=MATCH),
        step(
            "is.workflow.actions.setclipboard",
            WFInput=att(output("iCloud Link", "link")),
        ),
    ],
    "delete": [intent("DeleteWorkflowAction", "delete", entities=MATCH)],
    "rename": [
        intent(
            "RenameShortcutAction", "rename", shortcut=MATCH, name=token(ARG["Value"])
        )
    ],
    # Without a folder, Move takes the shortcut out of its folder.
    "unfile": [intent("MoveShortcutToFolderAction", "unfile", shortcuts=MATCH)],
    "mkfolder": [
        intent("CreateFolderAction", "mkfolder", name=token(output("Name", "name")))
    ],
}

workflow = {
    "WFWorkflowActions": lookup
    + [s for op, body in ops.items() for s in when(op, body)],
    "WFWorkflowClientVersion": "4046.0.2.1.102",
    "WFWorkflowMinimumClientVersion": 2025,
    "WFWorkflowMinimumClientVersionString": "2025",
    "WFWorkflowIcon": {
        "WFWorkflowIconGlyphNumber": 59649,
        "WFWorkflowIconStartColor": 255,
    },
    "WFWorkflowImportQuestions": [],
    "WFWorkflowInputContentItemClasses": ["WFStringContentItem"],
    "WFWorkflowOutputContentItemClasses": [],
    "WFWorkflowHasOutputFallback": False,
    "WFWorkflowHasShortcutInputVariables": True,
    "WFWorkflowTypes": [],
    "WFQuickActionSurfaces": [],
}
