// Device IDs look like Home Assistant's: hex, often starting with a digit.
// A fake `hass` for the dashboard card, shared by the tests, the preview page
// and the screenshot script. Times are in Europe/Warsaw, "now" is 10:00 on a Tuesday.

export const NOW = new Date("2026-11-24T09:00:00Z");
export const TIME_ZONE = "Europe/Warsaw";
const DOMAIN = "iphone_alarms_sync";
const WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
const EVERY_DAY = [...WEEKDAYS, "Saturday", "Sunday"];

const MORNING = [
  "Bedroom lights on",
  "Coffee machine",
  "Open the blinds",
  "Heat the bathroom",
  "Play the news",
  "Kitchen lights",
  "Thermostat to day",
  "Unlock the front door",
  "Start the dishwasher",
  "Turn off night mode",
  "Wake the kids",
  "Weather on the TV",
  "Garage heater",
  "Hallway lights",
  "Feed the cat",
  "Radio in the bathroom",
  "Water the plants",
  "Robot vacuum",
  "Morning playlist",
  "Read the calendar out loud",
];

export const PHONE = {
  id: "0f3e9a1b2c4d5e6f",
  slug: "johns_iphone",
  name: "John's iPhone",
  alarms: [
    {
      id: "1a2b3c4d5e6f7a8b",
      label: "1️⃣ Pierwszy",
      hour: 7,
      minute: 35,
      repeat_days: EVERY_DAY,
      next: "2026-11-25T06:35:00Z",
      last: "2026-11-24T06:35:00Z",
      events: {
        last_event_goes_off_at: "2026-11-24T06:35:00Z",
        last_event_snoozed_at: "2026-11-24T06:44:00Z",
        last_event_stopped_at: "2026-11-24T06:52:00Z",
      },
      automations: ["automation.bedroom_lights_on", "automation.coffee_machine", "automation.open_the_blinds"],
    },
    {
      id: "2b3c4d5e6f7a8b9c",
      label: "⚠️ Drugi",
      hour: 7,
      minute: 40,
      repeat_days: WEEKDAYS,
      next: "2026-11-25T06:40:00Z",
      // Rang today, but only yesterday's "goes off" reached Home Assistant.
      last: "2026-11-24T06:40:00Z",
      events: { last_event_goes_off_at: "2026-11-23T06:40:00Z" },
      automations: MORNING.map((name) => `automation.${slug(name)}`),
    },
    { id: "3c4d5e6f7a8b9c0d", label: "Test 2", hour: 16, minute: 43, repeat_days: ["Tuesday", "Wednesday"], next: "2026-11-24T15:43:00Z", allows_snooze: false },
    { id: "4d5e6f7a8b9c0d1e", label: "Gym", hour: 6, minute: 0, enabled: false, repeat_days: ["Saturday", "Sunday"], automations: ["script.good_morning"] },
  ],
};

export const SECOND_PHONE = {
  id: "5e6f7a8b9c0d1e2f",
  slug: "annas_iphone",
  name: "Anna's iPhone",
  alarms: [{ id: "6f7a8b9c0d1e2f3a", label: "Work", hour: 6, minute: 45, repeat_days: WEEKDAYS }],
};

const OFF = new Set(["automation.open_the_blinds", "automation.garage_heater"]);

function slug(text) {
  return text.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
}

function state(entityId, value, attributes = {}) {
  return { entity_id: entityId, state: value ?? "unknown", attributes, last_changed: "", last_updated: "" };
}

/** Build `hass`. `callWS` answers search/related from the fixtures unless replaced. */
export function makeHass({ phones = [PHONE], locale = {}, callWS } = {}) {
  const hass = {
    states: {},
    entities: {},
    devices: {},
    config: { time_zone: TIME_ZONE },
    locale: { language: "en", time_format: "24", time_zone: "server", ...locale },
    user: { is_admin: true },
    related: {},
  };
  const add = (entityId, deviceId, key, value, attributes) => {
    hass.entities[entityId] = { entity_id: entityId, device_id: deviceId, platform: DOMAIN, translation_key: key };
    hass.states[entityId] = state(entityId, value, attributes);
  };
  const addRelated = (target, ids = []) => {
    hass.related[target] = ids;
    for (const id of ids) {
      const name = id === "script.good_morning" ? "Good morning" : null;
      const label = name ?? MORNING.find((n) => `automation.${slug(n)}` === id) ?? id;
      hass.states[id] = state(id, OFF.has(id) ? "off" : "on", { friendly_name: label });
    }
  };
  for (const phone of phones) {
    hass.devices[phone.id] = { id: phone.id, name: phone.name, model: null, via_device_id: "mobile_app" };
    // The card finds a phone through its entities.
    add(`sensor.${phone.slug}_last_sync`, phone.id, "last_sync", "2026-11-24T08:00:00Z");
    for (const alarm of phone.alarms) {
      const base = `${phone.slug}_${slug(alarm.label)}`;
      hass.devices[alarm.id] = { id: alarm.id, name: `${phone.name} ${alarm.label}`, model: "Alarm", via_device_id: phone.id };
      add(`sensor.${base}_alarm_id`, alarm.id, "alarm_id", alarm.id, {
        label: alarm.label,
        time: `${String(alarm.hour).padStart(2, "0")}:${String(alarm.minute).padStart(2, "0")}`,
        hour: alarm.hour,
        minute: alarm.minute,
        enabled: alarm.enabled ?? true,
        repeats: Boolean(alarm.repeat_days?.length),
        repeat_days: alarm.repeat_days ?? [],
        allows_snooze: alarm.allows_snooze ?? true,
      });
      add(`sensor.${base}_next_occurrence_datetime`, alarm.id, "next_occurrence_datetime", alarm.next);
      add(`sensor.${base}_last_occurrence_datetime`, alarm.id, "last_occurrence_datetime", alarm.last);
      for (const key of ["last_event_goes_off_at", "last_event_snoozed_at", "last_event_stopped_at"]) {
        add(`sensor.${base}_${key}`, alarm.id, key, alarm.events?.[key]);
      }
      addRelated(alarm.id, alarm.automations);
    }
  }
  hass.callWS = callWS ?? (async ({ item_id: id }) => ({ automation: hass.related[id]?.filter((e) => e.startsWith("automation.")) ?? [], script: hass.related[id]?.filter((e) => e.startsWith("script.")) ?? [] }));
  return hass;
}

/** A copy of `hass` with one state replaced, as HA does on a state change. */
export function withState(hass, entityId, value, attributes) {
  const old = hass.states[entityId];
  return {
    ...hass,
    states: { ...hass.states, [entityId]: state(entityId, value, attributes ?? old?.attributes) },
  };
}
