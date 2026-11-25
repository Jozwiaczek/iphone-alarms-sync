// The card in a DOM, with a fake `hass`.
import assert from "node:assert/strict";
import { afterEach, beforeEach, mock, test } from "node:test";

import { card, flush, mount } from "./dom.js";
import { makeHass, NOW, PHONE, SECOND_PHONE, withState } from "./fixtures.js";

const [FIRST, SECOND, TEST, GYM] = PHONE.alarms.map((a) => a.id);
const $ = (el, selector) => el.shadowRoot.querySelector(selector);
const $$ = (el, selector) => [...el.shadowRoot.querySelectorAll(selector)];
const text = (node) => node?.textContent.replace(/\s+/g, " ").trim();
// Alarm rows only, without the phone row under them.
const ALARM = ".item:not(.phone-row)";
const row = (el, key) => $$(el, "button.row").find((b) => b.dataset.key === key);
const labels = (el) => $$(el, ".details .label .group").map(text);
const counts = (el) => $$(el, ".details .label .count").map(text);
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

test("lists the alarms like the Clock app", () => {
  const el = mount({}, makeHass());
  // Only what the Sync shortcut sent: iOS shares no Sleep schedule.
  ok(!$(el, "h2"));
  assert.deepEqual($$(el, `${ALARM} .time`).map(text), ["06:00", "07:35", "07:40", "16:43"]);
  assert.deepEqual($$(el, `${ALARM} .subtitle`).map(text), [
    "Gym · Weekends",
    "1️⃣ Pierwszy · Every day Went off Today 07:35",
    "⚠️ Drugi · Weekdays Went off Today 07:40 · estimated",
    "Test 2 · Tue and Wed",
  ]);
  assert.deepEqual($$(el, `${ALARM} .status`).map((s) => s.getAttribute("aria-label")), ["Off", "On", "On", "On"]);
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
  assert.equal(text($$(el, `${ALARM} .time`)[0]), "05:43");
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
  const el = mount({ show_automations: false }, hass);
  row(el, TEST).click();
  assert.equal(info(el)["Next ring"], "Today 16:43");
  mock.timers.setTime(NOW.getTime() + 86400000);
  el.hass = { ...hass };
  assert.equal(info(el)["Next ring"], "Yesterday 16:43");
});

test("a tap shows everything else about an alarm, and asks Home Assistant nothing", () => {
  const hass = makeHass();
  hass.callWS = () => assert.fail("an alarm's automations are in the Automations row");
  const el = mount({}, hass);
  row(el, FIRST).click();
  assert.equal(row(el, FIRST).getAttribute("aria-expanded"), "true");
  assert.equal(row(el, FIRST).getAttribute("aria-controls"), "details");
  assert.equal($(el, "#details")?.className, "details");
  assert.deepEqual(info(el), {
    Snooze: "Allowed",
    "Next ring": "Tomorrow 07:35",
    "Went off": "07:35",
    Snoozed: "07:44",
    Stopped: "07:52",
  });
  assert.equal(text($(el, ".link")), "Show all entities");
  ok(!$(el, ".details .label") && !$(el, ".automation"));
  // One row open at a time; a second tap closes it.
  row(el, TEST).click();
  assert.equal(row(el, FIRST).getAttribute("aria-expanded"), "false");
  assert.deepEqual(info(el), { Snooze: "Not allowed", "Next ring": "Today 16:43", "Last events": "None yet" });
  row(el, TEST).click();
  ok(!$(el, ".details"));
});

test("an alarm that is off has no next ring", () => {
  const el = mount({ show_automations: false }, makeHass());
  row(el, GYM).click();
  assert.equal(info(el)["Next ring"], undefined);
});

