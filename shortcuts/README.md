# iOS Shortcuts

This directory should contain template `.shortcut` files for import into iOS Shortcuts app.

## Required Shortcuts

### 1. Sync All Alarms

**Trigger:**
- Personal Automation → "App" → "Clock" → "Is Closed"

**Actions (step by step):**

1. **Find Alarms**
   - Action: "Find Alarms"
   - Condition: "Is Enabled" (optional, if you want only enabled alarms)
   - Sort by: "Hours" (optional)
   - Order: "Smallest First" (optional)

2. **Repeat with Each** (transform each alarm to the appropriate format)
   
   **Step 2.1:** Add "Repeat with Each" action
   - In the **Input** field, select the "Alarms" variable from the "Find Alarms" action
   
   **Step 2.2:** Inside the loop, build a Dictionary for each alarm:
   
   Add **Dictionary** action (not "Get Dictionary from Input", but "Dictionary" - creates a new empty Dictionary)
   
   In the "Dictionary" action, add the following keys and values (click **+** for each):
   
   **IMPORTANT:** For each field, select the appropriate data type (Text, Number, Boolean, Array) from the menu that appears:
   
   - **Key:** `alarm_id` (type: **Text**)
     - **Value:** Get Value for Key → Dictionary: "Repeat Item", Key: `URL`
     - **Type:** Select **Text** from the type menu
     - **NOTE:** `URL` contains the alarm identifier in URL format (e.g., `x-apple-clock://alarm/UUID`). You can use the entire URL as `alarm_id`, or if you want only the UUID, use:
       - Action "Get Text from Input" → Input: result from "Get Value for Key" (URL)
       - Action "Match Text" → Text: result from "Get Text", Pattern: `[A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12}` (regex for UUID)
       - Use the result from "Match Text" as `alarm_id`
     - **Simpler solution:** Use the entire URL as `alarm_id` - Home Assistant will accept it as a string
   
   - **Key:** `label` (type: **Text**)
     - **Value:** Get Value for Key → Dictionary: "Repeat Item", Key: `Label`
     - **Type:** Select **Text** from the type menu
   
   - **Key:** `enabled` (type: **Boolean**)
     - **Value:** Get Value for Key → Dictionary: "Repeat Item", Key: `Is Enabled`
     - **Type:** Select **Boolean** from the type menu
   
   - **Key:** `hour` (type: **Number**)
     - **Value:** Get Value for Key → Dictionary: "Repeat Item", Key: `Hours`
     - **Type:** Select **Number** from the type menu
   
   - **Key:** `minute` (type: **Number**)
     - **Value:** Get Value for Key → Dictionary: "Repeat Item", Key: `Minutes`
     - **Type:** Select **Number** from the type menu
   
   - **Key:** `repeats` (type: **Boolean**)
     - **Value:** Get Value for Key → Dictionary: "Repeat Item", Key: `Repeats`
     - **Type:** Select **Boolean** from the type menu
   
   - **Key:** `repeat_days` (type: **Array**)
     - **Value:** Get Value for Key → Dictionary: "Repeat Item", Key: `Repeat Days`
     - **Type:** Select **Array** from the type menu
     - **NOTE:** If `Repeat Days` is empty or null, you can use the "If" action to check if it exists, or simply pass the value (Home Assistant will accept an empty array)
   
   - **Key:** `allows_snooze` (type: **Boolean**)
     - **Value:** Get Value for Key → Dictionary: "Repeat Item", Key: `Allows Snooze`
     - **Type:** Select **Boolean** from the type menu
   
   **Step 2.3:** At the end of the loop (before closing "Repeat with Each"), add **Add to Variable** action
   - **IMPORTANT:** On first use, click "New Variable" and name it "Formatted Alarms"
   - In the **Item** field, select the result from the "Dictionary" action (newly created alarm object)
   - **NOTE:** Make sure you use the same "Formatted Alarms" variable for all alarms in the loop - iOS will automatically create an array (Array) from all added elements
   
   **Summary of data types for each field:**
   - `alarm_id`: **Text**
   - `label`: **Text**
   - `enabled`: **Boolean**
   - `hour`: **Number**
   - `minute`: **Number**
   - `repeats`: **Boolean**
   - `repeat_days`: **Array**
   - `allows_snooze`: **Boolean**

