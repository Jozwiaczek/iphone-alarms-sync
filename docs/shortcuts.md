# iOS Shortcuts Setup

This guide covers setup for all three shortcuts used by iPhone Alarms Sync integration.

## Shortcut 1: Sync

**Required** - Synchronizes alarm data from iPhone to Home Assistant.

### Import

Scan QR code or open link **on your iPhone/iPad that is synced/integrated with Home Assistant**:

![QR Code](https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=https://www.icloud.com/shortcuts/3a7ef812167b410f8b429de5bb07587e)

**[Open Shortcut](https://www.icloud.com/shortcuts/3a7ef812167b410f8b429de5bb07587e)**

### Import Questions

When importing, you'll be asked:
- **Enter Phone ID**: Enter your Phone ID from Home Assistant
  - Find it in: Settings → Devices & Services → iPhone Alarms Sync → Configure → Sync Shortcut Setup
- **Home Wi-Fi** (optional): fill in only if Home Assistant works just at home. Use the exact name. On any other network, the shortcut stops.
- **Server** and **Action**: pick your Home Assistant server, then `iphone_alarms_sync.sync_alarms` (search for `iphone_alarms_sync`).

### Personal Automation

1. Open **Shortcuts** app → **Automation** tab
2. Tap **+** → **Personal Automation**
3. Select **App** → **Clock** → **Is Closed**
4. Add action: **Run Shortcut** → **"iPhone Alarms Sync: Sync"**
5. Enable **"Run Immediately"**
6. Tap **Done**

Alarms sync automatically when you close the Clock app.

## Shortcut 2: Device Event

**Optional** - Reports events from device-level alarms (Wake-Up, any alarm, or sleep events).

### Import

Scan QR code or open link **on your iPhone/iPad that is synced/integrated with Home Assistant**:

![QR Code](https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=https://www.icloud.com/shortcuts/af592e425fd04cdbb4835f96f35ed793)

**[Open Shortcut](https://www.icloud.com/shortcuts/af592e425fd04cdbb4835f96f35ed793)**

### Import Questions

When importing, you'll be asked:
- **Enter Phone ID**: Enter your Phone ID (same as in Sync shortcut)
- **Home Wi-Fi** (optional): as in Sync.
- **Enter Event Type Number**: Choose from:
  - `1` = Any Alarm Goes Off
  - `2` = Any Alarm Snoozed
  - `3` = Any Alarm Stopped
  - `4` = Wake-Up Goes Off
  - `5` = Wake-Up Snoozed
  - `6` = Wake-Up Stopped
  - `7` = Waking Up
  - `8` = Wind Down Starts
  - `9` = Bedtime Starts
- **Server** and **Action**: pick your Home Assistant server, then `iphone_alarms_sync.report_device_event`.

### Personal Automation

1. Open **Shortcuts** app → **Automation** tab
2. Tap **+** → **Personal Automation**
3. Choose trigger:
   - **Alarm** → **When Alarm Goes Off** (any alarm or Wake-Up)
   - **Sleep** → **When Bedtime Starts** / **When Waking Up** / **When Wind Down Starts**
4. Add action: **Run Shortcut** → **"iPhone Alarms Sync: Device Event"**
5. Enable **"Run Immediately"**
6. Tap **Done**

**Note:** One copy sends one event. Import it once per event and name each copy, e.g. *iPhone Alarms Sync: Any Alarm Goes Off*.

## Shortcut 3: Alarm Event

**Optional** - Reports events from specific alarms (requires alarm_id).

### Import

Scan QR code or open link **on your iPhone/iPad that is synced/integrated with Home Assistant**:

![QR Code](https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=https://www.icloud.com/shortcuts/0b78900623dd4269a50fc481971ecea5)

**[Open Shortcut](https://www.icloud.com/shortcuts/0b78900623dd4269a50fc481971ecea5)**

### Import Questions

When importing, you'll be asked:
- **Enter Phone ID**: Enter your Phone ID (same as in Sync shortcut)
- **Home Wi-Fi** (optional): as in Sync.
- **Enter Event Type Number**: Choose:
  - `1` = Goes Off
  - `2` = Snoozed
  - `3` = Stopped
- **Enter Alarm ID**: Enter the alarm UUID
  - Find alarm IDs in: Settings → Devices & Services → iPhone Alarms Sync → Configure → Event Shortcuts Setup
- **Server** and **Action**: pick your Home Assistant server, then `iphone_alarms_sync.report_alarm_event`.

### Personal Automation

1. Open **Shortcuts** app → **Automation** tab
2. Tap **+** → **Personal Automation**
3. Choose trigger:
   - **Alarm** → **When Alarm Goes Off** (specific alarm)
   - Or use **When Alarm Goes Off** with alarm selection
4. Add action: **Run Shortcut** → **"iPhone Alarms Sync: Alarm Event"**
5. Enable **"Run Immediately"**
6. Tap **Done**

**Note:** The shortcut will use the alarm that triggered the automation. Make sure the Alarm ID in import questions matches the alarm you want to track.

## Event Type Mapping

| Shortcut | Event Type | Service | Use Case |
|---------|-----------|---------|----------|
| Device Event | 1-3 | `report_device_event` | Any alarm events |
| Device Event | 4-6 | `report_device_event` | Wake-Up alarm events |
| Device Event | 7-9 | `report_device_event` | Sleep events (Waking Up, Wind Down, Bedtime) |
| Alarm Event | 1-3 | `report_alarm_event` | Specific alarm events (needs alarm_id) |

## Privacy

The shared templates contain no personal data: the Phone ID, Alarm ID, Server and Action fields are empty and filled in by the import questions. Server identifiers are different on every device, so always pick the **Server** and the **Action** when importing, otherwise the shortcut shows **Choose** or fails with *No server provided*.

The templates are built from the files in [`shortcuts/`](../shortcuts), so you can read exactly what each one does. Never share a shortcut from your own library: it contains your Phone ID and server name.

## Maintaining the templates

For maintainers, on a Mac:

1. Edit the template in `shortcuts/*.plist` and run `python3 scripts/shortcuts.py check` (CI runs it too). To catch your own values, list them one per line in `~/.config/iphone-alarms-sync/private.txt`.
2. `python3 scripts/shortcuts.py build` signs the templates into `dist/`.
3. Open each file, add it with the import questions left empty, then **Share → Copy iCloud Link**.
4. `python3 scripts/shortcuts.py verify <link>…` checks what each link really serves. Only then update the links in `const.py`, the README and this guide.

## Troubleshooting

### How it works

Each iOS Personal Automation runs a shortcut. The shortcut builds a **Dictionary** and passes it to the **Perform action** step of the Home Assistant app, which calls an `iphone_alarms_sync.*` action in Home Assistant. An update to iOS, the Shortcuts app or the Home Assistant app can break this chain without any error in Home Assistant. When a phone sends nothing for 7 days, Home Assistant shows a repair issue in **Settings → System → Repairs**.

| Shortcut | Action to pick in **Perform action** | Dictionary keys |
|---|---|---|
| Sync | `iphone_alarms_sync.sync_alarms` | `phone_id`, `alarms` (list of objects with `alarm_id`, `label`, `enabled`, `hour`, `minute`, `repeats`, `repeat_days`, `allows_snooze`) |
| Device Event | `iphone_alarms_sync.report_device_event` | `phone_id`, `event` (`wakeup_goes_off`, `wakeup_snoozed`, `wakeup_stopped`, `any_goes_off`, `any_snoozed`, `any_stopped`, `bedtime_starts`, `waking_up`, `wind_down_starts`) |
| Alarm Event | `iphone_alarms_sync.report_alarm_event` | `phone_id`, `alarm_id`, `event` (`goes_off`, `snoozed`, `stopped`) |

If Home Assistant rejects the data (unknown Phone ID, invalid event, malformed alarms), the shortcut shows the error when you run it.

### Perform action shows "Choose" or "No server provided"

Home Assistant app 2026.9 replaced the old *Call service* shortcut action with *Perform action*. Shortcuts made from the old templates (named *Sync Alarms With HA*, *Emit Device HA Event* and *Emit Alarm HA Event*) kept the server and the data but lost the selected action, so they stopped sending anything. To fix it:

1. Update the Home Assistant app to 2026.9.3 or newer.
2. Open each shortcut, tap **Choose** in the **Perform action** step and pick the action from the table above. This keeps your automations working.
3. If the app has more than one server, pick the **Server** first, then the action. A shortcut saved with a server from another device (for example synced through iCloud from an iPad or Mac) fails with *No server provided* until you pick both again on this device.
4. Run each shortcut manually once and check that the **Last Sync** sensor (or the event sensor) updates.

You can instead import the new templates from the links above. They are named *iPhone Alarms Sync: …* and already have the action set. Point your automations to the new shortcuts, then delete the old ones.

### "Timed out after 10 seconds"

The Home Assistant app (2026.10.1+) waits 10 s for Home Assistant. The phone must reach it then, also when locked. Using a VPN? Make sure it reconnects after your home IP changes.

### Alarm Event Missed

The **Alarm Event Missed** sensor turns on when an alarm rings and no *Goes Off* event arrives within 5 minutes. It turns off when the phone sends data. It works after the first *Goes Off* event.

It may also turn on if you changed the alarm outside the Clock app, travelled across time zones, or the phone was off or away from your **Home Wi-Fi**.

To get a notification, add an automation:

```yaml
triggers:
  - trigger: state
    entity_id: binary_sensor.<phone>_alarm_event_missed
    to: "on"
# Home Assistant works just at home? Add a condition that the phone is home.
actions:
  - action: notify.mobile_app_<phone>
    data:
      message: "Alarm event didn't reach Home Assistant."
```

### Debug logs

Add this to `configuration.yaml` and restart Home Assistant:

```yaml
logger:
  logs:
    custom_components.iphone_alarms_sync: debug
```

Every call from a shortcut then logs `<action> called for phone_id=...`. No log line means the call never reached Home Assistant: check the shortcut.

### Shortcut doesn't run

- iOS Settings → Shortcuts → Advanced → Enable "Allow Running Automations"
- Check automation has "Run Immediately" enabled

### Alarms not syncing

- Verify Phone ID matches in shortcut and Home Assistant
- Test manually: Shortcuts app → Run "iPhone Alarms Sync: Sync"
- Check the **Last Sync** sensor: it updates on every successful sync

### Events not appearing

- Verify Phone ID matches in all shortcuts
- Check event type number matches your use case
- For the Alarm Event shortcut: verify Alarm ID is correct
- Test manually: Shortcuts app → Run the event shortcut

### Import doesn't work

- Link must be opened on iOS device
- Try opening in Safari if other browsers fail
