// iPhone Alarms card: a read-only list of the alarms that iPhone Alarms Sync
// keeps, laid out like the Alarms tab of the iOS Clock app.
// Plain web component, no build step: Home Assistant loads this file as is.

const DOMAIN = "iphone_alarms_sync";
const CARD = "iphone-alarms-card";
const PREVIEW_LIMIT = 5;
const DAY_MS = 86400000;
const WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
// In the order the card shows them.
const BOOLEANS = ["show_sleep", "show_other", "show_disabled", "show_last_events", "show_automations"];
const ALARM_EVENTS = [
  ["last_event_goes_off_at", "Went off"],
  ["last_event_snoozed_at", "Snoozed"],
  ["last_event_stopped_at", "Stopped"],
];
const SLEEP_EVENTS = [
  ["wind_down_last_event_at", "Wind down"],
  ["wakeup_last_event_goes_off_at", "Went off"],
  ["wakeup_last_event_snoozed_at", "Snoozed"],
  ["wakeup_last_event_stopped_at", "Stopped"],
  ["waking_up_last_event_at", "Waking up"],
];
const ALARM_KEYS = ["alarm_id", "next_occurrence_datetime", ...ALARM_EVENTS.map(([key]) => key)];
const PHONE_KEYS = ["bedtime_last_event_at", ...SLEEP_EVENTS.map(([key]) => key)];
// The phone's event entities that sleep automations use. Searching the phone
// device instead would also return every alarm's automations.
const SLEEP_TARGETS = ["wakeup_alarm", "sleep"];
const BED_ICON =
  "M19,7H11V14H3V5H1V20H3V17H21V20H23V11A4,4 0 0,0 19,7M7,13A3,3 0 0,0 10,10A3,3 0 0,0 7,7A3,3 0 0,0 4,10A3,3 0 0,0 7,13Z";

const LABELS = {
  title: "Title",
  devices: "Phones or alarms",
  show_sleep: "Show Sleep | Wake Up",
  show_other: "Show other alarms",
  show_disabled: "Show alarms that are off",
  show_automations: "Show automations of an alarm",
  show_last_events: "Show last events of an alarm",
};
const HELPERS = {
  title: "Leave empty for a more compact card.",
  devices: "Pick phones (all their alarms) or single alarms. Leave empty to show every alarm.",
  show_sleep: "Last bedtime, wake-up and how long you slept. Needs the Device Event shortcut.",
  show_other: "Every alarm of a phone besides the Wake-Up alarm. Alarms picked one by one always show.",
  show_disabled: "Shown grayed out, with a crossed-out clock.",
  show_automations: "Tap an alarm to see the automations and scripts that use it.",
  show_last_events: "Tap an alarm to see when it last went off, was snoozed or stopped.",
};

/** Check the card config and fill in the defaults. Throws on a wrong type. */
export function validateConfig(config) {
  if (!config || typeof config !== "object" || Array.isArray(config)) {
    throw new Error("Invalid configuration");
  }
  if (config.title !== undefined && typeof config.title !== "string") {
    throw new Error("'title' must be text");
  }
  const devices = config.devices ?? [];
  if (!Array.isArray(devices) || devices.some((id) => typeof id !== "string")) {
    throw new Error("'devices' must be a list of device IDs");
  }
  for (const key of BOOLEANS) {
    if (config[key] !== undefined && typeof config[key] !== "boolean") {
      throw new Error(`'${key}' must be true or false`);
    }
  }
  return {
    ...config,
    devices,
    ...Object.fromEntries(BOOLEANS.map((key) => [key, config[key] ?? true])),
  };
}

/** The repeat text iOS shows under an alarm: "Every day", "Weekdays", "Tue and Wed". */
export function describeRepeat(days) {
  const set = new Set(days ?? []);
  const picked = WEEK.filter((day) => set.has(day));
  const key = picked.map((day) => day.slice(0, 2)).join("");
  if (picked.length === 7) return "Every day";
  if (key === "MoTuWeThFr") return "Weekdays";
  if (key === "SaSu") return "Weekends";
  if (picked.length === 1) return `Every ${picked[0]}`;
  const short = picked.map((day) => day.slice(0, 3));
  if (short.length === 2) return `${short[0]} and ${short[1]}`;
  return short.join(", ");
}

