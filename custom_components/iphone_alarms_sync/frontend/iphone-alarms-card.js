// iPhone Alarms card: a read-only list of the alarms that iPhone Alarms Sync
// keeps, laid out like the Alarms tab of the iOS Clock app.
// Plain web component, no build step: Home Assistant loads this file as is.

const DOMAIN = "iphone_alarms_sync";
const CARD = "iphone-alarms-card";
const PREVIEW_LIMIT = 5;
const DAY_MS = 86400000;
const WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
// In the order the card shows them.
const BOOLEANS = ["show_disabled", "show_last_events", "show_automations"];
// Entity and the text key of its event name.
const ALARM_EVENTS = [
  ["last_event_goes_off_at", "went_off"],
  ["last_event_snoozed_at", "snoozed"],
  ["last_event_stopped_at", "stopped"],
];
// The phone's event entities, in the order the phone row lists their automations.
const PHONE_SUBJECTS = ["any_alarm", "wakeup_alarm", "sleep"];
const ALARM_KEYS = ["alarm_id", "next_occurrence_datetime", "last_occurrence_datetime", ...ALARM_EVENTS.map(([key]) => key)];
// A "goes off" from the phone this close after the scheduled time confirms that ring.
const CONFIRM_WINDOW_MS = 5 * 60000;
// Every text the card shows, by language. A language or key missing here falls back to English.
const STRINGS = {
  en: {
    description: "Your iPhone alarms, the way the Clock app shows them.",
    title: "Title",
    title_helper: "Leave empty for a more compact card.",
    devices: "Phones or alarms",
    devices_helper: "Pick phones (all their alarms) or single alarms. Leave empty to show every alarm.",
    show_disabled: "Show alarms that are off",
    show_disabled_helper: "Shown grayed out, with a crossed-out clock.",
    show_automations: "Show automations of an alarm",
    show_automations_helper: "Tap an alarm to see the automations and scripts that use it. Those of the whole phone get a row of their own.",
    show_last_events: "Show last events of an alarm",
    show_last_events_helper: "Tap an alarm to see when it last went off, was snoozed or stopped.",
    every_day: "Every day",
    weekdays: "Weekdays",
    weekends: "Weekends",
    // day: the weekday's full name; i: 0 for Monday.
    every: (day) => `Every ${day}`,
    and: "and",
    today: "Today",
    yesterday: "Yesterday",
    tomorrow: "Tomorrow",
    alarm: "Alarm",
    alarm_on: "On",
    alarm_off: "Off",
    went_off: "Went off",
    snoozed: "Snoozed",
    stopped: "Stopped",
    snooze: "Snooze",
    allowed: "Allowed",
    not_allowed: "Not allowed",
    next_ring: "Next ring",
    last_events: "Last events",
    none_yet: "None yet",
    estimated: "estimated",
    show_all_entities: "Show all entities",
    automations: "Automations",
    loading: "Loading…",
    load_error: "Couldn't load automations.",
    no_alarm_automations: "No automations use this alarm.",
    script: "Script",
    automation_off: "Off",
    phone_automations: "Automations",
    no_phone_automations: "No automations use this phone.",
    // Named like the phone's event entities.
    any_alarm: "Any alarm",
    wakeup_alarm: "Wake-Up alarm",
    sleep: "Sleep",
    // Device triggers on the phone, which don't say which of the above they use.
    other: "Other",
    show_all: (n) => `Show all (${n})`,
    no_phones: "No phones yet. Add one in Settings → Devices & services → iPhone Alarms Sync.",
    no_match: "No alarms match this card's filters.",
    no_alarms: "No alarms yet. Run the Sync shortcut on your phone.",
    missing: (n) => (n === 1 ? "1 selected device no longer exists." : `${n} selected devices no longer exist.`),
  },
  pl: {
    description: "Twoje budziki z iPhone'a, tak jak pokazuje je aplikacja Zegar.",
    title: "Tytuł",
    title_helper: "Zostaw puste, aby karta była bardziej zwarta.",
    devices: "Telefony lub budziki",
    devices_helper: "Wybierz telefony (wszystkie ich budziki) albo pojedyncze budziki. Zostaw puste, aby pokazać wszystkie budziki.",
    show_disabled: "Pokaż wyłączone budziki",
    show_disabled_helper: "Wyszarzone, z przekreślonym zegarem.",
    show_automations: "Pokaż automatyzacje budzika",
    show_automations_helper: "Dotknij budzika, aby zobaczyć automatyzacje i skrypty, które go używają. Automatyzacje całego telefonu mają osobny wiersz.",
    show_last_events: "Pokaż ostatnie zdarzenia budzika",
    show_last_events_helper: "Dotknij budzika, aby zobaczyć, kiedy ostatnio zadzwonił, przeszedł w drzemkę albo został zatrzymany.",
    every_day: "Codziennie",
    weekdays: "Dni robocze",
    weekends: "Weekendy",
    // "Co" takes the accusative, which Intl doesn't give.
    every: (day, i) => `Co ${["poniedziałek", "wtorek", "środę", "czwartek", "piątek", "sobotę", "niedzielę"][i]}`,
    and: "i",
    today: "Dziś",
    yesterday: "Wczoraj",
    tomorrow: "Jutro",
    alarm: "Budzik",
    alarm_on: "Włączony",
    alarm_off: "Wyłączony",
    went_off: "Zadzwonił",
    snoozed: "Odłożony",
    stopped: "Zatrzymany",
    snooze: "Drzemka",
    allowed: "Dozwolona",
    not_allowed: "Niedozwolona",
    next_ring: "Następny dzwonek",
    last_events: "Ostatnie zdarzenia",
    none_yet: "Jeszcze brak",
    estimated: "szacowane",
    show_all_entities: "Pokaż wszystkie encje",
    automations: "Automatyzacje",
    loading: "Wczytywanie…",
    load_error: "Nie udało się wczytać automatyzacji.",
    no_alarm_automations: "Żadna automatyzacja nie używa tego budzika.",
    script: "Skrypt",
    automation_off: "Wyłączona",
    phone_automations: "Automatyzacje",
    no_phone_automations: "Żadna automatyzacja nie używa tego telefonu.",
    any_alarm: "Dowolny budzik",
    wakeup_alarm: "Budzik pobudki",
    sleep: "Sen",
    other: "Inne",
    show_all: (n) => `Pokaż wszystkie (${n})`,
    no_phones: "Brak telefonów. Dodaj telefon w Ustawienia → Urządzenia oraz usługi → iPhone Alarms Sync.",
    no_match: "Żaden budzik nie pasuje do filtrów tej karty.",
    no_alarms: "Brak budzików. Uruchom skrót Sync na telefonie.",
    missing: (n) =>
      ({
        one: "1 wybrane urządzenie już nie istnieje.",
        few: `${n} wybrane urządzenia już nie istnieją.`,
      })[new Intl.PluralRules("pl").select(n)] ?? `${n} wybranych urządzeń już nie istnieje.`,
  },
};