3. **Call Service**
   - Action: "Call Service" (from Home Assistant Companion App)
   - Server: Select your Home Assistant server
   - Service: `iphone_alarms_sync.sync_alarms`
   - Data (Dictionary):
     - `phone_id`: enter your phone_id (e.g., "kuba_iphone_15_pro")
     - `alarms`: select the "Formatted Alarms" variable
     - **IMPORTANT:** If you see a red ✗ next to "Formatted Alarms", it means:
       1. The variable was not created correctly in the loop
       2. The variable is empty (no alarms)
       3. The variable is not an array (Array)
       - **Solution:** Check if in the "Repeat with Each" loop you use "Add to Variable" and if you select the same "Formatted Alarms" variable for all alarms

**Important notes:**
- "Find Alarms" returns alarm objects, but not in a format that Home Assistant can directly accept
- You must manually build a Dictionary for each alarm using the "Dictionary" action
- Key names in the alarm object from iOS may vary - use the debugging section to check exact names
- If any field doesn't exist in the alarm (e.g., `Repeat Days` is empty), you can pass an empty value or use the "If" action to check

**Notes:**
- You can find `phone_id` in the integration: Settings → Devices & Services → iPhone Alarms Sync → Configure → Shortcuts Setup
- **IMPORTANT:** "Find Alarms" does not return a ready-made object in the appropriate format - you must manually build a Dictionary for each alarm
- Use the "Dictionary" action (not "Get Dictionary from Input") to create a new alarm object
- **Exact key names in iOS Shortcuts:**
  - `URL` → use as `alarm_id` (or extract UUID from URL)
  - `Label` → `label`
  - `Is Enabled` → `enabled`
  - `Hours` → `hour`
  - `Minutes` → `minute`
  - `Repeats` → `repeats`
  - `Repeat Days` → `repeat_days`
  - `Allows Snooze` → `allows_snooze`

### 2. Alarm Goes Off

**Trigger:**
- Personal Automation → "Alarm" → "Goes Off"

**Actions:**
1. **Call Service**
   - Action: "Call Service" (from Home Assistant Companion App)
   - Service: `iphone_alarms_sync.report_alarm_event`
   - Data (Dictionary):
     ```json
     {
       "phone_id": "YOUR_PHONE_ID",
       "alarm_id": [Alarm ID from trigger],
       "event": "goes_off"
     }
     ```
   - In the `alarm_id` field, use the variable from the trigger (automatically available as "Alarm ID")

### 3. Alarm Snoozed

**Trigger:**
- Personal Automation → "Alarm" → "Is Snoozed"

**Actions:**
1. **Call Service**
   - Action: "Call Service" (from Home Assistant Companion App)
   - Service: `iphone_alarms_sync.report_alarm_event`
   - Data (Dictionary):
     ```json
     {
       "phone_id": "YOUR_PHONE_ID",
       "alarm_id": [Alarm ID from trigger],
       "event": "snoozed"
     }
     ```

### 4. Alarm Stopped

**Trigger:**
- Personal Automation → "Alarm" → "Is Stopped"

**Actions:**
1. **Call Service**
   - Action: "Call Service" (from Home Assistant Companion App)
   - Service: `iphone_alarms_sync.report_alarm_event`
   - Data (Dictionary):
     ```json
     {
       "phone_id": "YOUR_PHONE_ID",
       "alarm_id": [Alarm ID from trigger],
       "event": "stopped"
     }
     ```

## Creating Shortcuts

Shortcuts must be created in the iOS Shortcuts app and exported as `.shortcut` files.
These files are binary and cannot be created as text files.

**Steps to create the main shortcut:**

1. Open the **Shortcuts** app on iPhone/iPad
2. Go to the **Automation** tab (at the bottom)
3. Click **+** (Create Personal Automation)
4. Select **App** → **Clock** → **Is Closed** → **Next**
5. Click **Add Action**
6. Search and add **Find Alarms**
   - Optionally set condition "Is Enabled"
