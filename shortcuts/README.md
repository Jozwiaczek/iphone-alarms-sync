# iOS Shortcuts Setup

## Quick Start (2 Steps)

### Step 1: Import Shortcut

Scan QR code or open link on your iPhone/iPad:

![QR Code](https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=https://www.icloud.com/shortcuts/9add5384e92f42b792fb4f91ce50ee6c)

**[Open Shortcut](https://www.icloud.com/shortcuts/9add5384e92f42b792fb4f91ce50ee6c)**

When prompted for **Device ID**, enter your Phone ID from Home Assistant:
- Find it in: Settings → Devices & Services → iPhone Alarms Sync → Configure → Sync Shortcut Setup

### Step 2: Create Automation

1. Open **Shortcuts** app → **Automation** tab
2. Tap **+** → **Personal Automation**
3. Select **App** → **Clock** → **Is Closed**
4. Add action: **Run Shortcut** → **"Sync Alarms With HA"**
5. Enable **"Run Immediately"**
6. Tap **Done**

Alarms sync automatically when you close the Clock app.

## Troubleshooting

### Shortcut doesn't run

- iOS Settings → Shortcuts → Advanced → Enable "Allow Running Automations"
- Check automation has "Run Immediately" enabled

### Alarms not syncing

- Verify Phone ID matches in shortcut and Home Assistant
- Test manually: Shortcuts app → Run "Sync Alarms With HA"

### Import doesn't work

- Link must be opened on iOS device
- Try opening in Safari if other browsers fail
