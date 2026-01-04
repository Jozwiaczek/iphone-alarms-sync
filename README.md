# iPhone Alarms Sync

![Version](https://img.shields.io/github/v/release/Jozwiaczek/iphone-alarms-sync?label=version)
![Release Date](https://img.shields.io/github/release-date/Jozwiaczek/iphone-alarms-sync)
![License](https://img.shields.io/github/license/Jozwiaczek/iphone-alarms-sync)
![HACS](https://img.shields.io/badge/HACS-Custom-orange)
![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue?logo=homeassistant)
![Downloads](https://img.shields.io/github/downloads/Jozwiaczek/iphone-alarms-sync/total)
[![gitmoji-changelog](https://img.shields.io/badge/Changelog-gitmoji-brightgreen.svg)](https://github.com/frinyvonnick/gitmoji-changelog)

[![HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Jozwiaczek&repository=iphone-alarms-sync&category=integration)

Sync iPhone/iPad alarms to Home Assistant. Track alarm states and events (goes off, snoozed, stopped).

## Installation

### HACS (Recommended)

1. Open HACS → Integrations → Custom repositories
2. Add this repository
3. Install "iPhone Alarms Sync"
4. Restart Home Assistant

### Manual

Copy `custom_components/iphone_alarms_sync` to your HA `custom_components` folder.

## Setup

### Step 1: Add Device

Settings → Devices & Services → Add Integration → "iPhone Alarms Sync"

### Step 2: Import Shortcuts

During setup, you'll see QR codes and links for all shortcuts. Import at least the **Sync Alarms** shortcut:

- **[Sync Alarms With HA](https://www.icloud.com/shortcuts/9add5384e92f42b792fb4f91ce50ee6c)** - Required for syncing alarms
- **[Emit Alarm Event To HA Template](https://www.icloud.com/shortcuts/9f7d28f1a627402a92e1e23044112e53)** - Optional: for specific alarm events
- **[Emit Device Event To HA Template](https://www.icloud.com/shortcuts/54e7bbaf5fb2479fb59bff0dfecfc856)** - Optional: for device-level events (Wake-Up, any alarm, sleep events)

When prompted, enter your **Phone ID** (shown during setup).

### Step 3: Create Automation

1. Shortcuts app → Automation → +
2. App → Clock → Is Closed
3. Run Shortcut → "Sync Alarms With HA"
4. Enable "Run Immediately" → Done

Alarms sync automatically when you close the Clock app.

For detailed setup instructions, import questions, and event shortcuts configuration, see [Shortcuts Setup Guide](docs/shortcuts.md).

## Entities

For each alarm:
- `binary_sensor.{phone_id}_{alarm_id}_enabled` - Alarm on/off
- `sensor.{phone_id}_{alarm_id}_time` - Alarm time (HH:MM)
- `sensor.{phone_id}_{alarm_id}_repeat_days` - Repeat days

## Device Triggers

- `goes_off` - Alarm fired
- `snoozed` - Alarm snoozed
- `stopped` - Alarm stopped

## Automation Example

```yaml
automation:
  - alias: "Lights on alarm"
    trigger:
      - platform: device
        domain: iphone_alarms_sync
        device_id: !device_id johns_iphone_morning
        type: goes_off
    action:
      - service: light.turn_on
        target:
          entity_id: light.bedroom
```

## Troubleshooting

- **Alarms not syncing:** Check Personal Automations are enabled in iOS Settings → Shortcuts
- **Phone ID:** Found in integration options → Sync Shortcut Setup

## Documentation

- [Shortcuts Setup Guide](docs/shortcuts.md) - Detailed iOS shortcuts setup and troubleshooting
- [Issue Tracker](https://github.com/Jozwiaczek/iphone-alarms-sync/issues)

## License

MIT
