// The card in a DOM, with a fake `hass`.
import assert from "node:assert/strict";
import { afterEach, beforeEach, mock, test } from "node:test";

import { flush, mount } from "./dom.js";
import { makeHass, NOW, PHONE, SECOND_PHONE, withState } from "./fixtures.js";

const [FIRST, SECOND, TEST, GYM] = PHONE.alarms.map((a) => a.id);
const SLEEP = `sleep:${PHONE.id}`;
const $ = (el, selector) => el.shadowRoot.querySelector(selector);
const $$ = (el, selector) => [...el.shadowRoot.querySelectorAll(selector)];
const text = (node) => node?.textContent.replace(/\s+/g, " ").trim();
const row = (el, key) => $$(el, "button.row").find((b) => b.dataset.key === key);
const names = (el) => $$(el, ".automation .name").map((n) => n.textContent);
const info = (el) => Object.fromEntries($$(el, ".info dt").map((dt) => [dt.textContent, dt.nextElementSibling.textContent]));
// Compare booleans and strings only: assert on a DOM node prints the whole tree.
const ok = (value, message) => assert.equal(Boolean(value), true, message);

beforeEach(() => mock.timers.enable({ apis: ["Date"], now: NOW }));
afterEach(() => {
  mock.timers.reset();
  mock.restoreAll();
  document.body.innerHTML = "";
});

test("lists Sleep and the other alarms like the Clock app", () => {
  const el = mount({}, makeHass());
  assert.deepEqual($$(el, ".section-header").map(text), ["Sleep | Wake Up", "Other"]);
  assert.deepEqual($$(el, ".time").map(text), ["08:30", "06:00", "07:35", "07:40", "16:43"]);
  assert.deepEqual($$(el, ".subtitle").map(text), [
    "Bedtime 00:00·8 hr 30 min·Today",
    "Gym · Weekends",
    "1️⃣ Pierwszy · Every day",
    "⚠️ Drugi · Weekdays",
    "Test 2 · Tue and Wed",
  ]);
  assert.deepEqual($$(el, ".status").map((s) => s.getAttribute("aria-label")), [null, "Off", "On", "On", "On"]);
  ok(row(el, GYM).parentElement.classList.contains("off"));
  ok(!$(el, ".title") && !$(el, ".phone"));
});

test("renders again only when what it shows changes", () => {
  let hass = makeHass();
  const el = mount({}, hass);
  const first = $(el, ".section");
  ok(first);
  hass = withState(hass, "light.unrelated", "on");
  el.hass = hass;
  el.hass = { ...hass };
  ok($(el, ".section") === first, "no render");
  const sensor = "sensor.johns_iphone_test_2_alarm_id";
  el.hass = withState(hass, sensor, "x", { ...hass.states[sensor].attributes, hour: 5 });
  ok($(el, ".section") !== first, "rendered");
  assert.equal(text($$(el, ".time")[1]), "05:43");
});

test("ha-card stays across renders, so card-mod styles survive", () => {
  const hass = makeHass();
  const el = mount({}, hass);
  const card = $(el, "ha-card");
  el.hass = withState(hass, "sensor.johns_iphone_test_2_alarm_id", "x");
  ok($(el, "ha-card") === card);
});

test("a new day relabels 'Today' without any state change", () => {
  const hass = makeHass();
  const el = mount({}, hass);
  mock.timers.setTime(NOW.getTime() + 86400000);
  el.hass = { ...hass };
  assert.equal(text($$(el, ".subtitle")[0]), "Bedtime 00:00·8 hr 30 min·Yesterday");
});

