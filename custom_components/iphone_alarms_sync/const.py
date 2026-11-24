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
# Tuples keep the order shown in Home Assistant, the same as in iOS.
ALARM_EVENTS = (EVENT_GOES_OFF, EVENT_SNOOZED, EVENT_STOPPED)
SLEEP_EVENTS = (EVENT_WIND_DOWN_STARTS, EVENT_BEDTIME_STARTS, EVENT_WAKING_UP)

# Which alarm a device trigger listens to; "any" and "wakeup" are also event scopes.
TRIGGER_SUBTYPE_ALARM = "alarm"
TRIGGER_SUBTYPE_ANY = "any"
TRIGGER_SUBTYPE_WAKEUP = "wakeup"


PLATFORMS = ["binary_sensor", "event", "sensor", "switch"]

SHORTCUT_SYNC_URL = "https://www.icloud.com/shortcuts/f8015b2fa07f4c4cbab8126816137ff5"
SHORTCUT_ALARM_EVENT_URL = (
    "https://www.icloud.com/shortcuts/c200af1ee622472aa45fd037c24ad0e7"
)
SHORTCUT_DEVICE_EVENT_URL = (
    "https://www.icloud.com/shortcuts/1024bb19477e425e9f0ae8a8a04dfa7c"
)

DOCS_ESTIMATED_URL = "https://github.com/Jozwiaczek/iphone-alarms-sync/blob/main/docs/shortcuts.md#estimated-goes-off"
DOCS_TROUBLESHOOTING_URL = "https://github.com/Jozwiaczek/iphone-alarms-sync/blob/main/docs/shortcuts.md#troubleshooting"

# A phone that sent nothing for this long likely has a broken shortcut.
STALE_AFTER = timedelta(days=7)
STALE_CHECK_INTERVAL = timedelta(hours=12)
# Time the "goes off" shortcut gets to reach HA before the alarm counts as missed.
MISSED_EVENT_GRACE = timedelta(minutes=5)
# The dashboard card, served by the integration and loaded on every dashboard.
CARD_PATH = "frontend/iphone-alarms-card.js"
CARD_URL = f"/{DOMAIN}/iphone-alarms-card.js"
