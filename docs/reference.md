# Reference

Everything iPhone Alarms Sync adds to Home Assistant. For setup, see the [README](../README.md) and the [Shortcuts Setup Guide](shortcuts.md). The dashboard card has its own page: [Dashboard card](dashboard-card.md).

## Entities

**Phone device**

| Entity | Description |
|---|---|
| Next alarm, Next alarm label | Time and label of the next enabled alarm |
| Last alarm | When the last alarm was scheduled to ring |
| Last sync | Last successful run of the Sync shortcut (diagnostic) |
| Enabled / Disabled / Total alarms | Alarm counts |
| Wake-up alarm last went off / snoozed / stopped | Last Wake-Up alarm events (Device Event shortcut) |
| Any alarm last went off / snoozed / stopped | Last events of any alarm (Device Event shortcut) |
| Bedtime last started, Wind down last started, Last woke up | Last sleep events (Device Event shortcut) |
| Alarm event missed | On when an alarm rang but no *Goes Off* event arrived ([details](shortcuts.md#alarm-event-missed)) |

**Alarm device** (one per alarm, named after its label, e.g. *John's iPhone Wake*; an alarm without a label or with a label another alarm has, such as the default *Alarm*, also gets its time, e.g. *John's iPhone 07:00 Alarm*. The name follows the alarm; entity IDs keep the name they were created with)

| Entity | Description |
|---|---|
| Alarm ID | Alarm ID for the Alarm Event shortcut (diagnostic); its attributes hold the alarm's time, label and settings |
| Next occurrence, Last occurrence | Next and last scheduled ring |
| Last went off / snoozed / stopped | Last events of this alarm (Alarm Event shortcut) |
| Enabled, Allows snooze | Alarm state on the phone |
| Repeats, Repeats on Monday … Sunday | Repeat schedule (disabled by default) |
| Estimated goes off | Fires *Goes off* at the alarm's time, without an event shortcut ([limits](shortcuts.md#estimated-goes-off)). Turns itself off when the alarm's shortcut reports *Goes off* |

Event timestamps stay *unknown* until the matching shortcut reports the first event.

## Triggers

The easiest way: add the trigger **Alarm goes off**, **Alarm is snoozed** or **Alarm is stopped** and pick one or more alarms (or an area or label). It fires when any of them rings, so "when *07:00 Wake* or *06:30 Gym* goes off" is one trigger. See the [YAML example](../README.md#-examples).

The alarms you can pick are event entities, named like the iOS automations:

| Device | Event entity | Events | Needs |
|---|---|---|---|
| Alarm | *Alarm* | Goes off, Is snoozed, Is stopped | Sync only for an estimated Goes off; Alarm Event shortcut for the rest |
| Phone | *Any alarm* | Goes off, Is snoozed, Is stopped | Device Event shortcut, events 1-3 |
| Phone | *Wake-Up alarm* | Goes off, Is snoozed, Is stopped | Device Event shortcut, events 4-6 |
| Phone | *Sleep* | Wind Down begins, Bedtime begins, Waking up | Device Event shortcut, events 7-9 |

For sleep events use the built-in **Event received** trigger on the *Sleep* entity. The same events also work as device triggers (pick the phone or alarm device). Phone alarm device triggers saved before 2026-11 still fire for both Any and Wake-Up, but show without a subject in the editor. Pick them again to choose one.

Each reported event also fires `iphone_alarms_sync_alarm_event`, for templates and advanced use:

| Field | Value |
|---|---|
| `phone_id` | Phone ID |
| `alarm_id` | Alarm UUID, or `wakeup`, `any`, `bedtime`, `waking_up`, `wind_down` |
| `event` | `goes_off`, `snoozed`, `stopped`, `bedtime_starts`, `waking_up`, `wind_down_starts` |
| `event_id`, `occurred_at` | Unique ID and UTC time of the event |
| `estimated` | `true` when fired at the alarm's time, `false` when a shortcut reported it. Also an attribute of the event entities |

## Actions

The shortcuts call `iphone_alarms_sync.sync_alarms`, `iphone_alarms_sync.report_device_event` and `iphone_alarms_sync.report_alarm_event`. Their fields are listed in the [Shortcuts Setup Guide](shortcuts.md#how-it-works).

## Options

Settings → Devices & services → iPhone Alarms Sync → **Configure**:

- **Edit Device** - name, linked Mobile App device and **Sync disabled alarms** (off: disabled alarms are not synced and their devices are removed). A new name can give a new **Phone ID**: enter it in every shortcut on the phone.
- **Events History** - the last 20 events since Home Assistant started
- **Sync Shortcut Setup** and **Event Shortcuts Setup** - Phone ID, QR codes and the Alarm IDs

## Removal

1. Settings → Devices & services → iPhone Alarms Sync → ⋮ on the phone → **Delete**.
2. On the phone, delete the iPhone Alarms Sync shortcuts and their automations.

## Beta versions

Every change is first published as a beta (`vX.Y.Z-beta.N`) before it becomes a stable release. To help test, turn on the **Pre-release** switch on the iPhone Alarms Sync device of the Marketplace integration (HACS on Home Assistant 2026.8–2026.10) and update as usual. Turn it off to return to stable.