/** Time settings of the user's profile, as Home Assistant itself applies them. */
export function timeContext(hass, now = new Date()) {
  const locale = hass.locale ?? {};
  const format = locale.time_format;
  let h12 = format === "12";
  if (format !== "12" && format !== "24") {
    const language = format === "system" ? undefined : locale.language;
    const cycle = new Intl.DateTimeFormat(language, { hour: "numeric" }).resolvedOptions().hourCycle;
    h12 = cycle === "h11" || cycle === "h12";
  }
  const timeZone = locale.time_zone === "server" ? hass.config?.time_zone : undefined;
  return { h12, timeZone, now };
}

/** Clock time, as the Clock app writes it: "07:35" or "7:35 AM". */
export function formatClock(hour, minute, ctx) {
  const mm = String(minute).padStart(2, "0");
  if (!ctx.h12) return { time: `${String(hour).padStart(2, "0")}:${mm}`, period: "" };
  return { time: `${hour % 12 || 12}:${mm}`, period: hour < 12 ? "AM" : "PM" };
}

function parts(date, timeZone) {
  const out = {};
  const fmt = new Intl.DateTimeFormat("en-US", {
    timeZone,
    year: "numeric",
    month: "numeric",
    day: "numeric",
    hour: "numeric",
    minute: "numeric",
    hourCycle: "h23",
  });
  for (const { type, value } of fmt.formatToParts(date)) out[type] = Number(value);
  return out;
}

const dayNumber = (p) => Date.UTC(p.year, p.month - 1, p.day) / DAY_MS;

