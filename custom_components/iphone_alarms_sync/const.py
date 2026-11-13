from datetime import timedelta

DOMAIN = "iphone_alarms_sync"

# Config entry data and action fields.
CONF_PHONE_NAME = "phone_name"
CONF_PHONE_ID = "phone_id"
CONF_MOBILE_APP_DEVICE_ID = "mobile_app_device_id"
CONF_SYNC_DISABLED_ALARMS = "sync_disabled_alarms"
CONF_ALARMS = "alarms"
CONF_ALARM_ID = "alarm_id"
CONF_ENABLED = "enabled"
CONF_EVENT = "event"

EVENT_ALARM_EVENT = "iphone_alarms_sync_alarm_event"

EVENT_GOES_OFF = "goes_off"
EVENT_SNOOZED = "snoozed"
EVENT_STOPPED = "stopped"
EVENT_BEDTIME_STARTS = "bedtime_starts"
EVENT_WAKING_UP = "waking_up"
EVENT_WIND_DOWN_STARTS = "wind_down_starts"

DEFAULT_SNOOZE_TIME = 9

PLATFORMS = ["binary_sensor", "number", "sensor"]

SHORTCUT_SYNC_URL = "https://www.icloud.com/shortcuts/3a7ef812167b410f8b429de5bb07587e"
SHORTCUT_ALARM_EVENT_URL = (
    "https://www.icloud.com/shortcuts/0b78900623dd4269a50fc481971ecea5"
)
SHORTCUT_DEVICE_EVENT_URL = (
    "https://www.icloud.com/shortcuts/af592e425fd04cdbb4835f96f35ed793"
)

DOCS_TROUBLESHOOTING_URL = "https://github.com/Jozwiaczek/iphone-alarms-sync/blob/main/docs/shortcuts.md#troubleshooting"

# A phone that sent nothing for this long likely has a broken shortcut.
STALE_AFTER = timedelta(days=7)
STALE_CHECK_INTERVAL = timedelta(hours=12)
# Time the "goes off" shortcut gets to reach HA before the alarm counts as missed.
MISSED_EVENT_GRACE = timedelta(minutes=5)
