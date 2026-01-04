# iPhone Alarms Sync

![Version](https://img.shields.io/github/v/release/Jozwiaczek/iphone-alarms-sync?label=version)
![Release Date](https://img.shields.io/github/release-date/Jozwiaczek/iphone-alarms-sync)
![License](https://img.shields.io/badge/License-MIT-blue.svg)
![HACS](https://img.shields.io/badge/HACS-Custom-orange)
![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue?logo=homeassistant)
![Downloads](https://img.shields.io/github/downloads/Jozwiaczek/iphone-alarms-sync/total)
[![gitmoji-changelog](https://img.shields.io/badge/Changelog-gitmoji-brightgreen.svg)](https://github.com/frinyvonnick/gitmoji-changelog)

[![HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Jozwiaczek&repository=iphone-alarms-sync&category=integration)

Sync iPhone/iPad alarms to Home Assistant using predefined Apple Shortcuts. This is a **one-way synchronization** from Apple iPhone or iPad to Home Assistant, enabling alarm-based automations like turning on lights, brewing coffee, or opening blinds when your alarm goes off.

## ✨ Features

### Alarm Synchronization
- **Automatic sync** - All alarms from your iPhone/iPad are automatically synchronized to Home Assistant when you close the Clock app
- **Real-time updates** - Alarm changes (enable/disable, time changes, repeat settings) are reflected immediately
- **Multiple alarms support** - Track all your alarms individually with their own entities and states
- **Wake-Up alarms** - Special support for iOS Wake-Up alarms with dedicated tracking

### Event Tracking
- **Alarm events** - Monitor when alarms go off, are snoozed, or stopped
- **Precise timestamps** - Know exactly when each event occurred for detailed automation logic
- **Event history** - Track the last occurrence of each event type per alarm
- **Device-level events** - Monitor Wake-Up alarms, any alarm events, or sleep-related events (bedtime, wind down, waking up)

### Smart Home Integration
- **Device triggers** - Use alarm events as triggers in Home Assistant automations
- **Rich sensor data** - Access alarm times, repeat schedules, next occurrence, and sync status
- **Conditional automations** - Create automations based on specific alarms, weekdays, or event types
- **Multi-device support** - Sync alarms from multiple iPhones/iPads in the same Home Assistant instance

## 🚀 Installation

### Step 1: Install via HACS

1. Open HACS → Integrations → Custom repositories
2. Add repository: `Jozwiaczek/iphone-alarms-sync`
3. Install "iPhone Alarms Sync"
4. Restart Home Assistant

### Step 2: Configure

1. Settings → Devices & Services → Add Integration → "iPhone Alarms Sync"
2. Scan QR code or open link on your iPhone/iPad
3. Import the **"Sync Alarms With HA"** shortcut (required)
4. Enter your **Phone ID** when prompted

#### Sync Alarms With HA (Required)

![QR Code](https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=https://www.icloud.com/shortcuts/9add5384e92f42b792fb4f91ce50ee6c)

**[Open Shortcut](https://www.icloud.com/shortcuts/9add5384e92f42b792fb4f91ce50ee6c)**

#### Emit Alarm Event To HA Template (Optional)

![QR Code](https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=https://www.icloud.com/shortcuts/9f7d28f1a627402a92e1e23044112e53)

**[Open Shortcut](https://www.icloud.com/shortcuts/9f7d28f1a627402a92e1e23044112e53)** - For specific alarm events

#### Emit Device Event To HA Template (Optional)

![QR Code](https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=https://www.icloud.com/shortcuts/54e7bbaf5fb2479fb59bff0dfecfc856)

**[Open Shortcut](https://www.icloud.com/shortcuts/54e7bbaf5fb2479fb59bff0dfecfc856)** - For device-level events (Wake-Up, any alarm, sleep events)

### Step 3: Create iOS Automation

1. Shortcuts app → Automation → **+**
2. App → Clock → **Is Closed**
3. Run Shortcut → **"Sync Alarms With HA"**
4. Enable **"Run Immediately"** → Done

Alarms sync automatically when you close the Clock app.

> 💡 See [Shortcuts Setup Guide](docs/shortcuts.md) for detailed instructions.

## 🎯 Example Use Cases

- **Morning routine** - Turn on lights, adjust thermostat, open blinds, and start coffee maker when alarm goes off
- **Smart snooze** - Dim or turn off lights when alarm is snoozed, brighten when stopped
- **Weekday vs weekend** - Different automations for weekdays (full routine) and weekends (gentle wake-up)
- **Bedtime preparation** - Dim lights, lower thermostat, close blinds when bedtime starts
- **Gradual wake-up** - Gradually increase light brightness over several minutes before alarm
- **Pre-alarm preparation** - Start warming up room 30 minutes before alarm time

## 🔧 Troubleshooting

- **Alarms not syncing:** Check Personal Automations are enabled in iOS Settings → Shortcuts
- **Phone ID:** Found in integration options → Sync Shortcut Setup
- **Shortcut not working:** Verify Phone ID is correct during import

## 📚 Documentation

- [Shortcuts Setup Guide](docs/shortcuts.md) - Detailed setup and troubleshooting
- [Issue Tracker](https://github.com/Jozwiaczek/iphone-alarms-sync/issues)

## ☕ Support

If you find this integration useful, consider supporting its development:

[![GitHub Sponsors](https://img.shields.io/badge/sponsor-30363D?style=for-the-badge&logo=GitHub-Sponsors&logoColor=#EA4AAA)](https://github.com/sponsors/Jozwiaczek)

or

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-ffdd00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/jozwiaczek)