function parseTime(value) {
  if (!value || value === "unknown" || value === "unavailable") return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

/** A moment near now, short: "07:35", "Yesterday 07:35", "Tomorrow 07:35", "Mon 07:35" or "Nov 12". */
export function formatEventTime(value, ctx, today = "") {
  const date = parseTime(value);
  if (!date) return null;
  const at = parts(date, ctx.timeZone);
  const days = dayNumber(parts(ctx.now, ctx.timeZone)) - dayNumber(at);
  const clock = formatClock(at.hour, at.minute, ctx);
  const time = clock.period ? `${clock.time} ${clock.period}` : clock.time;
  const options = { timeZone: ctx.timeZone };
  if (days === 0) return `${today}${time}`;
  if (days === 1) return `Yesterday ${time}`;
  if (days === -1) return `Tomorrow ${time}`;
  if (Math.abs(days) < 7) return `${date.toLocaleDateString("en-US", { ...options, weekday: "short" })} ${time}`;
  return date.toLocaleDateString("en-US", { ...options, month: "short", day: "numeric" });
}

function formatDay(date, ctx) {
  const text = formatEventTime(date.toISOString(), ctx, "Today ");
  return text.replace(/\s\d{1,2}:\d\d.*$/, "");
}

/** The Sleep row from the last bedtime and wake-up events, or null without them. */
export function sleepSummary(bedtimeValue, wakeValue, ctx) {
  let bedtime = parseTime(bedtimeValue);
  const wake = parseTime(wakeValue);
  if (!bedtime && !wake) return null;
  const clock = (date) => {
    const at = parts(date, ctx.timeZone);
    return formatClock(at.hour, at.minute, ctx);
  };
  // Bedtime belongs to this wake-up only when it came less than a day before it;
  // a bedtime from tonight starts the next night.
  const slept = bedtime && wake ? wake - bedtime : 0;
  const paired = slept > 0 && slept < DAY_MS;
  if (wake && !paired) bedtime = null;
  let duration = null;
  if (paired) {
    const minutes = Math.round(slept / 60000);
    const hours = Math.floor(minutes / 60);
    duration = [hours && `${hours} hr`, minutes % 60 && `${minutes % 60} min`].filter(Boolean).join(" ") || null;
  }
  return {
    main: clock(wake ?? bedtime),
    isWake: Boolean(wake),
    bedtime: bedtime && wake ? clock(bedtime) : null,
    duration,
    day: formatDay(wake ?? bedtime, ctx),
  };
}

/** Phones and alarms from the registries; rebuilt only when they change. */
export function buildIndex(hass) {
  const devices = hass.devices ?? {};
  const byDevice = new Map();
  for (const entity of Object.values(hass.entities ?? {})) {
    if (entity.platform !== DOMAIN || !entity.device_id || !entity.translation_key) continue;
    if (!byDevice.has(entity.device_id)) byDevice.set(entity.device_id, {});
    byDevice.get(entity.device_id)[entity.translation_key] = entity.entity_id;
  }
  const phones = new Map();
  const alarms = new Map();
  for (const [id, entities] of byDevice) {
    const device = devices[id];
    if (!device) continue;
    const name = device.name_by_user || device.name || "";
    if (device.model === "Alarm") alarms.set(id, { id, phoneId: device.via_device_id, name, entities });
    else phones.set(id, { id, name, entities, alarms: [] });
  }
  for (const alarm of alarms.values()) phones.get(alarm.phoneId)?.alarms.push(alarm);
  return { phones, alarms };
}

function readAlarm(alarm, states) {
  const state = states[alarm.entities.alarm_id];
  const attrs = state?.attributes;
  if (!attrs || state.state === "unavailable" || !Number.isInteger(attrs.hour)) return null;
  return {
    key: alarm.id,
    entities: alarm.entities,
    label: attrs.label || "Alarm",
    hour: attrs.hour,
    minute: attrs.minute ?? 0,
    enabled: attrs.enabled !== false,
    allowsSnooze: attrs.allows_snooze !== false,
    repeat: attrs.repeats ? describeRepeat(attrs.repeat_days) : "",
  };
}

/** What the card shows: phones with their alarms, after the config's filters. */
export function selectAlarms(index, config, states) {
  const picked = new Map();
  let missing = 0;
  const pick = (phoneId, whole, alarmId) => {
    if (!picked.has(phoneId)) picked.set(phoneId, { whole: false, alarmIds: new Set() });
    const entry = picked.get(phoneId);
    entry.whole ||= whole;
    if (alarmId) entry.alarmIds.add(alarmId);
  };
  if (!config.devices.length) for (const id of index.phones.keys()) pick(id, true);
  for (const id of config.devices) {
    const alarm = index.alarms.get(id);
    if (index.phones.has(id)) pick(id, true);
    else if (alarm && index.phones.has(alarm.phoneId)) pick(alarm.phoneId, false, id);
    else missing += 1;
  }
  const groups = [];
  for (const [phoneId, { whole, alarmIds }] of picked) {
    const phone = index.phones.get(phoneId);
    const alarms = phone.alarms
      .filter((alarm) => whole || alarmIds.has(alarm.id))
      .map((alarm) => readAlarm(alarm, states))
      .filter((alarm) => alarm && (config.show_disabled || alarm.enabled))
      .sort((a, b) => a.hour * 60 + a.minute - (b.hour * 60 + b.minute) || a.label.localeCompare(b.label));
    groups.push({ phone, whole, alarms });
  }
  groups.sort((a, b) => a.phone.name.localeCompare(b.phone.name));
  return { groups, missing };
}

/** Automations and scripts on the related list, sorted by name; gone ones dropped. */
export function relatedItems(ids, states) {
  return ids
    .filter((id) => states[id])
    .map((id) => ({
      id,
      name: states[id].attributes?.friendly_name || id,
      // A script is "off" whenever it is not running; only automations get turned off.
      off: id.startsWith("automation.") && states[id].state === "off",
      script: id.startsWith("script."),
    }))
    .sort((a, b) => a.name.localeCompare(b.name));
}

const escape = (value) =>
  String(value).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

const bed = () => `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="${BED_ICON}"/></svg>`;
const LIST_ICON = "M7,5H21V7H7V5M7,13V11H21V13H7M4,4.5A1.5,1.5 0 0,1 5.5,6A1.5,1.5 0 0,1 4,7.5A1.5,1.5 0 0,1 2.5,6A1.5,1.5 0 0,1 4,4.5M4,10.5A1.5,1.5 0 0,1 5.5,12A1.5,1.5 0 0,1 4,13.5A1.5,1.5 0 0,1 2.5,12A1.5,1.5 0 0,1 4,10.5M7,19V17H21V19H7M4,16.5A1.5,1.5 0 0,1 5.5,18A1.5,1.5 0 0,1 4,19.5A1.5,1.5 0 0,1 2.5,18A1.5,1.5 0 0,1 4,16.5Z";
// One icon for two facts: the clock says whether the alarm is on, the arrow in its corner whether the row is open.
const clockIcon = (state, label) =>
  `<svg class="status ${state}" viewBox="0 0 32 32" ` +
  (label ? `role="img" aria-label="${label}"><title>${label}</title>` : `aria-hidden="true">`) +
  `<path class="bells" d="M4.5 9.5a5.5 5.5 0 0 1 6-6M27.5 9.5a5.5 5.5 0 0 0-6-6"/>` +
  `<circle class="face" cx="16" cy="17" r="10"/>` +
  `<path class="hands" d="M16 11.5V17l3.5 2.5"/>` +
  `<path class="slash" d="M5 5l22 24"/>` +
  `<g class="badge"><circle cx="25.5" cy="25.5" r="6"/><path d="M23 24.5l2.5 2.5 2.5-2.5"/></g></svg>`;
const clockHtml = ({ time, period }) => `${escape(time)}${period ? `<span class="period">${period}</span>` : ""}`;

const STYLE = `
:host { display: block; }
ha-card { overflow: hidden; container-type: inline-size; }
.content { padding-block: 4px 12px; }
.title { margin: 0; padding: 16px 16px 0; font-size: 1.5rem; font-weight: 700; line-height: 1.2; color: var(--primary-text-color); }
.phone { padding: 16px 16px 0; font-size: 0.8125rem; font-weight: 600; letter-spacing: 0.02em; text-transform: uppercase; color: var(--secondary-text-color); }
.section { padding-inline: 16px; }
/* Space between Sleep | Wake Up and Other, as in the Clock app. */
.section + .section { margin-top: 20px; }
.section-header { display: flex; align-items: center; gap: 8px; margin: 0; padding: 16px 0 8px; font-size: 1.125rem; font-weight: 700; color: var(--primary-text-color); border-bottom: 1px solid var(--divider-color); }
.section-header svg { width: 22px; height: 22px; fill: var(--iphone-alarms-accent, #ff9f0a); }
.item { border-bottom: 1px solid var(--divider-color); }
.section:last-child .item:last-child { border-bottom: 0; }
.row { display: flex; align-items: center; gap: 12px; width: 100%; margin: 0; padding: var(--iphone-alarms-row-padding, 10px 0 12px); border: 0; background: none; color: inherit; font: inherit; text-align: start; cursor: pointer; }
button:focus-visible { outline: 2px solid var(--primary-color); outline-offset: -2px; border-radius: 6px; }
.main { flex: 1; min-width: 0; }
.time { display: block; font-size: var(--iphone-alarms-time-size, 2.5rem); font-weight: var(--iphone-alarms-time-weight, 300); line-height: 1.1; font-variant-numeric: tabular-nums; letter-spacing: -0.01em; color: var(--primary-text-color); }
.period { margin-inline-start: 3px; font-size: 0.45em; font-weight: 400; }
.subtitle { display: flex; align-items: center; gap: 6px; margin-top: 4px; overflow: hidden; font-size: 0.9375rem; line-height: 1.35; white-space: nowrap; color: var(--primary-text-color); }
.subtitle span { overflow: hidden; text-overflow: ellipsis; }
.subtitle svg { flex: none; width: 16px; height: 16px; fill: var(--iphone-alarms-accent, #ff9f0a); }
.off .main { opacity: var(--iphone-alarms-disabled-opacity, 0.45); }
.status { flex: none; width: 36px; height: 36px; overflow: visible; fill: none; stroke: var(--secondary-text-color); stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
.status.on { --clock: var(--iphone-alarms-on-color, #34c759); }
.status.sleep { --clock: var(--iphone-alarms-accent, #ff9f0a); }
.status.on .bells, .status.sleep .bells { stroke: var(--clock); }
.status.on .face, .status.sleep .face { fill: var(--clock); stroke: var(--clock); }
.status.on .hands, .status.sleep .hands { stroke: #fff; }
.status .slash { display: none; }
.status.off .slash { display: inline; }
.status .badge circle { fill: var(--ha-card-background, var(--card-background-color, #fff)); stroke: var(--divider-color); stroke-width: 1.5; }
.status .badge path { stroke: var(--primary-text-color); stroke-width: 1.75; transform-box: view-box; transform-origin: 25.5px 25.75px; transition: transform 0.2s; }
[aria-expanded="true"] .status .badge path { transform: rotate(180deg); }
.details { margin: 0 0 14px; padding: 12px 14px 4px; border-radius: 12px; font-size: 0.875rem; line-height: 1.35; color: var(--secondary-text-color); background: var(--iphone-alarms-panel-color, rgba(127, 127, 127, 0.1)); }
.details p { margin: 4px 0 10px; }
.details .note { margin-top: 12px; font-size: 0.8125rem; }
.info { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 8px 16px; margin: 0 0 10px; }
.info dt { color: var(--secondary-text-color); }
.info dd { margin: 0; overflow-wrap: anywhere; color: var(--primary-text-color); }
.label { margin: 16px 0 2px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.03em; }
.automation, .more, .link { display: flex; align-items: center; gap: 8px; width: 100%; margin: 0; padding: 11px 0; border: 0; border-bottom: 1px solid var(--divider-color); background: none; color: var(--primary-text-color); font: inherit; font-size: 0.9375rem; text-align: start; cursor: pointer; }
.automation .name, .link .name { flex: 1; min-width: 0; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.automation.disabled .name { opacity: 0.5; }
.automation::after, .link::after { content: ""; flex: none; width: 6px; height: 6px; margin-inline-end: 4px; border: solid var(--secondary-text-color); border-width: 2px 2px 0 0; transform: rotate(45deg); }
:host([dir="rtl"]) .automation::after, :host([dir="rtl"]) .link::after { transform: rotate(-135deg); }
.tag { flex: none; font-size: 0.75rem; color: var(--secondary-text-color); }
.more, .link { border-bottom: 0; color: var(--primary-color); }
.link svg { flex: none; width: 18px; height: 18px; fill: currentColor; }
.details > :last-child { border-bottom: 0; }
.empty { padding: 16px; color: var(--secondary-text-color); }
.warning { margin: 12px 16px 0; padding: 8px 12px; border-radius: 8px; font-size: 0.8125rem; color: var(--primary-text-color); background: rgba(var(--rgb-warning-color, 255, 166, 0), 0.15); }
@container (max-width: 300px) {
  .time { font-size: var(--iphone-alarms-time-size, 2rem); }
  .subtitle { font-size: 0.8125rem; flex-wrap: wrap; white-space: normal; }
  .subtitle span { overflow: visible; }
}
@media (prefers-reduced-motion: reduce) { .status .badge path { transition: none; } }
`;

class IPhoneAlarmsCard extends HTMLElement {
  static getConfigForm() {
    return {
      schema: [
        { name: "title", selector: { text: {} } },
        { name: "devices", selector: { device: { multiple: true, filter: { integration: DOMAIN } } } },
        ...BOOLEANS.map((name) => ({ name, default: true, selector: { boolean: {} } })),
      ],
      computeLabel: (schema) => LABELS[schema.name],
      computeHelper: (schema) => HELPERS[schema.name],
    };
  }

  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    // ha-card stays for the card's whole life, so what card-mod adds to it survives renders.
    this.shadowRoot.innerHTML = `<style>${STYLE}</style><ha-card><div class="content"></div></ha-card>`;
    this._content = this.shadowRoot.querySelector(".content");
    this._expanded = null;
    this._showAll = false;
    this._related = null;
    this._request = 0;
    this._seen = [];
    this.shadowRoot.addEventListener("click", (ev) => this._onClick(ev));
  }

  setConfig(config) {
    this._config = validateConfig(config);
    // New options may need data the open row never loaded, so start closed.
    this._expanded = null;
    this._related = null;
    this._request += 1;
    this._seen = [];
    this._update();
  }

  set hass(hass) {
    this._hass = hass;
    this._update();
  }

  get hass() {
    return this._hass;
  }

  getCardSize() {
    const alarms = this._view?.groups.reduce((sum, group) => sum + group.alarms.length + 1, 0) ?? 3;
    return 1 + alarms;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6 };
  }

  _update() {
    const hass = this._hass;
    if (!hass || !this._config) return;
    if (hass.entities !== this._entities || hass.devices !== this._devices) {
      this._entities = hass.entities;
      this._devices = hass.devices;
      this._index = buildIndex(hass);
      this._seen = [];
    }
    const ctx = timeContext(hass);
    const today = parts(ctx.now, ctx.timeZone).day;
    // Render only when something this card shows has changed: HA replaces the
    // state object of an entity when it changes, so comparing references is enough.
    const seen = [hass.locale, ctx.timeZone, today, hass.user?.is_admin, ...this._watched().map((id) => hass.states[id])];
    if (seen.length === this._seen.length && seen.every((item, i) => item === this._seen[i])) return;
    this._seen = seen;
    this._render(ctx);
  }

  _watched() {
    const ids = [];
    for (const phone of this._index.phones.values()) {
      for (const key of PHONE_KEYS) if (phone.entities[key]) ids.push(phone.entities[key]);
      for (const alarm of phone.alarms) for (const key of ALARM_KEYS) if (alarm.entities[key]) ids.push(alarm.entities[key]);
    }
    if (this._related?.items) ids.push(...this._related.items);
    return ids;
  }

  _onClick(ev) {
    const target = ev.composedPath().find((el) => el instanceof HTMLElement && el.dataset?.action);
    if (!target) return;
    const { action, key } = target.dataset;
    if (action === "toggle") this._toggle(key);
    else if (action === "more") {
      this._showAll = true;
      this._refresh();
    } else if (action === "open") {
      this.dispatchEvent(new CustomEvent("hass-more-info", { detail: { entityId: key }, bubbles: true, composed: true }));
    } else if (action === "device") {
      window.history.pushState(null, "", `/config/devices/device/${key}`);
      window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace: false } }));
    }
  }

  _refresh() {
    this._seen = [];
    this._update();
  }

  _toggle(key) {
    this._request += 1;
    this._showAll = false;
    this._related = null;
    this._expanded = this._expanded === key ? null : key;
    if (this._expanded && this._config.show_automations) this._load(key);
    this._refresh();
  }

  async _load(key) {
    const request = ++this._request;
    let targets;
    if (key.startsWith("sleep:")) {
      const phone = this._index.phones.get(key.slice(6));
      targets = SLEEP_TARGETS.map((k) => phone?.entities[k]).filter(Boolean).map((id) => ["entity", id]);
    } else targets = [["device", key]];
    this._related = { key, status: "loading" };
    let related;
    try {
      const results = await Promise.all(
        targets.map(([type, id]) => this._hass.callWS({ type: "search/related", item_type: type, item_id: id })),
      );
      const ids = new Set();
      for (const result of results) for (const id of [...(result.automation ?? []), ...(result.script ?? [])]) ids.add(id);
      related = { key, status: "done", items: [...ids] };
    } catch (err) {
      related = { key, status: "error" };
    }
    // A late reply for a row the user already closed. A detached card keeps it:
    // dashboards detach and reattach cards when they rebuild columns.
    if (request !== this._request) return;
    this._related = related;
    this._refresh();
  }

  _render(ctx) {
    const { _config: config, _hass: hass } = this;
    this._view = selectAlarms(this._index, config, hass.states);
    const { groups, missing } = this._view;
    const keys = new Set();
    let body = "";
    for (const group of groups) {
      let html = config.show_sleep && group.whole ? this._sleepSection(group.phone, ctx, keys) : "";
      // Alarms picked one by one stay even with show_other off.
      if ((config.show_other || !group.whole) && group.alarms.length) {
        html += `<section class="section"><h2 class="section-header">Other</h2>`;
        for (const alarm of group.alarms) {
          keys.add(alarm.key);
          const subtitle = [alarm.label, alarm.repeat].filter(Boolean).join(" · ");
          const on = alarm.enabled ? "On" : "Off";
          const status = clockIcon(on.toLowerCase(), on);
          html += this._item(
            alarm.key,
            alarm.enabled ? "" : "off",
            clockHtml(formatClock(alarm.hour, alarm.minute, ctx)),
            `<span>${escape(subtitle)}</span>`,
            status,
            () => this._alarmDetails(alarm, ctx),
          );
        }
        html += `</section>`;
      }
      // A phone with nothing to show gets no heading either.
      if (html && groups.length > 1) body += `<div class="phone">${escape(group.phone.name)}</div>`;
      body += html;
    }
    if (this._expanded && !keys.has(this._expanded)) this._expanded = null;
    if (!this._index.phones.size) {
      body = `<div class="empty">No phones yet. Add one in Settings → Devices &amp; services → iPhone Alarms Sync.</div>`;
    } else if (!keys.size) {
      body = config.devices.length || groups.some((group) => group.alarms.length)
        ? `<div class="empty">No alarms match this card's filters.</div>`
        : `<div class="empty">No alarms yet. Run the Sync shortcut on your phone.</div>`;
    }
    const warning = missing
      ? `<div class="warning">${missing} selected device${missing > 1 ? "s" : ""} no longer exist${missing > 1 ? "" : "s"}.</div>`
      : "";
    const title = config.title ? `<h1 class="title">${escape(config.title)}</h1>` : "";
    const focused = this.shadowRoot.activeElement?.dataset;
    this._content.innerHTML = `${title}${warning}${body}`;
    if (focused?.action === "more" && this._showAll) {
      // "Show all" is gone after the render: go on with the first automation it revealed.
      this._content.querySelectorAll(".automation")[PREVIEW_LIMIT]?.focus();
    } else if (focused?.action) {
      [...this._content.querySelectorAll(`[data-action="${focused.action}"]`)].find((el) => el.dataset.key === focused.key)?.focus();
    }
  }

  _sleepSection(phone, ctx, keys) {
    const states = this._hass.states;
    const value = (key) => states[phone.entities[key]]?.state;
    const sleep = sleepSummary(value("bedtime_last_event_at"), value("wakeup_last_event_goes_off_at"), ctx);
    if (!sleep) return "";
    const key = `sleep:${phone.id}`;
    keys.add(key);
    const meta = [
      sleep.bedtime ? `<span>Bedtime ${clockHtml(sleep.bedtime)}</span>` : "",
      sleep.duration ? `<span>${escape(sleep.duration)}</span>` : "",
      `<span>${sleep.isWake ? "" : "Bedtime · "}${escape(sleep.day)}</span>`,
    ]
      .filter(Boolean)
      .join(`<span aria-hidden="true">·</span>`);
    // The row already shows the wake-up, bedtime and sleep length; details add the events.
    const details = () => this._details(key, [], SLEEP_EVENTS, phone.entities, ctx, null);
    return (
      `<section class="section"><h2 class="section-header">${bed()}Sleep | Wake Up</h2>` +
      this._item(key, "", clockHtml(sleep.main), meta, clockIcon("sleep"), details) +
      `</section>`
    );
  }

  _item(key, cls, time, subtitle, status, details) {
    const open = this._expanded === key;
    return (
      `<div class="item ${cls}"><button class="row" data-action="toggle" data-key="${escape(key)}" aria-expanded="${open}"${open ? ' aria-controls="details"' : ""}>` +
      `<span class="main"><span class="time">${time}</span><span class="subtitle">${subtitle}</span></span>` +
      `${status}</button>` +
      (open ? `<div class="details" id="details">${details()}</div>` : "") +
      `</div>`
    );
  }

  _alarmDetails(alarm, ctx) {
    const next = formatEventTime(this._hass.states[alarm.entities.next_occurrence_datetime]?.state, ctx, "Today ");
    // Only what the row doesn't show already.
    const rows = [
      ["Snooze", alarm.allowsSnooze ? "Allowed" : "Not allowed"],
      ["Next ring", next],
    ];
    return this._details(alarm.key, rows, ALARM_EVENTS, alarm.entities, ctx, alarm.key);
  }

  _details(key, rows, events, entities, ctx, deviceId) {
    const states = this._hass.states;
    const info = [...rows];
    if (this._config.show_last_events) {
      const last = events.map(([entityKey, label]) => [label, formatEventTime(states[entities[entityKey]]?.state, ctx)]);
      info.push(...(last.some(([, when]) => when) ? last : [["Last events", "None yet"]]));
    }
    let html = `<dl class="info">${info
      .filter(([, value]) => value)
      .map(([label, value]) => `<dt>${escape(label)}</dt><dd>${escape(value)}</dd>`)
      .join("")}</dl>`;
    // Above the automations, whose list can be long. The device page is under Settings, which only admins can open.
    if (deviceId && this._hass.user?.is_admin) {
      html += `<button class="link" data-action="device" data-key="${escape(deviceId)}"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="${LIST_ICON}"/></svg><span class="name">Show all entities</span></button>`;
    }
    if (this._config.show_automations) {
      const related = this._related?.key === key ? this._related : { status: "loading" };
      html += `<div class="label">Automations</div>`;
      if (related.status === "loading") html += `<p>Loading…</p>`;
      else if (related.status === "error") html += `<p>Couldn't load automations.</p>`;
      else {
        const items = relatedItems(related.items, states);
        if (!items.length) html += `<p>No automations use this ${key.startsWith("sleep:") ? "schedule" : "alarm"}.</p>`;
        const shown = this._showAll ? items : items.slice(0, PREVIEW_LIMIT);
        for (const item of shown) {
          html +=
            `<button class="automation${item.off ? " disabled" : ""}" data-action="open" data-key="${escape(item.id)}">` +
            `<span class="name">${escape(item.name)}</span>` +
            (item.script ? `<span class="tag">Script</span>` : "") +
            (item.off ? `<span class="tag">Off</span>` : "") +
            `</button>`;
        }
        if (shown.length < items.length) {
          html += `<button class="more" data-action="more" data-key="${escape(key)}">Show all (${items.length})</button>`;
        }
        // Telling those apart from "any alarm" triggers needs admin rights, so the search misses them.
        if (key.startsWith("sleep:")) html += `<p class="note">Device triggers on the phone, such as Bedtime starts, aren't listed.</p>`;
      }
    }
    return html;
  }
}

if (!customElements.get(CARD)) {
  customElements.define(CARD, IPhoneAlarmsCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: CARD,
    name: "iPhone Alarms",
    description: "Your iPhone alarms, the way the Clock app shows them.",
    preview: true,
    documentationURL: "https://github.com/Jozwiaczek/iphone-alarms-sync/blob/main/docs/dashboard-card.md",
  });
}
