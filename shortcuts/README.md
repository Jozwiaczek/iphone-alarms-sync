# iOS Shortcuts Setup

This directory contains ready-to-use `.shortcut` files for easy import into iOS Shortcuts app.

## Quick Start (2 Steps)

### Step 1: Import Shortcut

1. **On your iPhone/iPad**, open this link to import the shortcut:
   - [Import "Sync Alarms With HA" Shortcut](shortcuts://import-shortcut?url=https%3A%2F%2Fraw.githubusercontent.com%2FJozwiaczek%2Fiphone-alarms-sync%2Fmain%2Fshortcuts%2FSync%2520Alarms%2520With%2520HA.shortcut&name=Sync%20Alarms%20With%20HA)
   
   **Note:** The link must be opened on an iOS device. If you're viewing this on a computer, copy the link and send it to yourself, then open it on your iPhone/iPad.

2. **When prompted for "Device ID"**, enter your Phone ID from Home Assistant:
   - Find your Phone ID in: Settings → Devices & Services → iPhone Alarms Sync → Configure → Sync Shortcut Setup
   - Copy the Phone ID (e.g., `johns_iphone`) and paste it when the shortcut asks for Device ID
   - The shortcut will be imported and ready to use

### Step 2: Create Personal Automation

After importing the shortcut, you need to create a Personal Automation that runs it automatically:

1. Open the **Shortcuts** app on your iPhone/iPad
2. Go to the **Automation** tab (at the bottom)
3. Tap **+** (Create Personal Automation)
4. Select **App** → **Clock** → **Is Closed** → **Next**
5. Tap **Add Action**
6. Search for **Run Shortcut** and add it
7. Select **"Sync Alarms With HA"** from the list of shortcuts
8. Tap **Next**
9. **Important:** Make sure **"Run Immediately"** is enabled (turn off "Ask Before Running" if it's on)
10. Tap **Done**

**That's it!** Now every time you close the Clock app, your alarms will automatically sync to Home Assistant.

## Where to Find Your Device ID

Your **Phone ID** (Device ID) is shown in several places:

1. **During setup:** In the confirmation screen when adding the integration
2. **In Options Flow:** Settings → Devices & Services → iPhone Alarms Sync → Configure → Sync Shortcut Setup
3. **In entity IDs:** Your Phone ID is part of entity names like `sensor.{phone_id}_{alarm_id}_time`

The Phone ID is generated from your device name (e.g., "John's iPhone" becomes `johns_iphone`).

## Troubleshooting

### Shortcut doesn't run automatically

- **Check Personal Automations are enabled:** iOS Settings → Shortcuts → Advanced → Allow Running Automations
- **Verify automation settings:** Make sure "Run Immediately" is enabled (not "Ask Before Running")
- **Check trigger:** Ensure the automation trigger is set to "App" → "Clock" → "Is Closed"

### Alarms not syncing

- **Verify Phone ID:** Make sure the Device ID in the shortcut matches your Phone ID in Home Assistant
- **Check Home Assistant logs:** Settings → System → Logs → Look for `iphone_alarms_sync` entries
- **Test manually:** Open Shortcuts app → My Shortcuts → Run "Sync Alarms With HA" manually to test

### Import link doesn't work

- **Must open on iOS device:** The import link only works on iPhone/iPad, not on computers
- **Try alternative:** If the link doesn't work, you can manually download the `.shortcut` file from GitHub and share it to your device via AirDrop or Files app

### Shortcut shows error when running

- **Check Home Assistant connection:** Make sure your iPhone is connected to the same network as Home Assistant, or use remote access
- **Verify service exists:** Check that `iphone_alarms_sync.sync_alarms` service is available in Developer Tools → Services
- **Check logs:** Review Home Assistant logs for detailed error messages

## Additional Shortcuts

More shortcuts for alarm events (goes off, snoozed, stopped) and sleep events will be available soon. They will follow the same simple 2-step import process.
