<p align="center">
  <img src="assets/social-preview.png" alt="iPhone Alarms Sync">
</p>

<h1 align="center">iPhone Alarms Sync</h1>

<p align="center">
  <a href="https://github.com/Jozwiaczek/iphone-alarms-sync/releases/latest"><img src="https://img.shields.io/github/v/release/Jozwiaczek/iphone-alarms-sync?label=stable" alt="Stable version"></a>
  <a href="https://github.com/Jozwiaczek/iphone-alarms-sync/releases"><img src="https://img.shields.io/github/v/release/Jozwiaczek/iphone-alarms-sync?include_prereleases&label=beta&color=orange" alt="Beta version"></a>
  <a href="https://github.com/Jozwiaczek/iphone-alarms-sync/actions/workflows/validate.yml"><img src="https://github.com/Jozwiaczek/iphone-alarms-sync/actions/workflows/validate.yml/badge.svg?branch=main" alt="Validate"></a>
  <img src="https://img.shields.io/badge/License-GPL--3.0-blue.svg" alt="License">
  <img src="https://img.shields.io/badge/Marketplace-integration-FF9500" alt="Marketplace">
  <img src="https://img.shields.io/badge/Home%20Assistant-2026.8%2B-blue?logo=homeassistant" alt="Home Assistant">
</p>

<p align="center">
  <a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=Jozwiaczek&repository=iphone-alarms-sync&category=integration"><img src="https://my.home-assistant.io/badges/hacs_repository.svg" alt="Open in the Marketplace"></a>
</p>

iOS shares its alarms with no app, so Home Assistant can't see when you wake up. iPhone Alarms Sync gets them there with Apple Shortcuts. Each alarm becomes a device, and automations can run before an alarm, or when it goes off, is snoozed or stopped.

## ✨ What you get

Start with one shortcut. Add the others only if you need them.

| On the phone | Home Assistant gets | Ideas |
|---|---|---|
| **Sync** shortcut (required) | A device per alarm with its time, repeat days and enabled state. Next alarm sensors. | Warm the bedroom before the alarm. Brighten the lights slowly. Remind you when no alarm is set. |
| + **Device Event** shortcut, one copy per event | The moment any alarm or the Wake-Up alarm goes off, is snoozed or stopped. Wind down, bedtime and waking up. | Lights, blinds and coffee when the alarm goes off. Dim the lights at bedtime. |
| + **Alarm Event** shortcut, one copy per alarm and event | Goes off, snoozed and stopped for one alarm. | A full routine for *Work*, a gentle one for *Weekend*. |

Sync is one-way, from the phone to Home Assistant. Works on iPhone, iPad and Mac: add the integration once per device.

### Why Shortcuts?

- The Home Assistant app has a next alarm sensor on Android only. iOS gives apps no access to the alarms in Clock.
- Another alarm app sees only its own alarms.
- Shortcuts can read them. This integration turns that into devices, triggers and warnings, so you don't have to build it yourself.

## 🚀 Installation

**Requirements:** Home Assistant 2026.8 or newer, an iPhone or iPad with iOS 17+ or a Mac with Shortcuts automations, and the Home Assistant app 2026.9.3 or newer.

### Step 1: Install from the Marketplace

1. Click **Open in the Marketplace** above, or go to Settings → Marketplace and search for "iPhone Alarms Sync"
2. Download "iPhone Alarms Sync"
3. Restart Home Assistant

On Home Assistant 2026.8–2026.10 the button opens HACS instead.

#### Beta versions

Every change is first published as a beta (`vX.Y.Z-beta.N`) and tested before it becomes a stable release. You get stable releases by default. To help test, enable the **Pre-release** switch (disabled by default) on the iPhone Alarms Sync device of the Marketplace integration, or of HACS on Home Assistant 2026.8–2026.10, and update as usual. Turn it off to return to stable.

### Step 2: Add your phone

1. Settings → Devices & Services → Add Integration → "iPhone Alarms Sync"
2. Pick your Home Assistant app device or enter a name
3. Follow the screen: it shows your **Phone ID**, the QR code of the Sync shortcut and the iOS automation to create

Alarms then sync every time you close the Clock app.

For the event shortcuts, open **Configure → Event Shortcuts Setup**. The [Shortcuts Setup Guide](docs/shortcuts.md) has every link and step.

## 🎯 Examples

Sync shortcut only: warm the bedroom 30 minutes before the next alarm.

```yaml
triggers:
  - trigger: time
    at:
      entity_id: sensor.johns_iphone_next_alarm
      offset: "-00:30:00"
actions:
  - action: climate.set_temperature
    target:
      entity_id: climate.bedroom
    data:
      temperature: 21
```