test("the Automations row lists everything: the phone's subjects, each alarm, then the rest", async () => {
  // "Wake the kids" uses the Any alarm entity, "Kitchen lights" the Sleep one. "Coffee machine" and
  // "Garage heater" are device triggers on the phone; the first also uses an alarm, so it is listed there only.
  const phone = {
    ...PHONE,
    alarms: PHONE.alarms.filter((alarm) => alarm.id !== SECOND),
    automations: ["automation.coffee_machine", "automation.garage_heater", "automation.wake_the_kids", "automation.kitchen_lights"],
    entityAutomations: { any_alarm: ["automation.wake_the_kids"], sleep: ["automation.kitchen_lights", "automation.wake_the_kids"] },
  };
  const el = mount({}, makeHass({ phones: [phone] }));
  const phoneRow = row(el, PHONE.id);
  assert.equal(text($(el, ".phone-row .time")), "Automations");
  assert.equal(text($(el, ".phone-row .subtitle")), "");
  // Above the alarms, like Sleep | Wake Up in the Clock app.
  assert.equal($$(el, "button.row").at(0), phoneRow);
  phoneRow.click();
  await flush();
  assert.equal(text($(el, ".more")), "Show all (7)");
  $(el, ".more").click();
  assert.deepEqual(labels(el), ["Any alarm", "Sleep", "06:00 · Gym", "07:35 · 1️⃣ Pierwszy", "Other"]);
  assert.deepEqual(names(el), ["Wake the kids", "Kitchen lights", "Good morning", "Bedroom lights on", "Coffee machine", "Open the blinds", "Garage heater"]);
  assert.deepEqual($$(el, ".automation .tag").map(text), ["Script", "Off", "Off"]);
});

test("the Automations row follows what the card shows", async () => {
  const hidden = mount({ show_disabled: false }, makeHass());
  row(hidden, PHONE.id).click();
  await flush();
  $(hidden, ".more").click();
  assert.deepEqual(labels(hidden), ["07:35 · 1️⃣ Pierwszy", "07:40 · ⚠️ Drugi"]);
  // Picked alarms keep the row, with only their own groups.
  const picked = mount({ devices: [GYM] }, makeHass());
  row(picked, PHONE.id).click();
  await flush();
  assert.deepEqual(labels(picked), ["06:00 · Gym"]);
  assert.deepEqual(names(picked), ["Good morning"]);
});

test("alarm groups are named after the alarms as shown now", async () => {
  let hass = makeHass();
  const el = mount({ devices: [FIRST, GYM] }, hass);
  row(el, PHONE.id).click();
  await flush();
  assert.deepEqual(labels(el), ["06:00 · Gym", "07:35 · 1️⃣ Pierwszy"]);
  const sensor = Object.values(hass.entities).find((e) => e.device_id === FIRST && e.translation_key === "alarm_id").entity_id;
  hass = withState(hass, sensor, "x", { ...hass.states[sensor].attributes, label: "", hour: 5 });
  el.hass = hass;
  assert.deepEqual(labels(el), ["05:35 · Alarm", "06:00 · Gym"]);
  el.hass = withState(hass, sensor, "unavailable");
  assert.deepEqual(labels(el), ["06:00 · Gym"]);
  const h12 = mount({ devices: [GYM] }, makeHass({ locale: { time_format: "12" } }));
  row(h12, PHONE.id).click();
  await flush();
  assert.deepEqual(labels(h12), ["6:00 AM · Gym"]);
});

test("an Automations row with nothing says so", async () => {
  const el = mount({ devices: [TEST] }, makeHass());
  row(el, PHONE.id).click();
  await flush();
  assert.equal(text($(el, ".details p")), "No automations use this phone or its alarms.");
  assert.equal(text($(el, ".link")), "Show all entities");
});

test("the phone row stays when no alarm is shown, above the empty message", () => {
  const none = mount({}, makeHass({ phones: [{ ...PHONE, alarms: [] }] }));
  assert.match(text($(none, ".empty")), /No alarms yet/);
  ok(row(none, PHONE.id).compareDocumentPosition($(none, ".empty")) & Node.DOCUMENT_POSITION_FOLLOWING);
  const allOff = PHONE.alarms.map((alarm) => ({ ...alarm, enabled: false }));
  const hidden = mount({ show_disabled: false }, makeHass({ phones: [{ ...PHONE, alarms: allOff }] }));
  ok(row(hidden, PHONE.id));
  assert.equal($$(hidden, `${ALARM} .time`).length, 0);
});

