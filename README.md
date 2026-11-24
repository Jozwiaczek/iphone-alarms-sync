<p align="center">
  <img src="assets/social-preview.png" alt="iPhone Alarms Sync">
</p>

<h1 align="center">iPhone Alarms Sync</h1>

<p align="center">
  <a href="https://github.com/Jozwiaczek/iphone-alarms-sync/releases/latest"><img src="https://img.shields.io/github/v/release/Jozwiaczek/iphone-alarms-sync?label=stable" alt="Stable version"></a>
</p>

<p align="center">
  <a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=Jozwiaczek&repository=iphone-alarms-sync&category=integration"><img src="https://my.home-assistant.io/badges/hacs_repository.svg" alt="Open in the Marketplace"></a>
</p>

Let Home Assistant react to your iPhone alarms. Warm the bedroom before you wake up. Turn on the lights when the alarm goes off.

iOS shares alarms with no app, only with Shortcuts. One shortcut sends them to Home Assistant each time you close the Clock app. Works on iPhone, iPad and Mac.

## ✨ What you get

- A device per alarm: time, repeat days, on or off
- Next alarm sensors
- An **Alarm goes off** trigger at each alarm's time ([estimated](docs/shortcuts.md#estimated-goes-off))

Want the exact moment, snooze, stop or sleep events? Add the event shortcuts later: [Shortcuts Setup Guide](docs/shortcuts.md).

### Limitations

- Sync is one-way: Home Assistant can't change alarms on the phone.
- iOS lets no app read alarms in the background. Home Assistant learns about changes only when a shortcut runs, so an alarm changed with Siri or on an Apple Watch updates after you next close the Clock app.
- iOS turns a one-time alarm off after it rings; Home Assistant shows it until the next sync.
- Next Alarm and Next Occurrence are calculated in Home Assistant's time zone.

## 🚀 Installation

**Requirements:** Home Assistant 2026.8 or newer, an iPhone or iPad with iOS 17+ or a Mac with Shortcuts automations, and the Home Assistant app 2026.9.3 or newer.

### Step 1: Install from the Marketplace

1. Click **Open in the Marketplace** above, or go to Settings → Marketplace and search for "iPhone Alarms Sync"
2. Download "iPhone Alarms Sync"
3. Restart Home Assistant

On Home Assistant 2026.8–2026.10 the button opens HACS instead.

### Step 2: Add your phone

1. Settings → Devices & Services → Add Integration → "iPhone Alarms Sync"
2. Pick your Home Assistant app device or enter a name
3. Follow the screen: it shows your **Phone ID**, the QR code of the Sync shortcut and the iOS automation to create

Alarms then sync every time you close the Clock app.

For the event shortcuts, open **Configure → Event Shortcuts Setup**. The [Shortcuts Setup Guide](docs/shortcuts.md) has every link and step.

## 🎯 Examples

Warm the bedroom 30 minutes before the next alarm:

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

Turn on the light when an alarm goes off. In the automation editor, pick the trigger **Alarm goes off** and your alarms. In YAML:

```yaml
triggers:
  - trigger: iphone_alarms_sync.goes_off
    target:
      entity_id: event.johns_iphone_wake_alarm
actions:
  - action: light.turn_on
    target:
      entity_id: light.bedroom
```

Both work with the Sync shortcut alone. An event shortcut makes *goes off* exact.

## 🔧 Troubleshooting

Most problems come from the shortcut: see the [Troubleshooting guide](docs/shortcuts.md#troubleshooting).

Reporting a bug? Attach the diagnostics: Settings → Devices & services → iPhone Alarms Sync → ⋮ → Download diagnostics.

Still stuck? Ask in [Q&A](https://github.com/Jozwiaczek/iphone-alarms-sync/discussions/categories/q-a).

## 📚 More

- [Shortcuts Setup Guide](docs/shortcuts.md): every shortcut, step by step
- [Reference](docs/reference.md): entities, triggers, event data, options, removal
- [Beta versions](docs/reference.md#beta-versions)
- [Issues](https://github.com/Jozwiaczek/iphone-alarms-sync/issues)

## 🤝 Contributing

Bug reports, ideas and pull requests are welcome. [CONTRIBUTING.md](CONTRIBUTING.md) shows where to ask a question, report a bug or suggest an idea, and how to send a pull request.

## ☕ Support

If you find this integration useful, consider supporting its development:

[![GitHub Sponsors](https://img.shields.io/badge/sponsor-30363D?style=for-the-badge&logo=GitHub-Sponsors&logoColor=#EA4AAA)](https://github.com/sponsors/Jozwiaczek) [![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-ffdd00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/jozwiaczek)
