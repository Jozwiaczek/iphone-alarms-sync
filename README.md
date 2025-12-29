# iPhone Alarms Sync

[![Open your Home Assistant instance and open the iPhone Alarms Sync integration inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Jozwiaczek&repository=iphone-alarms-sync&category=integration)

Home Assistant custom integration for one-way synchronization of iPhone alarms (also works with iPad). Sync alarm states and track alarm events (goes off, snoozed, stopped) from your iPhone or iPad to Home Assistant.

## Features

- **One-way sync** from iPhone to Home Assistant
- **Auto-create alarms** - alarms are automatically created when first synced
- **Device triggers** - use alarm events in automations
- **Sensor entities** - track alarm state, time, repeat days, and events
- **Event history** - view all alarm events in Options Flow
- **HA Companion App integration** - uses built-in Shortcuts actions (no manual URL/auth needed)

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to Integrations
3. Click the three dots menu → Custom repositories
4. Add this repository
5. Install "iPhone Alarms Sync"
6. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/iphone_alarms_sync` folder to your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Go to Settings → Devices & Services → Add Integration
4. Search for "iPhone Alarms Sync"

## Configuration

### Step 1: Add Phone

1. Go to Settings → Devices & Services → Add Integration
2. Search for "iPhone Alarms Sync"
3. Enter device name (e.g., "John's iPhone" or "John's iPad") or select Mobile App device
4. Phone ID will be auto-generated (e.g., "johns_iphone")

### Step 2: Setup Shortcuts

1. Import shortcuts on your iPhone or iPad (see Shortcuts Setup below)
2. Enter your `phone_id` in each shortcut
3. Enable Personal Automations in iOS Settings

### Step 3: Wait for First Sync

1. Open Clock app on iPhone or iPad
2. Exit Clock app (triggers sync shortcut)
3. Integration will auto-create alarm devices

## Shortcuts Setup

### Required Shortcuts

You need to create 4 Personal Automations in iOS Shortcuts:

#### 1. Sync All Alarms

**Trigger:**
- Personal Automation → "App" → "Clock" → "Is Closed"

**Actions:**
1. Get All Alarms (from Clock app)
2. Format alarms as Dictionary
3. HA Companion App → "Call Service"
   - Service: `iphone_alarms_sync.sync_alarms`
   - Payload:
     ```json
     {
       "phone_id": "YOUR_PHONE_ID",
       "alarms": [/* alarm data from Get All Alarms */]
     }
     ```

#### 2. Alarm Goes Off

**Trigger:**
- Personal Automation → "Alarm" → "Goes Off"

**Actions:**
1. HA Companion App → "Call Service"
   - Service: `iphone_alarms_sync.report_alarm_event`
   - Payload:
     ```json
     {
       "phone_id": "YOUR_PHONE_ID",
       "alarm_id": "ALARM_ID_FROM_TRIGGER",
       "event": "goes_off"
     }
     ```

#### 3. Alarm Snoozed

**Trigger:**
- Personal Automation → "Alarm" → "Is Snoozed"

**Actions:**
1. HA Companion App → "Call Service"
   - Service: `iphone_alarms_sync.report_alarm_event`
   - Payload:
     ```json
     {
       "phone_id": "YOUR_PHONE_ID",
       "alarm_id": "ALARM_ID_FROM_TRIGGER",
       "event": "snoozed"
     }
     ```

#### 4. Alarm Stopped

**Trigger:**
- Personal Automation → "Alarm" → "Is Stopped"

**Actions:**
1. HA Companion App → "Call Service"
   - Service: `iphone_alarms_sync.report_alarm_event`
   - Payload:
     ```json
     {
       "phone_id": "YOUR_PHONE_ID",
       "alarm_id": "ALARM_ID_FROM_TRIGGER",
       "event": "stopped"
     }
     ```

### Getting Your Phone ID

Your `phone_id` is shown in the integration setup flow and can be found in:
- Integration Options → Shortcuts Setup
- Or in the sensor entity IDs: `sensor.{phone_id}_{alarm_id}_time`

## Entities

For each alarm, the integration creates:

### Binary Sensors
- `binary_sensor.{phone_id}_{alarm_id}_enabled` - Alarm enabled state
- `binary_sensor.{phone_id}_{alarm_id}_repeats` - Alarm repeats
- `binary_sensor.{phone_id}_{alarm_id}_allows_snooze` - Allows snooze

### Sensors
- `sensor.{phone_id}_{alarm_id}_time` - Alarm time (HH:MM)
- `sensor.{phone_id}_{alarm_id}_repeat_days` - Repeat days (Mon,Tue,Wed...)
- `sensor.{phone_id}_{alarm_id}_last_sync` - Last sync timestamp
- `sensor.{phone_id}_{alarm_id}_last_event` - Last event type
- `sensor.{phone_id}_{alarm_id}_last_event_at` - Last event timestamp
- `sensor.{phone_id}_{alarm_id}_shortcut_snippet` - Ready-to-use JSON payloads

## Device Triggers

Each alarm device supports device automation triggers:
- `goes_off` - Alarm fired
- `snoozed` - Alarm was snoozed
- `stopped` - Alarm was stopped/dismissed

## Events

The integration fires the following events:

### `iphone_alarms_sync_alarm_event`

Fired when an alarm event is reported. Event data:
```json
{
  "phone_id": "johns_iphone",
  "alarm_id": "ABC123",
  "event": "goes_off",
  "event_id": "uuid",
  "occurred_at": "2024-01-01T07:00:00Z"
}
```

## Automation Examples

### Play Music When Alarm Goes Off

```yaml
automation:
  - alias: "Play Music on Alarm"
    trigger:
      - platform: device
        domain: iphone_alarms_sync
        device_id: !device_id johns_iphone_morning_alarm
        type: goes_off
    action:
      - service: media_player.play_media
        target:
          entity_id: media_player.bedroom_speaker
        data:
          media_content_id: "spotify:playlist:your_playlist"
          media_content_type: "music"
```

### Turn On Lights When Alarm Stops

```yaml
automation:
  - alias: "Lights On When Alarm Stops"
    trigger:
      - platform: device
        domain: iphone_alarms_sync
        device_id: !device_id johns_iphone_morning_alarm
        type: stopped
    action:
      - service: light.turn_on
        target:
          entity_id: light.bedroom
        data:
          brightness: 255
```

### Event-Based Automation

```yaml
automation:
  - alias: "Morning Routine"
    trigger:
      - platform: event
        event_type: iphone_alarms_sync_alarm_event
        event_data:
          event: goes_off
          phone_id: johns_iphone
    condition:
      - condition: time
        after: "07:00:00"
        before: "08:00:00"
    action:
      - service: scene.turn_on
        target:
          entity_id: scene.morning_routine
```

## Options Flow

After setup, access Options Flow via:
Settings → Devices & Services → iPhone Alarms Sync → Configure

### Available Options

1. **Overview** - Dashboard with sync status, alarm count, recent events
2. **Alarms** - List all synced alarms, edit labels/icons, delete alarms
3. **Events History** - View chronological list of all alarm events
4. **Device Settings** - Edit device name, link/unlink Mobile App device
5. **Shortcuts Setup** - View phone_id and shortcuts instructions
6. **Delete Device** - Remove device and all alarms

## Troubleshooting

### Alarms Not Syncing

1. Check that Personal Automations are enabled in iOS Settings
2. Verify shortcuts are set up correctly
3. Check Home Assistant logs for service call errors
4. Ensure `phone_id` matches in shortcuts and integration

### Events Not Firing

1. Verify alarm triggers are set up in Shortcuts
2. Check that alarm events are being reported (view in Options → Events)
3. Ensure device triggers are available in automation editor

### Mobile App Device Link

Linking to Mobile App device is optional and only for visual organization. The integration works perfectly without it.

## Support

- [Issue Tracker](https://github.com/Jozwiaczek/iphone-alarms-sync/issues)
- [Documentation](https://github.com/Jozwiaczek/iphone-alarms-sync)

## Publishing to HACS

Before publishing to HACS, ensure:

1. **Add to Home Assistant Brands**:
   - Create a PR to [home-assistant/brands](https://github.com/home-assistant/brands)
   - Add your integration to the brands repository

4. **GitHub Actions must pass**:
   - HACS Action workflow (`.github/workflows/hacs.yml`)
   - Validate workflow (`.github/workflows/validate.yml`) with hassfest

5. **Create GitHub release** after all actions pass

6. **Repository requirements**:
   - Repository must be public
   - Repository must have description
   - Repository must have topics
   - Repository must have README

## License

MIT License