/** The card's texts in a language, such as "pl" or "en-GB", and the locale for its dates. */
export function strings(language) {
  const own = STRINGS[language] ?? STRINGS[language?.split("-")[0]];
  // Dates follow the texts, so one line never mixes two languages.
  return { ...STRINGS.en, ...own, locale: own ? language : "en-US" };
}

// The editor form gets no `hass`; Home Assistant puts the user's language on <html lang>.
const editorStrings = () => strings(document.documentElement.lang);

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
export function describeRepeat(days, t = strings()) {
  const set = new Set(days ?? []);
  const picked = WEEK.flatMap((day, i) => (set.has(day) ? [i] : []));
  const key = picked.join("");
  if (picked.length === 7) return t.every_day;
  if (key === "01234") return t.weekdays;
  if (key === "56") return t.weekends;
  // 1 January 2024 was a Monday.
  const name = (i, weekday) => new Date(Date.UTC(2024, 0, 1 + i)).toLocaleDateString(t.locale, { timeZone: "UTC", weekday });
  if (picked.length === 1) return t.every(name(picked[0], "long"), picked[0]);
  const short = picked.map((i) => name(i, "short"));
  if (short.length === 2) return `${short[0]} ${t.and} ${short[1]}`;
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
  return { h12, timeZone, now, t: strings(locale.language) };
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

/**
 * When an alarm last rang: the phone's "goes off" event, or else the time it was
 * set to ring, which Home Assistant only estimates. Null before either.
 */
export function lastRing(goesOffValue, scheduledValue) {
  const confirmed = parseTime(goesOffValue);
  const scheduled = parseTime(scheduledValue);
  if (scheduled && !(confirmed && confirmed >= scheduled - CONFIRM_WINDOW_MS)) return { at: scheduled, estimated: true };
  return confirmed ? { at: confirmed, estimated: false } : null;
}

/** A moment near now, short: "07:35", "Yesterday 07:35", "Tomorrow 07:35", "Mon 07:35" or "Nov 12". */
export function formatEventTime(value, ctx, withToday = false) {
  const date = parseTime(value);
  if (!date) return null;
  const at = parts(date, ctx.timeZone);
  const days = dayNumber(parts(ctx.now, ctx.timeZone)) - dayNumber(at);
  const clock = formatClock(at.hour, at.minute, ctx);
  const time = clock.period ? `${clock.time} ${clock.period}` : clock.time;
  const { t } = ctx;
  const options = { timeZone: ctx.timeZone };
  if (days === 0) return withToday ? `${t.today} ${time}` : time;
  if (days === 1) return `${t.yesterday} ${time}`;
  if (days === -1) return `${t.tomorrow} ${time}`;
  if (Math.abs(days) < 7) return `${date.toLocaleDateString(t.locale, { ...options, weekday: "short" })} ${time}`;
  return date.toLocaleDateString(t.locale, { ...options, month: "short", day: "numeric" });
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

function readAlarm(alarm, states, t) {
  const state = states[alarm.entities.alarm_id];
  const attrs = state?.attributes;
  if (!attrs || state.state === "unavailable" || !Number.isInteger(attrs.hour)) return null;
  return {
    key: alarm.id,
    entities: alarm.entities,
    label: attrs.label || t.alarm,
    hour: attrs.hour,
    minute: attrs.minute ?? 0,
    enabled: attrs.enabled !== false,
    allowsSnooze: attrs.allows_snooze !== false,
    repeat: attrs.repeats ? describeRepeat(attrs.repeat_days, t) : "",
    lastRing: lastRing(states[alarm.entities.last_event_goes_off_at]?.state, states[alarm.entities.last_occurrence_datetime]?.state),
  };
}

/** What the card shows: phones with their alarms, after the config's filters. */
export function selectAlarms(index, config, states, t = strings()) {
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
      .map((alarm) => readAlarm(alarm, states, t))
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

const LIST_ICON = "M7,5H21V7H7V5M7,13V11H21V13H7M4,4.5A1.5,1.5 0 0,1 5.5,6A1.5,1.5 0 0,1 4,7.5A1.5,1.5 0 0,1 2.5,6A1.5,1.5 0 0,1 4,4.5M4,10.5A1.5,1.5 0 0,1 5.5,12A1.5,1.5 0 0,1 4,13.5A1.5,1.5 0 0,1 2.5,12A1.5,1.5 0 0,1 4,10.5M7,19V17H21V19H7M4,16.5A1.5,1.5 0 0,1 5.5,18A1.5,1.5 0 0,1 4,19.5A1.5,1.5 0 0,1 2.5,18A1.5,1.5 0 0,1 4,16.5Z";
// The arrow in a row icon's corner: whether the row is open.
const BADGE = `<g class="badge"><circle cx="25.5" cy="25.5" r="6"/><path d="M23 24.5l2.5 2.5 2.5-2.5"/></g>`;
// One icon for two facts: the clock says whether the alarm is on, the arrow in its corner whether the row is open.
const clockIcon = (state, label) =>
  `<svg class="status ${state}" viewBox="0 0 32 32" ` +
  (label ? `role="img" aria-label="${escape(label)}"><title>${escape(label)}</title>` : `aria-hidden="true">`) +
  `<path class="bells" d="M4.5 9.5a5.5 5.5 0 0 1 6-6M27.5 9.5a5.5 5.5 0 0 0-6-6"/>` +
  `<circle class="face" cx="16" cy="17" r="10"/>` +
  `<path class="hands" d="M16 11.5V17l3.5 2.5"/>` +
  `<path class="slash" d="M5 5l22 24"/>${BADGE}</svg>`;
// The phone row's icon, with the same arrow as the clock.
const phoneIcon = () =>
  `<svg class="status" viewBox="0 0 32 32" aria-hidden="true">` +
  `<rect x="9" y="4" width="14" height="24" rx="3.5"/><path d="M14 8h4"/>${BADGE}</svg>`;
const clockHtml = ({ time, period }) => `${escape(time)}${period ? `<span class="period">${period}</span>` : ""}`;

const STYLE = `
:host { display: block; }
ha-card { overflow: hidden; container-type: inline-size; }
.content { padding-block: 4px 12px; }
.title { margin: 0; padding: 16px 16px 0; font-size: 1.5rem; font-weight: 700; line-height: 1.2; color: var(--primary-text-color); }
.phone { padding: 16px 16px 0; font-size: 0.8125rem; font-weight: 600; letter-spacing: 0.02em; text-transform: uppercase; color: var(--secondary-text-color); }
.section { padding-inline: 16px; }
.item { border-bottom: 1px solid var(--divider-color); }
.section:last-child .item:last-child { border-bottom: 0; }
.row { display: flex; align-items: center; gap: 12px; width: 100%; margin: 0; padding: var(--iphone-alarms-row-padding, 10px 0 12px); border: 0; background: none; color: inherit; font: inherit; text-align: start; cursor: pointer; }
button:focus-visible { outline: 2px solid var(--primary-color); outline-offset: -2px; border-radius: 6px; }
.main { flex: 1; min-width: 0; }
.time { display: block; font-size: var(--iphone-alarms-time-size, 2.5rem); font-weight: var(--iphone-alarms-time-weight, 300); line-height: 1.1; font-variant-numeric: tabular-nums; letter-spacing: -0.01em; color: var(--primary-text-color); }
.period { margin-inline-start: 3px; font-size: 0.45em; font-weight: 400; }
.subtitle { display: flex; align-items: center; gap: 6px; margin-top: 4px; overflow: hidden; font-size: 0.9375rem; line-height: 1.35; white-space: nowrap; flex-wrap: wrap; color: var(--primary-text-color); }
.subtitle span { overflow: hidden; text-overflow: ellipsis; }
.subtitle .last { flex-basis: 100%; font-size: 0.8125rem; color: var(--secondary-text-color); }
/* One line, not an alarm: its groups are named inside. */
.phone-row .time { font-size: 1rem; font-weight: 500; letter-spacing: 0; }
.phone-row .subtitle { display: none; }
.off .main { opacity: var(--iphone-alarms-disabled-opacity, 0.45); }
.status { flex: none; width: 36px; height: 36px; overflow: visible; fill: none; stroke: var(--secondary-text-color); stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
.status.on { --clock: var(--iphone-alarms-on-color, #34c759); }
.status.on .bells { stroke: var(--clock); }
.status.on .face { fill: var(--clock); stroke: var(--clock); }
.status.on .hands { stroke: #fff; }
.status .slash { display: none; }
.status.off .slash { display: inline; }
.status .badge circle { fill: var(--ha-card-background, var(--card-background-color, #fff)); stroke: var(--divider-color); stroke-width: 1.5; }
.status .badge path { stroke: var(--primary-text-color); stroke-width: 1.75; transform-box: view-box; transform-origin: 25.5px 25.75px; transition: transform 0.2s; }
[aria-expanded="true"] .status .badge path { transform: rotate(180deg); }
.details { margin: 0 0 14px; padding: 12px 14px 4px; border-radius: 12px; font-size: 0.875rem; line-height: 1.35; color: var(--secondary-text-color); background: var(--iphone-alarms-panel-color, rgba(127, 127, 127, 0.1)); }
.details p { margin: 4px 0 10px; }
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
  .subtitle { font-size: 0.8125rem; white-space: normal; }
  .subtitle span { overflow: visible; }
  /* Too narrow for two columns: each label above its value. */
  .info { grid-template-columns: minmax(0, 1fr); gap: 0; }
  .info dd { margin-bottom: 8px; }
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
      computeLabel: (schema) => editorStrings()[schema.name],
      computeHelper: (schema) => editorStrings()[`${schema.name}_helper`],
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
      for (const alarm of phone.alarms) for (const key of ALARM_KEYS) if (alarm.entities[key]) ids.push(alarm.entities[key]);
    }
    for (const [, related] of this._related?.groups ?? []) ids.push(...related);
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
    this._related = { key, status: "loading" };
    let related;
    try {
      related = { key, status: "done", groups: await this._lookup(key) };
    } catch (err) {
      related = { key, status: "error" };
    }
    // A late reply for a row the user already closed. A detached card keeps it:
    // dashboards detach and reattach cards when they rebuild columns.
    if (request !== this._request) return;
    this._related = related;
    this._refresh();
  }

  /** What uses an alarm, as one group, or a phone, grouped by its event entities. */
  async _lookup(key) {
    const search = async (type, id) => {
      const result = await this._hass.callWS({ type: "search/related", item_type: type, item_id: id });
      return [...(result.automation ?? []), ...(result.script ?? [])];
    };
    const phone = this._index.phones.get(key);
    if (!phone) return [[null, await search("device", key)]];
    const subjects = PHONE_SUBJECTS.filter((subject) => phone.entities[subject]);
    // The device search also finds device triggers, which name no entity: those go under "Other".
    const [all, ...found] = await Promise.all([
      search("device", key),
      ...subjects.map((subject) => search("entity", phone.entities[subject])),
    ]);
    const seen = new Set();
    return [...subjects.map((subject, i) => [subject, found[i]]), ["other", all]].map(([subject, ids]) => [
      subject,
      ids.filter((id) => !seen.has(id) && seen.add(id)),
    ]);
  }

  _render(ctx) {
    const { _config: config, _hass: hass } = this;
    const { t } = ctx;
    this._view = selectAlarms(this._index, config, hass.states, t);
    const { groups, missing } = this._view;
    const keys = new Set();
    let body = "";
    let shown = 0;
    for (const group of groups) {
      let rows = "";
      // Automations of the whole phone don't belong to one alarm: they get a row of their own, on top
      // like Sleep | Wake Up in the Clock app. It stays when no alarm is shown, since those automations still run.
      if (config.show_automations && group.whole) {
        keys.add(group.phone.id);
        rows += this._item(group.phone.id, "phone-row", escape(t.phone_automations), "", phoneIcon(), () =>
          this._phoneDetails(group.phone.id, ctx),
        );
      }
      for (const alarm of group.alarms) {
        keys.add(alarm.key);
        shown += 1;
        const subtitle = [alarm.label, alarm.repeat].filter(Boolean).join(" · ");
        const ring = alarm.lastRing;
        const last = ring
          ? [t.went_off, formatEventTime(ring.at, ctx, true), ring.estimated && `· ${t.estimated}`].filter(Boolean).join(" ")
          : "";
        const status = alarm.enabled ? clockIcon("on", t.alarm_on) : clockIcon("off", t.alarm_off);
        rows += this._item(
          alarm.key,
          alarm.enabled ? "" : "off",
          clockHtml(formatClock(alarm.hour, alarm.minute, ctx)),
          `<span>${escape(subtitle)}</span>${last ? ` <span class="last">${escape(last)}</span>` : ""}`,
          status,
          () => this._alarmDetails(alarm, ctx),
        );
      }
      if (!rows) continue;
      // A phone with nothing to show gets no heading either.
      if (groups.length > 1) body += `<div class="phone">${escape(group.phone.name)}</div>`;
      body += `<section class="section">${rows}</section>`;
    }
    if (this._expanded && !keys.has(this._expanded)) this._expanded = null;
    if (!this._index.phones.size) {
      body = `<div class="empty">${escape(t.no_phones)}</div>`;
    } else if (!shown) {
      const empty = config.devices.length || groups.some((group) => group.alarms.length) ? t.no_match : t.no_alarms;
      body += `<div class="empty">${escape(empty)}</div>`;
    }
    const warning = missing ? `<div class="warning">${escape(t.missing(missing))}</div>` : "";
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
    const states = this._hass.states;
    const { t } = ctx;
    const key = alarm.key;
    // Only what the row doesn't show already.
    const info = [
      [t.snooze, alarm.allowsSnooze ? t.allowed : t.not_allowed],
      [t.next_ring, formatEventTime(states[alarm.entities.next_occurrence_datetime]?.state, ctx, true)],
    ];
    if (this._config.show_last_events) {
      const last = ALARM_EVENTS.map(([entityKey, label]) => [t[label], formatEventTime(states[alarm.entities[entityKey]]?.state, ctx)]);
      info.push(...(last.some(([, when]) => when) ? last : [[t.last_events, t.none_yet]]));
    }
    let html = `<dl class="info">${info
      .filter(([, value]) => value)
      .map(([label, value]) => `<dt>${escape(label)}</dt><dd>${escape(value)}</dd>`)
      .join("")}</dl>`;
    return html + this._deviceLink(key, t) + (this._config.show_automations ? `<div class="label">${escape(t.automations)}</div>${this._automations(key, t, t.no_alarm_automations)}` : "");
  }

  _phoneDetails(key, ctx) {
    return this._deviceLink(key, ctx.t) + this._automations(key, ctx.t, ctx.t.no_phone_automations);
  }

  // Above the automations, whose list can be long. The device page is under Settings, which only admins can open.
  _deviceLink(key, t) {
    if (!this._hass.user?.is_admin) return "";
    return `<button class="link" data-action="device" data-key="${escape(key)}"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="${LIST_ICON}"/></svg><span class="name">${escape(t.show_all_entities)}</span></button>`;
  }

  /** The automations of the open row: a label over each group that has a subject, "Show all" counting across groups. */
  _automations(key, t, empty) {
    const related = this._related?.key === key ? this._related : { status: "loading" };
    if (related.status === "loading") return `<p>${escape(t.loading)}</p>`;
    if (related.status === "error") return `<p>${escape(t.load_error)}</p>`;
    const groups = related.groups
      .map(([subject, ids]) => [subject, relatedItems(ids, this._hass.states)])
      .filter(([, items]) => items.length);
    const total = groups.reduce((sum, [, items]) => sum + items.length, 0);
    if (!total) return `<p>${escape(empty)}</p>`;
    let left = this._showAll ? total : PREVIEW_LIMIT;
    let html = "";
    for (const [subject, items] of groups) {
      if (left <= 0) break;
      if (subject) html += `<div class="label">${escape(t[subject])}</div>`;
      for (const item of items.slice(0, left)) {
        html +=
          `<button class="automation${item.off ? " disabled" : ""}" data-action="open" data-key="${escape(item.id)}">` +
          `<span class="name">${escape(item.name)}</span>` +
          (item.script ? `<span class="tag">${escape(t.script)}</span>` : "") +
          (item.off ? `<span class="tag">${escape(t.automation_off)}</span>` : "") +
          `</button>`;
      }
      left -= items.length;
    }
    if (total > PREVIEW_LIMIT && !this._showAll) {
      html += `<button class="more" data-action="more" data-key="${escape(key)}">${escape(t.show_all(total))}</button>`;
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
    // Read when the picker opens, after Home Assistant has set the language.
    get description() {
      return editorStrings().description;
    },
    preview: true,
    documentationURL: "https://github.com/Jozwiaczek/iphone-alarms-sync/blob/main/docs/dashboard-card.md",
  });
}
