# iOS Shortcuts

This directory should contain template `.shortcut` files for import into iOS Shortcuts app.

## Required Shortcuts

1. **Sync All Alarms.shortcut**
   - Trigger: Personal Automation → "App" → "Clock" → "Is Closed"
   - Action: HA Companion App → "Call Service" → `iphone_alarms_sync.sync_alarms`
   - Payload: Dictionary with `phone_id` and `alarms` array

2. **Alarm Goes Off.shortcut**
   - Trigger: Personal Automation → "Alarm" → "Goes Off"
   - Action: HA Companion App → "Call Service" → `iphone_alarms_sync.report_alarm_event`
   - Payload: `{ phone_id, alarm_id, event: "goes_off" }`

3. **Alarm Snoozed.shortcut**
   - Trigger: Personal Automation → "Alarm" → "Is Snoozed"
   - Action: HA Companion App → "Call Service" → `iphone_alarms_sync.report_alarm_event`
   - Payload: `{ phone_id, alarm_id, event: "snoozed" }`

4. **Alarm Stopped.shortcut**
   - Trigger: Personal Automation → "Alarm" → "Is Stopped"
   - Action: HA Companion App → "Call Service" → `iphone_alarms_sync.report_alarm_event`
   - Payload: `{ phone_id, alarm_id, event: "stopped" }`

## Creating Shortcuts

Shortcuts must be created in the iOS Shortcuts app and exported as `.shortcut` files.
These files are binary and cannot be created as text files.

Users should:
1. Create shortcuts in iOS Shortcuts app
2. Share/export as `.shortcut` files
3. Import into this repository or share via iCloud links

