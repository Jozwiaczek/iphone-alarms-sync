# iOS Shortcuts Setup

This guide covers setup for all three shortcuts used by iPhone Alarms Sync integration.

## Shortcut 1: Sync Alarms With HA

**Required** - Synchronizes alarm data from iPhone to Home Assistant.

### Import

Scan QR code or open link **on your iPhone/iPad that is synced/integrated with Home Assistant**:

![QR Code](https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=https://www.icloud.com/shortcuts/6789fb4017904ef1aa6dda8d9c89eaa8)

**[Open Shortcut](https://www.icloud.com/shortcuts/6789fb4017904ef1aa6dda8d9c89eaa8)**

### Import Questions

When importing, you'll be asked:
- **Enter Phone ID**: Enter your Phone ID from Home Assistant
  - Find it in: Settings → Devices & Services → iPhone Alarms Sync → Configure → Sync Shortcut Setup

### Personal Automation

1. Open **Shortcuts** app → **Automation** tab
2. Tap **+** → **Personal Automation**
3. Select **App** → **Clock** → **Is Closed**
4. Add action: **Run Shortcut** → **"Sync Alarms With HA"**
5. Enable **"Run Immediately"**
6. Tap **Done**

Alarms sync automatically when you close the Clock app.

## Shortcut 2: Emit Device HA Event

**Optional** - Reports events from device-level alarms (Wake-Up, any alarm, or sleep events).

### Import

Scan QR code or open link **on your iPhone/iPad that is synced/integrated with Home Assistant**:

![QR Code](https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=https://www.icloud.com/shortcuts/206dbfe4dce1495e8989ce12b5f4955d)

**[Open Shortcut](https://www.icloud.com/shortcuts/206dbfe4dce1495e8989ce12b5f4955d)**

### Import Questions

When importing, you'll be asked:
- **Enter Phone ID**: Enter your Phone ID (same as in Sync shortcut)
- **Enter Event Type Number**: Choose from:
  - `1` = Wake-Up Goes Off
  - `2` = Wake-Up Snoozed
  - `3` = Wake-Up Stopped
  - `4` = Any Alarm Goes Off
  - `5` = Any Alarm Snoozed
  - `6` = Any Alarm Stopped
  - `7` = Bedtime Starts
  - `8` = Waking Up
  - `9` = Wind Down Starts

### Personal Automation

1. Open **Shortcuts** app → **Automation** tab
2. Tap **+** → **Personal Automation**
3. Choose trigger:
   - **Alarm** → **When Alarm Goes Off** (any alarm or Wake-Up)
   - **Sleep** → **When Bedtime Starts** / **When Waking Up** / **When Wind Down Starts**
4. Add action: **Run Shortcut** → **"Emit Device HA Event"**
5. Enable **"Run Immediately"**
6. Tap **Done**

**Note:** The shortcut will use the event type configured in import questions. You may want to create separate shortcuts for different event types, or use conditional logic within the shortcut.

## Shortcut 3: Emit Alarm HA Event

**Optional** - Reports events from specific alarms (requires alarm_id).

### Import

Scan QR code or open link **on your iPhone/iPad that is synced/integrated with Home Assistant**:

![QR Code](https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=https://www.icloud.com/shortcuts/5112bf576239414f91d626b10dd9f2e2)

**[Open Shortcut](https://www.icloud.com/shortcuts/5112bf576239414f91d626b10dd9f2e2)**

### Import Questions

When importing, you'll be asked:
- **Enter Phone ID**: Enter your Phone ID (same as in Sync shortcut)
- **Enter Event Type Number**: Choose:
  - `1` = Goes Off
  - `2` = Snoozed
  - `3` = Stopped
- **Enter Alarm ID**: Enter the alarm UUID
  - Find alarm IDs in: Settings → Devices & Services → iPhone Alarms Sync → Configure → Event Shortcuts Setup

### Personal Automation

1. Open **Shortcuts** app → **Automation** tab
2. Tap **+** → **Personal Automation**
3. Choose trigger:
   - **Alarm** → **When Alarm Goes Off** (specific alarm)
   - Or use **When Alarm Goes Off** with alarm selection
4. Add action: **Run Shortcut** → **"Emit Alarm HA Event"**
5. Enable **"Run Immediately"**
6. Tap **Done**

**Note:** The shortcut will use the alarm that triggered the automation. Make sure the Alarm ID in import questions matches the alarm you want to track.

## Event Type Mapping

| Shortcut | Event Type | Service | Use Case |
|---------|-----------|---------|----------|
| Emit Device HA Event | 1-3 | `report_device_event` | Wake-Up alarm events |
| Emit Device HA Event | 4-6 | `report_device_event` | Any alarm events |
| Emit Device HA Event | 7-9 | `report_device_event` | Sleep events (Bedtime, Waking Up, Wind Down) |
| Emit Alarm HA Event | 1-3 | `report_alarm_event` | Specific alarm events (needs alarm_id) |

## Troubleshooting

### Shortcut doesn't run

- iOS Settings → Shortcuts → Advanced → Enable "Allow Running Automations"
- Check automation has "Run Immediately" enabled

### Alarms not syncing

- Verify Phone ID matches in shortcut and Home Assistant
- Test manually: Shortcuts app → Run "Sync Alarms With HA"

### Events not appearing

- Verify Phone ID matches in all shortcuts
- Check event type number matches your use case
- For Alarm HA Event shortcut: verify Alarm ID is correct
- Test manually: Shortcuts app → Run the event shortcut

### Import doesn't work

- Link must be opened on iOS device
- Try opening in Safari if other browsers fail