test("no Automations row with automations off", () => {
  ok(!row(mount({ show_automations: false }, makeHass()), PHONE.id));
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

test("many automations: five, then all, counted across groups", async () => {
  const hass = makeHass();
  const el = mount({}, hass);
  row(el, PHONE.id).click();
  await flush();
  assert.equal(names(el).length, 5);
  assert.deepEqual(labels(el), ["06:00 · Gym", "07:35 · 1️⃣ Pierwszy", "07:40 · ⚠️ Drugi"]);
  // Drugi shows one of its 20: the count says so.
  assert.deepEqual(counts(el), ["1", "3", "20"]);
  // Drugi's 20 repeat Pierwszy's 3: each alarm lists all of its own.
  assert.equal(text($(el, ".more")), "Show all (24)");
  $(el, ".more").focus();
  // A state change while "Show all" only has focus keeps it there.
  el.hass = withState(hass, "automation.bedroom_lights_on", "off");
  assert.equal(el.shadowRoot.activeElement, $(el, ".more"));
  $(el, ".more").click();
  assert.equal(names(el).length, 24);
  ok(!$(el, '[data-action="more"]'));
  // The keyboard goes on with the first automation that "Show all" revealed.
  assert.equal(el.shadowRoot.activeElement, $$(el, ".automation")[5]);
  const drugi = names(el).slice(4);
  assert.deepEqual(drugi, [...drugi].sort((a, b) => a.localeCompare(b)));
  // Focus stays on the copy under Drugi when a state change renders again.
  const copies = () => $$(el, ".automation").filter((b) => b.dataset.key === "automation.coffee_machine");
  copies()[1].focus();
  el.hass = withState(hass, "automation.coffee_machine", "off");
  assert.equal(el.shadowRoot.activeElement, copies()[1]);
  // A long list folds back, with focus on "Show all" so the panel stays in view.
  assert.equal(text($$(el, ".more").at(-1)), "Show less");
  $$(el, ".more").at(-1).click();
  assert.equal(names(el).length, 5);
  assert.equal(el.shadowRoot.activeElement, $(el, '[data-action="more"]'));
});

test("a failed lookup says so and the next tap tries again", async () => {
  const hass = makeHass();
  const working = hass.callWS;
  hass.callWS = async () => {
    throw new Error("nope");
  };
  const el = mount({ devices: [FIRST] }, hass);
  row(el, PHONE.id).click();
  await flush();
  assert.match(text($(el, ".details")), /Couldn't load automations\./);
  hass.callWS = working;
  assert.equal(text($(el, '[data-action="retry"]')), "Try again");
  $(el, '[data-action="retry"]').click();
  assert.match(text($(el, ".details")), /Loading…/);
  assert.equal(el.shadowRoot.activeElement, row(el, PHONE.id));
  await flush();
  assert.equal(names(el).length, 3);
});

test("a late reply for a closed row is dropped, a detached card keeps it", async () => {
  const hass = makeHass();
  let replies = [];
  // The phone's device comes first, then its event entities and the alarm.
  hass.callWS = () => new Promise((resolve) => replies.push(resolve));
  const reply = (result) => {
    replies.forEach((resolve, i) => resolve(i === 0 ? result : {}));
    replies = [];
  };
  const el = mount({ devices: [FIRST] }, hass);
  row(el, PHONE.id).click();
  row(el, PHONE.id).click();
  reply({ automation: ["automation.coffee_machine"] });
  await flush();
  ok(!$(el, ".details"));

  row(el, PHONE.id).click();
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
  const el = mount({ devices: [FIRST] }, makeHass());
  const opened = [];
  document.body.addEventListener("hass-more-info", (ev) => opened.push(ev.detail.entityId));
  row(el, PHONE.id).click();
  await flush();
  $(el, ".automation").click();
  assert.deepEqual(opened, ["automation.bedroom_lights_on"]);
});

test("an automation gone after the lookup leaves the list", async () => {
  const hass = makeHass();
  const el = mount({ devices: [FIRST] }, hass);
  row(el, PHONE.id).click();
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

test("options: title, no disabled alarms, two phones", () => {
  const el = mount({ title: "Alarms", show_disabled: false }, makeHass({ phones: [PHONE, SECOND_PHONE] }));
  assert.equal(text($(el, ".title")), "Alarms");
  assert.deepEqual($$(el, ".phone").map(text), ["Anna's iPhone", "John's iPhone"]);
  ok(!row(el, GYM));
});

test("options of older versions are ignored", () => {
  const el = mount({ show_sleep: true, show_other: false }, makeHass());
  assert.equal($$(el, `${ALARM} .time`).length, 4);
});

test("picked alarms show alone", () => {
  const el = mount({ devices: [TEST] }, makeHass());
  assert.deepEqual($$(el, `${ALARM} .time`).map(text), ["16:43"]);
});

test("empty states and a deleted device", () => {
  const none = mount({}, makeHass({ phones: [] }));
  assert.match(text($(none, ".empty")), /No phones yet/);
  const noAlarms = mount({}, makeHass({ phones: [{ ...SECOND_PHONE, alarms: [] }] }));
  assert.match(text($(noAlarms, ".empty")), /No alarms yet/);
  const filtered = mount({ devices: ["gone"] }, makeHass());
  assert.equal(text($(filtered, ".empty")), "No alarms match this card's filters.");
  assert.equal(text($(filtered, ".warning")), "1 selected device no longer exists.");
});

test("templates set the options and change them live", async () => {
  const hass = makeHass();
  const guests = "{{ is_state('input_boolean.guests', 'off') }}";
  const el = mount({ devices: "{{ device_list }}", show_disabled: guests }, hass);
  await flush();
  const devices = hass.templates.get("{{ device_list }}");
  const disabled = hass.templates.get(guests);
  assert.deepEqual(devices.msg, { type: "render_template", template: "{{ device_list }}", variables: { user: "Anna" }, report_errors: true });
  // Nothing until every template answered: a moment of every alarm would be wrong.
  devices.send({ result: [FIRST, GYM] });
  assert.equal($$(el, ALARM).length, 0);
  disabled.send({ result: true });
  assert.equal($$(el, `${ALARM} .time`).length, 2);
  disabled.send({ result: false });
  assert.equal($$(el, `${ALARM} .time`).length, 1);
  // A warning comes with a result after it; an error falls back to the default and says so.
  devices.send({ error: "'x' is undefined", level: "WARNING" });
  assert.equal($$(el, ".warning").length, 0);
  devices.send({ error: "UndefinedError: 'device_list' is undefined", level: "ERROR" });
  assert.equal(text($(el, ".warning")), `The template of "Phones or alarms" doesn't work: UndefinedError: 'device_list' is undefined`);
  assert.equal($$(el, `${ALARM} .time`).length, 3);
  // "on" is text, not true.
  disabled.send({ result: "on" });
  assert.equal(text($$(el, ".warning")[1]), `The template of "Show alarms that are off" gives the wrong kind of value. See the card's documentation.`);
});

test("a template that Home Assistant refuses says so", async () => {
  const hass = makeHass();
  hass.connection.subscribeMessage = async () => {
    throw { code: "template_error", message: "TemplateSyntaxError: unexpected '}'" };
  };
  const el = mount({ title: "{{ x }" }, hass);
  await flush();
  assert.equal(text($(el, ".warning")), `The template of "Title" doesn't work: TemplateSyntaxError: unexpected '}'`);
  ok(!$(el, ".title"));
});

test("subscriptions end with the card and only change with their template", async () => {
  const hass = makeHass();
  const el = mount({ title: "{{ user }}" }, hass);
  await flush();
  const first = hass.templates.get("{{ user }}");
  first.send({ result: "Anna" });
  assert.equal(text($(el, ".title")), "Anna");
  // The editor's preview sets the config on every key.
  el.setConfig({ title: "{{ user }}", show_disabled: false });
  assert.equal(text($(el, ".title")), "Anna");
  el.setConfig({ title: "{{ user ~ '!' }}" });
  await flush();
  ok(first.closed);
  // The old card stays until the new template answers; the old one's late answer is dropped.
  first.send({ result: "late" });
  assert.equal(text($(el, ".title")), "Anna");
  const second = hass.templates.get("{{ user ~ '!' }}");
  second.send({ result: "Anna!" });
  assert.equal(text($(el, ".title")), "Anna!");
  document.body.removeChild(el);
  await flush();
  ok(second.closed);
  // Back on the dashboard: the last title shows until the new subscription answers.
  hass.templates.clear();
  document.body.appendChild(el);
  await flush();
  assert.equal(text($(el, ".title")), "Anna!");
  ok(hass.templates.get("{{ user ~ '!' }}") !== second);
});

test("a bad config is refused", () => {
  const el = document.createElement("iphone-alarms-card");
  assert.throws(() => el.setConfig({ devices: 5 }), /devices/);
});

test("12-hour clocks", () => {
  const el = mount({}, makeHass({ locale: { time_format: "12" } }));
  assert.deepEqual($$(el, `${ALARM} .time`).map((t) => t.textContent), ["6:00AM", "7:35AM", "7:40AM", "4:43PM"]);
});

test("the documented styling hooks exist", async () => {
  const el = mount({}, makeHass());
  const style = $(el, "style").textContent;
  for (const name of ["time-size", "time-weight", "row-padding", "disabled-opacity", "on-color", "panel-color"]) {
    ok(style.includes(`--iphone-alarms-${name}`), name);
  }
  row(el, PHONE.id).click();
  await flush();
  for (const cls of ["section", "row", "time", "subtitle", "status", "details", "automation"]) {
    ok($(el, `.${cls}`), cls);
  }
});

test("the editor form and the card picker", () => {
  const Card = customElements.get("iphone-alarms-card");
  ok(Card.getConfigElement() instanceof HTMLElement);
  const form = card.editorForm({});
  assert.deepEqual(
    form.schema.map((s) => s.name),
    ["title", "devices", "show_disabled", "show_last_events", "show_automations", "templates"],
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
  $$(el, ".time, .subtitle, .status, dt, dd, .label, .details p, .link, .automation, .more")
    .map((node) => node.getAttribute("aria-label") ?? text(node))
    .filter(Boolean);
// The editor's labels and helpers; Home Assistant puts the user's language on <html lang>.
const editor = (lang) => {
  document.documentElement.lang = lang;
  const form = card.editorForm({});
  const fields = form.schema.map((field) => [form.computeLabel(field), form.computeHelper(field)]);
  document.documentElement.lang = "";
  return fields;
};
const inLanguage = (language, config = {}) => mount(config, makeHass({ locale: { language } }));

// An open alarm, then the open Automations row.
async function openBoth(language) {
  const el = inLanguage(language);
  row(el, FIRST).click();
  const alarm = screen(el);
  row(el, PHONE.id).click();
  await flush();
  return [...alarm, "---", ...screen(el)];
}

test("Polish: the card and its editor", async (t) => {
  t.assert.snapshot(await openBoth("pl"));
  t.assert.snapshot(editor("pl"));
  const gone = (n) => text($(inLanguage("pl", { devices: Array.from({ length: n }, (_, i) => `gone${i}`) }), ".warning"));
  assert.deepEqual([1, 2, 5].map(gone), [
    "1 wybrane urządzenie już nie istnieje.",
    "2 wybrane urządzenia już nie istnieją.",
    "5 wybranych urządzeń już nie istnieje.",
  ]);
});

test("a language the card doesn't know falls back to English", async (t) => {
  const shown = await openBoth("tlh");
  assert.deepEqual(shown, await openBoth("en"));
  t.assert.snapshot(shown);
  t.assert.snapshot(editor("tlh"));
});