7. Click **+** to add another action
8. Search and add **Call Service** (from Home Assistant Companion App)
   - Select your server
   - In the **Service** field, enter: `iphone_alarms_sync.sync_alarms`
   - Enable **Show When Run** option (optional, for debugging)
9. In the **Data** section, click **Add Field** and add:
   - `phone_id`: enter your phone_id (e.g., "kuba_iphone_15_pro")
   - `alarms`: select the "Alarms" variable from the "Find Alarms" action
10. Click **Next** → **Done**

**Important:**
- Make sure Personal Automations are enabled in iOS Settings → Shortcuts → Advanced → Allow Running Automations
- After first run, you may receive a confirmation request - select "Allow"
- The shortcut will run automatically every time you close the Clock app

## Troubleshooting "Badly formed object" error

### Checking shortcut structure

Make sure the shortcut structure looks like this:

1. **Find Alarms**
2. **Repeat with Each** → Input: "Alarms"
   - Inside the loop:
     - **Dictionary** (with all alarm fields)
     - **Add to Variable** → Variable: "Formatted Alarms", Item: result from "Dictionary"
3. **End Repeat**
4. **Call Service**
   - Service: `iphone_alarms_sync.sync_alarms`
   - Data:
     - `phone_id`: "kuba_iphone_15_pro"
     - `alarms`: "Formatted Alarms" (variable, not directly Dictionary)

### Common errors

