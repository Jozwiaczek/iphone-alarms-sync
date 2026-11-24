# iOS Shortcuts Setup

This guide covers setup for all three shortcuts used by iPhone Alarms Sync integration.

## Shortcut 1: Sync

**Required** - Synchronizes alarm data from iPhone to Home Assistant.

### Import

Scan QR code or open link **on your iPhone, iPad or Mac that is synced/integrated with Home Assistant**:

![QR Code](https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=https://www.icloud.com/shortcuts/f8015b2fa07f4c4cbab8126816137ff5)

**[Open Shortcut](https://www.icloud.com/shortcuts/f8015b2fa07f4c4cbab8126816137ff5)**

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

Siri, Control Center and the Watch change alarms without opening Clock. To catch those too, add a second automation: **Time of Day** → daily → **Run Shortcut** → **"iPhone Alarms Sync: Sync"** → **Run Immediately**. It also stops the *no data* repair on a phone whose alarms never change.

### Estimated goes off

With the Sync shortcut alone, each alarm fires **Goes off** in Home Assistant at its scheduled time. No event shortcut is needed. The event is marked `estimated: true`.

Know its limits:

1. Only *goes off*. Snoozed and stopped need the event shortcuts.
2. It uses the last sync. A change made by Siri, Control Center or the Watch is unknown until the next sync.
3. It fires even when the device is off, asleep (a Mac), away from home or in another time zone. Add a condition such as "I am home" to your automation if that matters.
4. It does not fire when Home Assistant is not running at that minute.
5. The ring after a snooze is not estimated. Neither is an alarm without a device in Home Assistant, such as the Sleep Wake-Up alarm or an alarm set on the Watch.

Each alarm has an **Estimated goes off** switch. It is on by default, unless the phone already reported *goes off* through a shortcut before. When the Alarm Event shortcut of an alarm reports *Goes off*, the switch turns off by itself and the real event takes over.

## Shortcut 2: Device Event

**Optional** - Reports events from device-level alarms (Wake-Up, any alarm, or sleep events).

### Import

Scan QR code or open link **on your iPhone, iPad or Mac that is synced/integrated with Home Assistant**:

![QR Code](https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=https://www.icloud.com/shortcuts/1024bb19477e425e9f0ae8a8a04dfa7c)

**[Open Shortcut](https://www.icloud.com/shortcuts/1024bb19477e425e9f0ae8a8a04dfa7c)**

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

Scan QR code or open link **on your iPhone, iPad or Mac that is synced/integrated with Home Assistant**:

![QR Code](https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=https://www.icloud.com/shortcuts/c200af1ee622472aa45fd037c24ad0e7)

**[Open Shortcut](https://www.icloud.com/shortcuts/c200af1ee622472aa45fd037c24ad0e7)**

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
   - **Alarm** → **Goes Off**, **Is Snoozed** or **Is Stopped**, then pick the alarm
4. Add action: **Run Shortcut** → **"iPhone Alarms Sync: Alarm Event"**
5. Enable **"Run Immediately"**
6. Tap **Done**

**Note:** The shortcut reports the alarm whose ID you entered, not the one that rang. Pick the same alarm in the automation. One copy sends one event of one alarm.

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

Maintainers: see [Shortcut templates](../CONTRIBUTING.md#shortcut-templates) for how the templates are built and published.

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
4. Run each shortcut manually once and check that the **Last sync** sensor (or the event sensor) updates.

You can instead import the new templates from the links above. They are named *iPhone Alarms Sync: …* and already have the action set. Point your automations to the new shortcuts, then delete the old ones.

### Shortcut stops silently with Home Wi-Fi left empty

Shortcuts imported before the fix for [#20](https://github.com/Jozwiaczek/iphone-alarms-sync/issues/20) stop right after the Wi-Fi check when **Home Wi-Fi** is empty: no error, no share prompt, nothing in Home Assistant. Import the shortcuts again from the links above. Or, if you don't use Home Wi-Fi, open the shortcut and delete the steps from the first **If** to its **End If**.

### "Timed out after 10 seconds"

The Home Assistant app (2026.10.1+) waits 10 s for Home Assistant. The phone must reach it then, also when locked. Using a VPN? Make sure it reconnects after your home IP changes.

The same lost connection can also show *XPC error received on message reply handler*.

Shortcuts can't catch this error, so don't run **Perform action** without a connection. If your shortcut runs a helper shortcut first (for example to reconnect a VPN), **Stop This Shortcut** in the helper stops only the helper. Return a result with **Stop and Output** and stop the calling shortcut when it reports a failure.

### Alarm event missed

The **Alarm event missed** sensor turns on when an alarm rings and no *Goes Off* event arrives within 5 minutes. It turns off when the phone sends data. It works after the first *Goes Off* event.

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

### Download diagnostics

**Settings → Devices & services → iPhone Alarms Sync → ⋮ → Download diagnostics** saves the phone's alarms, the last sync time and the last 20 events to a file. Attach it to a bug report after you look through it: it contains your phone name and alarm labels.

### Shortcut doesn't run

- iOS Settings → Shortcuts → Advanced → Enable "Allow Running Automations"
- Check automation has "Run Immediately" enabled

### Alarms not syncing

- Verify Phone ID matches in shortcut and Home Assistant. Renaming the phone in **Edit Device** can change it: enter the new Phone ID in all three shortcuts
- Test manually: Shortcuts app → Run "iPhone Alarms Sync: Sync"
- Check the **Last sync** sensor: it updates on every successful sync

### Events not appearing

- Verify Phone ID matches in all shortcuts
- Check event type number matches your use case
- For the Alarm Event shortcut: verify Alarm ID is correct
- Test manually: Shortcuts app → Run the event shortcut

### Import doesn't work

- Open the link on the iPhone, iPad or Mac itself
- Try opening in Safari if other browsers fail
