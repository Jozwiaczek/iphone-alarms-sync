# iOS Shortcuts Setup

This guide covers setup for all three shortcuts used by iPhone Alarms Sync integration.

## Shortcut 1: Sync Alarms With HA

**Required** - Synchronizes alarm data from iPhone to Home Assistant.

### Import

Scan QR code or open link **on your iPhone/iPad that is synced/integrated with Home Assistant**:

![QR Code](https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=https://www.icloud.com/shortcuts/6e15a1bcd8114d0fa0b27c472c50f91b)

**[Open Shortcut](https://www.icloud.com/shortcuts/6e15a1bcd8114d0fa0b27c472c50f91b)**

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

## Shortcut 2: Emit Alarm Event To HA Template

**Optional** - Reports events from specific alarms (requires alarm_id).

### Import

Scan QR code or open link **on your iPhone/iPad that is synced/integrated with Home Assistant**:

![QR Code](https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=https://www.icloud.com/shortcuts/87b32f4a722b48b18fe68552d482b108)

**[Open Shortcut](https://www.icloud.com/shortcuts/87b32f4a722b48b18fe68552d482b108)**

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
4. Add action: **Run Shortcut** → **"Emit Alarm Event To HA Template"**
5. Enable **"Run Immediately"**
6. Tap **Done**

**Note:** The shortcut will use the alarm that triggered the automation. Make sure the Alarm ID in import questions matches the alarm you want to track.

## Shortcut 3: Emit Device Event To HA Template

**Optional** - Reports events from device-level alarms (Wake-Up, any alarm, or sleep events).

### Import

Scan QR code or open link **on your iPhone/iPad that is synced/integrated with Home Assistant**:

![QR Code](https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=https://www.icloud.com/shortcuts/575cd6dc87664e5d82b708466c64201f)

**[Open Shortcut](https://www.icloud.com/shortcuts/575cd6dc87664e5d82b708466c64201f)**

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
4. Add action: **Run Shortcut** → **"Emit Device Event To HA Template"**
5. Enable **"Run Immediately"**
6. Tap **Done**

**Note:** The shortcut will use the event type configured in import questions. You may want to create separate shortcuts for different event types, or use conditional logic within the shortcut.

## Event Type Mapping

| Shortcut | Event Type | Service | Use Case |
|---------|-----------|---------|----------|
| Emit Alarm Event | 1-3 | `report_alarm_event` | Specific alarm events (needs alarm_id) |
| Emit Device Event | 1-3 | `report_device_event` | Wake-Up alarm events |
| Emit Device Event | 4-6 | `report_device_event` | Any alarm events |
| Emit Device Event | 7-9 | `report_device_event` | Sleep events (Bedtime, Waking Up, Wind Down) |

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
- For Alarm Event shortcut: verify Alarm ID is correct
- Test manually: Shortcuts app → Run the event shortcut

### Import doesn't work

- Link must be opened on iOS device
- Try opening in Safari if other browsers fail