**Error 1: Red ✗ next to "Formatted Alarms"**
- **Cause:** Variable doesn't exist or is empty
- **Check:**
  - Is "Add to Variable" inside the loop (before "End Repeat")?
  - Are you using the same variable name "Formatted Alarms" for all alarms?
  - Does "Find Alarms" return any alarms? (may be empty if you don't have enabled alarms)

**Error 2: "Badly formed object around line X"**
- **Cause:** Dictionary is not built correctly or data types are invalid
- **Check:**
  - Do all fields have appropriate types (Text, Number, Boolean, Array)?
  - Is `repeat_days` of type Array (not Text)?
  - Are `enabled`, `repeats`, `allows_snooze` of type Boolean (not Text)?

**Error 3: Variable "Formatted Alarms" is not an array**
- **Cause:** You're not using "Add to Variable" correctly
- **Solution:** Make sure:
  1. "Add to Variable" is inside the "Repeat with Each" loop
  2. You use the same variable for all alarms
  3. iOS automatically creates an array from all added Dictionary items

## Troubleshooting "Badly formed object" error (details)

If you receive a **"Could Not Run Call Service"** error with message **"Badly formed object around line 3, column 12"**, it means the data from "Find Alarms" is not in the appropriate JSON format.

**Solution:**

iOS Shortcuts does not automatically pass alarms from "Find Alarms" in a format that Home Assistant can accept. You must manually transform the data:

1. **Find Alarms** (as usual)

2. **Repeat with Each**
   - Input: select "Alarms" from "Find Alarms"

3. **Inside the loop:**
   - **Get Dictionary from Input** → Input: "Repeat Item"
   - **Set Dictionary Value** → Dictionary: result from "Get Dictionary"
     - Add keys one by one:
       - `alarm_id`: use "Get Value for Key" → Dictionary: "Repeat Item", Key: `UUID` (or `ID`)
       - `label`: Get Value for Key → Key: `Label`
       - `enabled`: Get Value for Key → Key: `Enabled`
       - `hour`: Get Value for Key → Key: `Hour`
       - `minute`: Get Value for Key → Key: `Minute`
       - `repeats`: Get Value for Key → Key: `Repeats`
       - `repeat_days`: Get Value for Key → Key: `Repeat Days`
       - `allows_snooze`: Get Value for Key → Key: `Allows Snooze`

4. **Add to Variable** (at the end of the loop)
   - Create variable "Formatted Alarms"
   - Item: result from "Set Dictionary Value"

5. **Call Service**
   - Service: `iphone_alarms_sync.sync_alarms`
   - Data:
     - `phone_id`: your phone_id
     - `alarms`: select the "Formatted Alarms" variable

**Tip:** First use the debugging section to check the exact key names in the alarm (may vary depending on iOS version).

## Debugging data structure

To check what structure alarms returned by the "Find Alarms" action have, you can add debugging actions to the shortcut:

### Method 1: Quick Look (simplest)

1. In the shortcut, after the **Find Alarms** action, add **Quick Look** action
2. In the **Input** field, select the "Alarms" variable from the "Find Alarms" action
3. Run the shortcut - you'll see a preview of the data in visual format
4. You can scroll and check the structure of each alarm

### Method 2: Show Notification (for quick preview)

1. After the **Find Alarms** action, add **Show Notification** action
2. In the **Text** field, select the "Alarms" variable
3. Run the shortcut - you'll see the data in the notification
4. You can copy text from the notification

### Method 3: Checking the first alarm (detailed)

To see the exact structure of a single alarm:

1. After the **Find Alarms** action, add **Get Item from List** action
   - In the **List** field, select "Alarms"
   - In the **Index** field, enter `1` (first alarm)
2. Add **Get Dictionary from Input** action
   - In the **Input** field, select the result from the previous action
3. Add **Get Value for Key** action
   - In the **Dictionary** field, select the result from "Get Dictionary"
   - In the **Key** field, enter `alarm_id` (or other field you want to check)
4. Add **Show Notification** or **Quick Look** action
   - In the **Input** field, select the result from "Get Value"

### Method 4: Displaying all alarm keys

To see all available fields in the alarm:

1. After the **Find Alarms** action, add **Get Item from List** action (first alarm)
2. Add **Get Dictionary from Input** action
3. Add **Get Dictionary Value** action (without specifying a key - returns all keys)
4. Add **Show Notification** or **Quick Look** action

### Method 5: Formatting as text (for advanced users)

To see data in text format:

1. After the **Find Alarms** action, add **Text** action
2. In the text field, enter: `Alarms: [Alarms]`
   - Select the "Alarms" variable from the variable menu
3. Add **Show Notification** action
   - In the **Text** field, select the result from the "Text" action

### Example debugging shortcut

Create a separate test shortcut:

1. **Find Alarms** (without conditions, to see all)
2. **Get Item from List** → Index: `1` (first alarm)
3. **Quick Look** → Input: result from "Get Item"
4. **Get Dictionary from Input** → Input: result from "Get Item"
5. **Get Value for Key** → Key: `alarm_id`
6. **Show Notification** → Text: result from "Get Value"

Run this shortcut and check:
- Does the alarm have an `alarm_id` field?
- What other fields are available?
- What is the data format (string, number, boolean)?

### Checking the entire alarms array

To see how many alarms were found and their basic information:

1. After the **Find Alarms** action, add **Count** action
   - In the **Items** field, select "Alarms"
2. Add **Text** action
   - Enter: `Found [Count] alarms`
   - Select the "Count" variable from the menu
3. Add **Show Notification** action
   - In the **Text** field, select the result from "Text"

### Removing debugging actions

After checking the data structure:
1. Select debugging actions (tap and hold, select all)
2. Delete them (swipe left or use Delete option)
3. Leave only production actions: **Find Alarms** → **Call Service**

**Tip:** You can temporarily disable the **Call Service** action (toggle next to the action), so the shortcut only displays data without sending to Home Assistant.

## Testing Shortcuts

### Quick test without waiting for trigger

To test the shortcut without waiting for the Clock app to close:

1. Open the **Shortcuts** app on iPhone/iPad
2. Go to the **My Shortcuts** tab
3. Create a new shortcut (not Personal Automation):
   - Click **+** → **Create Shortcut**
   - Add **Find Alarms** action
   - Add **Call Service** action with configuration like in the main shortcut
4. Run the shortcut manually (click the play button)
5. Check results in Home Assistant (see below)

### Checking results in Home Assistant

**1. Check logs:**
- Settings → System → Logs
- Look for entries related to `iphone_alarms_sync`
- Errors will be visible if data format is invalid

**2. Check if alarms appeared:**
- Settings → Devices & Services → iPhone Alarms Sync → Configure
- Go to the **Alarms** tab
- You should see a list of synced alarms

**3. Check entities:**
- Settings → Devices & Services → iPhone Alarms Sync → Entities
- Entities should appear for each alarm:
  - `binary_sensor.{phone_id}_{alarm_id}_enabled`
  - `sensor.{phone_id}_{alarm_id}_time`
  - etc.

**4. Check Developer Tools:**
- Developer Tools → Services
- Search for `iphone_alarms_sync.sync_alarms`
- If the service is available, it means the integration is working correctly

### Manual service test (for advanced users)

You can manually call the service from Developer Tools to check the data format:

1. Developer Tools → Services
2. Select `iphone_alarms_sync.sync_alarms`
3. Fill in the data:
   ```yaml
   phone_id: "YOUR_PHONE_ID"
   alarms:
     - alarm_id: "TEST_ALARM_1"
       label: "Test Alarm"
       enabled: true
       hour: 7
       minute: 30
       repeats: true
       repeat_days: ["Monday", "Tuesday"]
       allows_snooze: true
   ```
4. Click **Call Service**
5. Check if the alarm appeared in the integration

### Troubleshooting

**Shortcut doesn't run automatically:**
- Check iOS Settings → Shortcuts → Advanced → Allow Running Automations
- Make sure Personal Automation is enabled
- Check if the trigger is configured correctly

**"Badly formed object" or "Could Not Run Call Service" error:**
- **Most common cause:** "Find Alarms" does not return a ready-made object in a format that Home Assistant can accept
- **Solution:** You must manually build a Dictionary for each alarm:
  1. Use "Repeat with Each" to go through all alarms
  2. For each alarm, use the "Dictionary" action (not "Get Dictionary from Input")
  3. Add all required keys (`alarm_id`, `label`, `enabled`, `hour`, `minute`, `repeats`, `repeat_days`, `allows_snooze`)
  4. Collect all Dictionary items into the "Formatted Alarms" variable using "Add to Variable"
  5. Use this variable in "Call Service"

**Error with red ✗ next to "Formatted Alarms":**
- **Cause:** Variable was not created correctly or is empty
- **Solution:**
  1. Check if in the "Repeat with Each" loop you use the "Add to Variable" action
  2. Make sure that on first use you clicked "New Variable" and named it "Formatted Alarms"
  3. Make sure you use the same "Formatted Alarms" variable for all alarms
  4. Check if "Add to Variable" is inside the loop (before "End Repeat")
  5. Check if "Find Alarms" returns any alarms (may be empty if you don't have enabled alarms)
- Check the data structure using the debugging section to find exact key names
- Make sure each alarm has an `alarm_id` field (use `URL` from iOS)

**Error in Home Assistant logs:**
- Check data format - `alarms` must be an array of objects (list of dictionaries)
- Each alarm must have an `alarm_id` field
- Check if `phone_id` is correct

**Alarms don't appear:**
- Check Home Assistant logs
- Make sure `phone_id` in the shortcut matches `phone_id` in the integration
- Check if the "Find Alarms" action returns data (enable "Show When Run" in the shortcut)

**Alarm data format:**
iOS automatically formats alarms from the "Find Alarms" action. Each alarm should contain:
- `alarm_id` (required) - unique alarm identifier
- `label` (optional) - alarm name
- `enabled` (optional) - whether alarm is enabled
- `hour` (optional) - hour (0-23)
- `minute` (optional) - minute (0-59)
- `repeats` (optional) - whether alarm repeats
- `repeat_days` (optional) - repeat days (e.g., ["Monday", "Tuesday"])
- `allows_snooze` (optional) - whether alarm allows snooze

## Exporting Shortcuts

Users should:
1. Create shortcuts in iOS Shortcuts app
2. Share/export as `.shortcut` files
3. Import into this repository or share via iCloud links