test("a tap shows everything else about an alarm", async () => {
  const el = mount({}, makeHass());
  row(el, FIRST).click();
  assert.equal(row(el, FIRST).getAttribute("aria-expanded"), "true");
  assert.equal(row(el, FIRST).getAttribute("aria-controls"), "details");
  assert.equal($(el, "#details")?.className, "details");
  assert.match(text($(el, ".details")), /Loading…/);
  await flush();
  assert.deepEqual(info(el), {
    Snooze: "Allowed",
    "Next ring": "Tomorrow 07:35",
    "Went off": "07:35",
    Snoozed: "07:44",
    Stopped: "07:52",
  });
  assert.deepEqual(names(el), ["Bedroom lights on", "Coffee machine", "Open the blinds"]);
  assert.deepEqual($$(el, ".automation .tag").map(text), ["Off"]);
  assert.equal(text($(el, ".link")), "Show all entities");
  assert.equal($(el, ".link").nextElementSibling.className, "label");
  // One row open at a time; a second tap closes it.
  row(el, TEST).click();
  await flush();
  assert.equal(row(el, FIRST).getAttribute("aria-expanded"), "false");
  assert.deepEqual(info(el), { Snooze: "Not allowed", "Next ring": "Today 16:43", "Last events": "None yet" });
  assert.match(text($(el, ".details")), /No automations use this alarm\./);
  row(el, TEST).click();
  ok(!$(el, ".details"));
});

test("an alarm that is off has no next ring", () => {
  const el = mount({ show_automations: false }, makeHass());
  row(el, GYM).click();
  assert.equal(info(el)["Next ring"], undefined);
});

test("'Show all entities' goes to the device page, for admins only", () => {
  const hass = makeHass();
  const el = mount({ show_automations: false }, hass);
  const pushed = [];
  mock.method(window.history, "pushState", (state, title, url) => pushed.push(url));
  let moved = 0;
  window.addEventListener("location-changed", () => moved++);
  row(el, FIRST).click();
  $(el, ".link").click();
  assert.deepEqual(pushed, [`/config/devices/device/${FIRST}`]);
  assert.equal(moved, 1);
  const user = mount({ show_automations: false }, { ...hass, user: { is_admin: false } });
  row(user, FIRST).click();
  ok(!$(user, ".link"));
});

test("many automations: five, then all", async () => {
  const hass = makeHass();
  const el = mount({}, hass);
  row(el, SECOND).click();
  await flush();
  assert.equal(names(el).length, 5);
  assert.equal(text($(el, ".more")), "Show all (20)");
  $(el, ".more").focus();
  // A state change while "Show all" only has focus keeps it there.
  el.hass = withState(hass, "automation.bedroom_lights_on", "off");
  assert.equal(el.shadowRoot.activeElement, $(el, ".more"));
  $(el, ".more").click();
  assert.equal(names(el).length, 20);
  ok(!$(el, ".more"));
  // The keyboard goes on with the first automation that "Show all" revealed.
  assert.equal(el.shadowRoot.activeElement, $$(el, ".automation")[5]);
  assert.deepEqual(names(el), [...names(el)].sort((a, b) => a.localeCompare(b)));
});

test("Sleep looks up the wake-up and sleep events, scripts included", async () => {
  const hass = makeHass();
  const calls = [];
  const callWS = hass.callWS;
  hass.callWS = (msg) => (calls.push(msg), callWS(msg));
  const el = mount({}, hass);
  row(el, SLEEP).click();
  await flush();
  assert.deepEqual(
    calls.map((c) => [c.item_type, c.item_id]),
    [
      ["entity", "event.johns_iphone_wakeup_alarm"],
      ["entity", "event.johns_iphone_sleep"],
    ],
  );
  assert.deepEqual(names(el), ["Good morning", "Night mode off"]);
  assert.deepEqual($$(el, ".automation .tag").map(text), ["Script"]);
  assert.deepEqual(info(el), { "Wind down": "Yesterday 23:30", "Went off": "08:30", Stopped: "08:32" });
  ok(!$(el, ".link"));
  // The search can't see the phone's device triggers, and the card says so.
  assert.match(text($(el, ".note")), /Device triggers on the phone/);
});

test("tonight's bedtime is not paired with this morning's wake-up", () => {
  const hass = makeHass();
  const el = mount({}, withState(hass, "sensor.johns_iphone_bedtime_last_event_at", "2026-11-24T08:50:00Z"));
  assert.equal(text($$(el, ".subtitle")[0]), "Today");
});