With an event shortcut: turn on the light when an alarm goes off. See [Triggers](#triggers).

## 📋 Reference

### Entities

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
| Alarm event missed | On when an alarm rang but no *Goes Off* event arrived ([details](docs/shortcuts.md#alarm-event-missed)) |

**Alarm device** (one per alarm, named like in the Clock app, e.g. *John's iPhone 07:00 Wake*; the name follows the alarm's time and label)

| Entity | Description |
|---|---|
| Alarm ID | Alarm ID for the Alarm Event shortcut (diagnostic); its attributes hold the alarm's time, label and settings |
| Next occurrence, Last occurrence | Next and last scheduled ring |
| Last went off / snoozed / stopped | Last events of this alarm (Alarm Event shortcut) |
| Enabled, Allows snooze | Alarm state on the phone |
| Repeats, Repeats on Monday … Sunday | Repeat schedule (disabled by default) |
| Snooze time | Snooze length for your automations, 1-30 min. iOS does not share it, so set it yourself (default 9) |

Event timestamps stay *unknown* until the matching shortcut reports the first event.

### Triggers

The easiest way: add the trigger **Alarm goes off**, **Alarm is snoozed** or **Alarm is stopped** and pick one or more alarms (or an area or label). It fires when any of them rings, so "when *07:00 Wake* or *06:30 Gym* goes off" is one trigger.

```yaml
triggers:
  - trigger: iphone_alarms_sync.goes_off
    target:
      entity_id:
        - event.johns_iphone_07_00_wake_alarm
        - event.johns_iphone_06_30_gym_alarm
actions:
  - action: light.turn_on
    target:
      entity_id: light.bedroom
```

The alarms you can pick are event entities, named like the iOS automations:

| Device | Event entity | Events | Needs |
|---|---|---|---|
| Alarm | *Alarm* | Goes off, Is snoozed, Is stopped | Alarm Event shortcut for this alarm |
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

### Actions

The shortcuts call `iphone_alarms_sync.sync_alarms`, `iphone_alarms_sync.report_device_event` and `iphone_alarms_sync.report_alarm_event`. Their fields are listed in the [Shortcuts Setup Guide](docs/shortcuts.md#how-it-works).

### Options

Settings → Devices & services → iPhone Alarms Sync → **Configure**:

- **Edit Device** - name, linked Mobile App device and **Sync disabled alarms** (off: disabled alarms are not synced and their devices are removed). A new name can give a new **Phone ID**: devices, entities, history and automations move to it, but you must enter the new Phone ID in every shortcut on the phone.
- **Events History** - the last 20 events since Home Assistant started
- **Sync Shortcut Setup** and **Event Shortcuts Setup** - Phone ID, QR codes and the Alarm IDs

### Limitations

- iOS lets no app read alarms in the background. Home Assistant learns about changes only when a shortcut runs, so an alarm changed with Siri or on an Apple Watch updates after you next close the Clock app.
- iOS turns a one-time alarm off after it rings; Home Assistant shows it until the next sync.
- Next Alarm and Next Occurrence are calculated in Home Assistant's time zone.

### Removal

1. Settings → Devices & services → iPhone Alarms Sync → ⋮ on the phone → **Delete**.
2. On the phone, delete the iPhone Alarms Sync shortcuts and their automations.

## 🔧 Troubleshooting

- **Alarms not syncing:** Check Personal Automations are enabled in iOS Settings → Shortcuts
- **Phone ID:** Found in integration options → Sync Shortcut Setup. After renaming the phone in Edit Device, enter the new one in every shortcut.
- **Shortcut not working:** Verify Phone ID is correct during import
- **Stopped working after a Home Assistant app update, or *No server provided*:** the shortcut's *Perform action* step may show **Choose** or point to a server from another device. Pick the **Server** and then the `iphone_alarms_sync.*` action again or re-import the shortcuts. See [Troubleshooting](docs/shortcuts.md#troubleshooting).
- **Repair issue "stopped sending alarm data":** Home Assistant raises it when a phone sends nothing for 7 days. Run the shortcut manually to see the error.
- **Alarm event missed is on:** the phone couldn't reach Home Assistant when the alarm rang. See [Troubleshooting](docs/shortcuts.md#troubleshooting).
- **Reporting a bug:** attach the diagnostics file (Settings → Devices & services → iPhone Alarms Sync → ⋮ → Download diagnostics).

## 📚 Documentation

- [Shortcuts Setup Guide](docs/shortcuts.md) - Detailed setup and troubleshooting
- [Issue Tracker](https://github.com/Jozwiaczek/iphone-alarms-sync/issues)

## 🤝 Contributing

Bug reports, ideas and pull requests are welcome. [CONTRIBUTING.md](CONTRIBUTING.md) shows how to set up, check a change and write the commit message.

## ☕ Support

If you find this integration useful, consider supporting its development:

[![GitHub Sponsors](https://img.shields.io/badge/sponsor-30363D?style=for-the-badge&logo=GitHub-Sponsors&logoColor=#EA4AAA)](https://github.com/sponsors/Jozwiaczek)

or

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-ffdd00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/jozwiaczek)
