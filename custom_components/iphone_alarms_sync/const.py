from datetime import timedelta

DOMAIN = "iphone_alarms_sync"

CONF_PHONE_NAME = "phone_name"
CONF_PHONE_ID = "phone_id"
CONF_MOBILE_APP_DEVICE = "mobile_app_device"
CONF_MOBILE_APP_DEVICE_ID = "mobile_app_device_id"
CONF_ALARMS = "alarms"
CONF_ALARM_ID = "alarm_id"
CONF_LABEL = "label"
CONF_ICON = "icon"
CONF_ENABLED = "enabled"
CONF_HOUR = "hour"
CONF_MINUTE = "minute"
CONF_REPEATS = "repeats"
CONF_REPEAT_DAYS = "repeat_days"
CONF_ALLOWS_SNOOZE = "allows_snooze"
CONF_SNOOZE_TIME = "snooze_time"
CONF_SYNCED_AT = "synced_at"
CONF_EVENT = "event"
CONF_EVENT_TYPE = "event_type"
CONF_EVENT_ID = "event_id"
CONF_OCCURRED_AT = "occurred_at"
CONF_LAST_SYNC = "last_sync"
CONF_LAST_EVENT_GOES_OFF_AT = "last_event_goes_off_at"
CONF_LAST_EVENT_SNOOZED_AT = "last_event_snoozed_at"
CONF_LAST_EVENT_STOPPED_AT = "last_event_stopped_at"
CONF_LAST_OCCURRENCE_DATETIME = "last_occurrence_datetime"
CONF_LAST_ALARM_DATETIME = "last_alarm_datetime"
CONF_LAST_ALARM_ID = "last_alarm_id"
CONF_TOTAL_ALARMS = "total_alarms"
CONF_ENABLED_ALARMS = "enabled_alarms"
CONF_DISABLED_ALARMS = "disabled_alarms"
CONF_NEXT_ALARM_TIME = "next_alarm_time"
CONF_NEXT_ALARM_LABEL = "next_alarm_label"
CONF_SYNC_DISABLED_ALARMS = "sync_disabled_alarms"
CONF_MISSED_ALARM_AT = "missed_alarm_at"
CONF_WAKEUP_LAST_EVENT_GOES_OFF_AT = "wakeup_last_event_goes_off_at"
CONF_WAKEUP_LAST_EVENT_SNOOZED_AT = "wakeup_last_event_snoozed_at"
CONF_WAKEUP_LAST_EVENT_STOPPED_AT = "wakeup_last_event_stopped_at"
CONF_ANY_LAST_EVENT_GOES_OFF_AT = "any_last_event_goes_off_at"
CONF_ANY_LAST_EVENT_SNOOZED_AT = "any_last_event_snoozed_at"
CONF_ANY_LAST_EVENT_STOPPED_AT = "any_last_event_stopped_at"
CONF_BEDTIME_LAST_EVENT_AT = "bedtime_last_event_at"
CONF_WAKING_UP_LAST_EVENT_AT = "waking_up_last_event_at"
CONF_WIND_DOWN_LAST_EVENT_AT = "wind_down_last_event_at"

EVENT_ALARM_EVENT = "iphone_alarms_sync_alarm_event"

EVENT_GOES_OFF = "goes_off"
EVENT_SNOOZED = "snoozed"
EVENT_STOPPED = "stopped"
EVENT_BEDTIME_STARTS = "bedtime_starts"
EVENT_WAKING_UP = "waking_up"
EVENT_WIND_DOWN_STARTS = "wind_down_starts"

DEFAULT_ICON = "mdi:alarm"
DEFAULT_SNOOZE_TIME = 9

PLATFORMS = ["binary_sensor", "number", "sensor"]

SHORTCUT_SYNC_URL = "https://www.icloud.com/shortcuts/3a7ef812167b410f8b429de5bb07587e"
SHORTCUT_ALARM_EVENT_URL = (
    "https://www.icloud.com/shortcuts/0b78900623dd4269a50fc481971ecea5"
)
SHORTCUT_DEVICE_EVENT_URL = (
    "https://www.icloud.com/shortcuts/af592e425fd04cdbb4835f96f35ed793"
)

SHORTCUT_ICLOUD_URL = SHORTCUT_SYNC_URL

DOCS_TROUBLESHOOTING_URL = "https://github.com/Jozwiaczek/iphone-alarms-sync/blob/main/docs/shortcuts.md#troubleshooting"

# A phone that sent nothing for this long likely has a broken shortcut.
STALE_AFTER = timedelta(days=7)
STALE_CHECK_INTERVAL = timedelta(hours=12)
# Time the "goes off" shortcut gets to reach HA before the alarm counts as missed.
MISSED_EVENT_GRACE = timedelta(minutes=5)