test("a failed lookup says so and the next tap tries again", async () => {
  const hass = makeHass();
  const working = hass.callWS;
  hass.callWS = async () => {
    throw new Error("nope");
  };
  const el = mount({}, hass);
  row(el, FIRST).click();
  await flush();
  assert.match(text($(el, ".details")), /Couldn't load automations\./);
  hass.callWS = working;
  row(el, FIRST).click();
  row(el, FIRST).click();
  await flush();
  assert.equal(names(el).length, 3);
});

test("a late reply for a closed row is dropped, a detached card keeps it", async () => {
  const hass = makeHass();
  let reply;
  hass.callWS = () => new Promise((resolve) => (reply = resolve));
  const el = mount({}, hass);
  row(el, FIRST).click();
  row(el, FIRST).click();
  reply({ automation: ["automation.coffee_machine"] });
  await flush();
  ok(!$(el, ".details"));

  row(el, FIRST).click();
  document.body.removeChild(el);
  reply({ automation: ["automation.coffee_machine"] });
  await flush();
  document.body.appendChild(el);
  assert.deepEqual(names(el), ["Coffee machine"]);
});

test("changing the options closes the open row", async () => {
  const el = mount({ show_automations: false }, makeHass());
  row(el, FIRST).click();
  el.setConfig({ show_automations: true });
  await flush();
  ok(!$(el, ".details"));
});

test("an automation opens its more-info dialog", async () => {
  const el = mount({}, makeHass());
  const opened = [];
  document.body.addEventListener("hass-more-info", (ev) => opened.push(ev.detail.entityId));
  row(el, FIRST).click();
  await flush();
  $(el, ".automation").click();
  assert.deepEqual(opened, ["automation.bedroom_lights_on"]);
});

test("an automation gone after the lookup leaves the list", async () => {
  const hass = makeHass();
  const el = mount({}, hass);
  row(el, FIRST).click();
  await flush();
  const states = Object.fromEntries(Object.entries(hass.states).filter(([id]) => id !== "automation.coffee_machine"));
  el.hass = { ...hass, states };
  assert.deepEqual(names(el), ["Bedroom lights on", "Open the blinds"]);
});

test("with automations and events off, a tap still shows the alarm's details and asks nothing", () => {
  const hass = makeHass();
  hass.callWS = () => assert.fail("no lookup expected");
  const el = mount({ show_automations: false, show_last_events: false }, hass);
  row(el, FIRST).click();
  assert.deepEqual(info(el), { Snooze: "Allowed", "Next ring": "Tomorrow 07:35" });
  ok(!$(el, ".label"));
});

test("options: title, no Sleep, no disabled alarms, two phones", () => {
  const el = mount({ title: "Alarms", show_sleep: false, show_disabled: false }, makeHass({ phones: [PHONE, SECOND_PHONE] }));
  assert.equal(text($(el, ".title")), "Alarms");
  assert.deepEqual($$(el, ".phone").map(text), ["Anna's iPhone", "John's iPhone"]);
  ok(!$$(el, ".section-header").some((h) => h.textContent.includes("Sleep")));
  ok(!row(el, GYM));
});

test("show_other: false keeps only Sleep | Wake Up", () => {
  const el = mount({ show_other: false }, makeHass());
  assert.deepEqual($$(el, ".section-header").map(text), ["Sleep | Wake Up"]);
  const none = mount({ show_other: false, show_sleep: false }, makeHass());
  assert.equal(text($(none, ".empty")), "No alarms match this card's filters.");
  const picked = mount({ show_other: false, devices: [TEST] }, makeHass());
  assert.deepEqual($$(picked, ".time").map(text), ["16:43"]);
});

test("picked alarms show without the phone's Sleep section", () => {
  const el = mount({ devices: [TEST] }, makeHass());
  assert.deepEqual($$(el, ".time").map(text), ["16:43"]);
});

test("empty states and a deleted device", () => {
  const none = mount({}, makeHass({ phones: [] }));
  assert.match(text($(none, ".empty")), /No phones yet/);
  const noAlarms = mount({ show_sleep: false }, makeHass({ phones: [{ ...SECOND_PHONE, alarms: [] }] }));
  assert.match(text($(noAlarms, ".empty")), /No alarms yet/);
  const filtered = mount({ devices: ["gone"] }, makeHass());
  assert.equal(text($(filtered, ".empty")), "No alarms match this card's filters.");
  assert.equal(text($(filtered, ".warning")), "1 selected device no longer exists.");
});

test("a bad config is refused", () => {
  const el = document.createElement("iphone-alarms-card");
  assert.throws(() => el.setConfig({ devices: "phone" }), /devices/);
});

test("12-hour clocks", () => {
  const el = mount({}, makeHass({ locale: { time_format: "12" } }));
  assert.deepEqual($$(el, ".time").map((t) => t.textContent), ["8:30AM", "6:00AM", "7:35AM", "7:40AM", "4:43PM"]);
});

test("the documented styling hooks exist", async () => {
  const el = mount({}, makeHass());
  const style = $(el, "style").textContent;
  for (const name of ["accent", "time-size", "time-weight", "row-padding", "disabled-opacity", "on-color", "panel-color"]) {
    ok(style.includes(`--iphone-alarms-${name}`), name);
  }
  row(el, FIRST).click();
  await flush();
  for (const cls of ["section", "section-header", "row", "time", "subtitle", "status", "details", "automation"]) {
    ok($(el, `.${cls}`), cls);
  }
});

test("the editor form and the card picker", () => {
  const Card = customElements.get("iphone-alarms-card");
  const form = Card.getConfigForm();
  assert.deepEqual(
    form.schema.map((s) => s.name),
    ["title", "devices", "show_sleep", "show_other", "show_disabled", "show_last_events", "show_automations"],
  );
  assert.equal(form.schema[1].selector.device.filter.integration, "iphone_alarms_sync");
  for (const field of form.schema) ok(form.computeLabel(field) && form.computeHelper(field), field.name);
  ok(window.customCards.some((c) => c.type === "iphone-alarms-card"));
  const el = mount({}, makeHass());
  assert.deepEqual(el.getGridOptions(), { columns: 12, min_columns: 6 });
  ok(el.getCardSize() > 1);
});

// What a user reads and hears, line by line.
const screen = (el) =>
  $$(el, ".section-header, .time, .subtitle, .status, dt, dd, .label, .details p, .link, .automation, .more")
    .map((node) => node.getAttribute("aria-label") ?? text(node))
    .filter(Boolean);
// The editor's labels and helpers; Home Assistant puts the user's language on <html lang>.
const editor = (lang) => {
  document.documentElement.lang = lang;
  const form = customElements.get("iphone-alarms-card").getConfigForm();
  const fields = form.schema.map((field) => [form.computeLabel(field), form.computeHelper(field)]);
  document.documentElement.lang = "";
  return fields;
};
const inLanguage = (language, config = {}) => mount(config, makeHass({ locale: { language } }));

async function openFirst(language) {
  const el = inLanguage(language);
  row(el, FIRST).click();
  await flush();
  return el;
}

test("Polish: the card and its editor", async (t) => {
  const el = await openFirst("pl");
  assert.deepEqual($$(el, ".section-header").map(text), ["Sen | Pobudka", "Inne"]);
  t.assert.snapshot(screen(el));
  t.assert.snapshot(editor("pl"));
  const gone = (n) => text($(inLanguage("pl", { devices: Array.from({ length: n }, (_, i) => `gone${i}`) }), ".warning"));
  assert.deepEqual([1, 2, 5].map(gone), [
    "1 wybrane urządzenie już nie istnieje.",
    "2 wybrane urządzenia już nie istnieją.",
    "5 wybranych urządzeń już nie istnieje.",
  ]);
});

test("a language the card doesn't know falls back to English", async (t) => {
  const el = await openFirst("tlh");
  assert.deepEqual($$(el, ".section-header").map(text), ["Sleep | Wake Up", "Other"]);
  assert.deepEqual(screen(el), screen(await openFirst("en")));
  t.assert.snapshot(screen(el));
  t.assert.snapshot(editor("tlh"));
});
