# iPhone Alarms Sync

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

### Step 2: Import Shortcut

Scan QR code or open link on your iPhone/iPad:

![QR Code](https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=https://www.icloud.com/shortcuts/9add5384e92f42b792fb4f91ce50ee6c)

**[Open Shortcut](https://www.icloud.com/shortcuts/9add5384e92f42b792fb4f91ce50ee6c)**

When prompted, enter your **Phone ID** (shown during setup).

### Step 3: Create Automation

1. Shortcuts app → Automation → +
2. App → Clock → Is Closed
3. Run Shortcut → "Sync Alarms With HA"
4. Enable "Run Immediately" → Done

Alarms sync automatically when you close the Clock app.

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
