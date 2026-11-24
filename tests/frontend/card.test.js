// Pure helpers of the dashboard card.
import assert from "node:assert/strict";
import { test } from "node:test";

import { card } from "./dom.js";
import { makeHass, NOW, PHONE, SECOND_PHONE, TIME_ZONE } from "./fixtures.js";

const { validateConfig, describeRepeat, formatClock, formatEventTime, lastRing, buildIndex, selectAlarms, relatedItems, timeContext, strings } = card;
const ctx = (overrides = {}) => ({ h12: false, timeZone: TIME_ZONE, now: NOW, t: strings(), ...overrides });
const config = (overrides = {}) => validateConfig(overrides);

test("validateConfig fills defaults and rejects wrong types", () => {
  assert.deepEqual(validateConfig({ type: "x" }), {
    type: "x",
    devices: [],
    show_disabled: true,
    show_automations: true,
    show_last_events: true,
  });
  assert.equal(validateConfig({ show_disabled: false }).show_disabled, false);
  // Options of older versions are kept, not rejected, so old cards still load.
  assert.equal(validateConfig({ show_sleep: true }).show_sleep, true);
  for (const bad of [null, [], { title: 3 }, { devices: "a" }, { devices: [1] }, { show_disabled: "no" }]) {
    assert.throws(() => validateConfig(bad));
  }
});

test("describeRepeat writes days like iOS", () => {
  const week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
  assert.equal(describeRepeat([...week, "Saturday", "Sunday"]), "Every day");
  assert.equal(describeRepeat(week), "Weekdays");
  assert.equal(describeRepeat(["Sunday", "Saturday"]), "Weekends");
  assert.equal(describeRepeat(["Wednesday", "Tuesday"]), "Tue and Wed");
  assert.equal(describeRepeat(["Friday"]), "Every Friday");
  assert.equal(describeRepeat(["Monday", "Wednesday", "Friday"]), "Mon, Wed, Fri");
  assert.equal(describeRepeat([]), "");
});

test("formatClock follows 12 and 24 hours", () => {
  assert.deepEqual(formatClock(7, 5, ctx()), { time: "07:05", period: "" });
  assert.deepEqual(formatClock(0, 30, ctx({ h12: true })), { time: "12:30", period: "AM" });
  assert.deepEqual(formatClock(16, 43, ctx({ h12: true })), { time: "4:43", period: "PM" });
});

test("timeContext reads the user's profile", () => {
  assert.equal(timeContext({ locale: { time_format: "12" }, config: {} }).h12, true);
  assert.equal(timeContext({ locale: { time_format: "language", language: "en-US" }, config: {} }).h12, true);
  assert.equal(timeContext({ locale: { time_format: "language", language: "pl" }, config: {} }).h12, false);
  assert.equal(timeContext({ locale: { time_zone: "server" }, config: { time_zone: TIME_ZONE } }).timeZone, TIME_ZONE);
  assert.equal(timeContext({ locale: { time_zone: "local" }, config: { time_zone: TIME_ZONE } }).timeZone, undefined);
});

test("formatEventTime shows how old an event is", () => {
  assert.equal(formatEventTime("2026-11-24T06:35:00Z", ctx()), "07:35");
  assert.equal(formatEventTime("2026-11-24T06:35:00Z", ctx({ h12: true })), "7:35 AM");
  assert.equal(formatEventTime("2026-11-23T06:40:00Z", ctx()), "Yesterday 07:40");
  assert.equal(formatEventTime("2026-11-20T06:40:00Z", ctx()), "Fri 07:40");
  assert.equal(formatEventTime("2026-11-10T06:40:00Z", ctx()), "Nov 10");
  // 23:30 UTC on the 23rd is already the 24th in Warsaw.
  assert.equal(formatEventTime("2026-11-23T23:30:00Z", ctx()), "00:30");
  for (const empty of [null, "unknown", "unavailable", "nonsense"]) assert.equal(formatEventTime(empty, ctx()), null);
});

test("lastRing prefers what the phone reported", () => {
  const at = (iso, estimated) => ({ at: new Date(iso), estimated });
  assert.equal(lastRing(null, "unknown"), null);
  assert.deepEqual(lastRing("2026-11-09T07:37:00Z", null), at("2026-11-09T07:37:00Z", false));
  // The alarm was due today, the phone last reported a ring on the 9th.
  assert.deepEqual(lastRing("2026-11-09T07:37:00Z", "2026-11-24T06:35:00Z"), at("2026-11-24T06:35:00Z", true));
  assert.deepEqual(lastRing(undefined, "2026-11-24T06:35:00Z"), at("2026-11-24T06:35:00Z", true));
  // The phone's "goes off" a few seconds before or after the scheduled minute confirms it.
  assert.deepEqual(lastRing("2026-11-24T06:34:56Z", "2026-11-24T06:35:00Z"), at("2026-11-24T06:34:56Z", false));
  assert.deepEqual(lastRing("2026-11-24T06:36:10Z", "2026-11-24T06:35:00Z"), at("2026-11-24T06:36:10Z", false));
  // A test event from the phone later in the day is the latest ring.
  assert.deepEqual(lastRing("2026-11-24T11:36:59Z", "2026-11-24T06:35:00Z"), at("2026-11-24T11:36:59Z", false));
});

test("selectAlarms filters by phone and alarm", () => {
  const hass = makeHass({ phones: [PHONE, SECOND_PHONE] });
  const index = buildIndex(hass);
  const labels = (view) => view.groups.map((g) => [g.phone.name, g.whole, g.alarms.map((a) => a.label)]);

  assert.deepEqual(labels(selectAlarms(index, config(), hass.states)), [
    ["Anna's iPhone", true, ["Work"]],
    ["John's iPhone", true, ["Gym", "1️⃣ Pierwszy", "⚠️ Drugi", "Test 2"]],
  ]);
  assert.deepEqual(labels(selectAlarms(index, config({ devices: ["0f3e9a1b2c4d5e6f"], show_disabled: false }), hass.states)), [
    ["John's iPhone", true, ["1️⃣ Pierwszy", "⚠️ Drugi", "Test 2"]],
  ]);
  assert.deepEqual(labels(selectAlarms(index, config({ devices: ["3c4d5e6f7a8b9c0d", "6f7a8b9c0d1e2f3a"] }), hass.states)), [
    ["Anna's iPhone", false, ["Work"]],
    ["John's iPhone", false, ["Test 2"]],
  ]);
  // A phone and one of its alarms: the phone wins.
  assert.deepEqual(labels(selectAlarms(index, config({ devices: ["3c4d5e6f7a8b9c0d", "0f3e9a1b2c4d5e6f"] }), hass.states))[0][2].length, 4);
  const gone = selectAlarms(index, config({ devices: ["deleted", "3c4d5e6f7a8b9c0d"] }), hass.states);
  assert.equal(gone.missing, 1);
  assert.equal(gone.groups.length, 1);
});

test("selectAlarms skips unreadable alarms and names empty labels", () => {
  let hass = makeHass();
  const first = "sensor.johns_iphone_1_pierwszy_alarm_id";
  hass.states[first] = { ...hass.states[first], state: "unavailable" };
  const test2 = "sensor.johns_iphone_test_2_alarm_id";
  hass.states[test2] = { ...hass.states[test2], attributes: { ...hass.states[test2].attributes, label: "", repeats: false } };
  const view = selectAlarms(buildIndex(hass), config(), hass.states);
  const alarms = view.groups[0].alarms;
  assert.deepEqual(alarms.map((a) => a.label), ["Gym", "⚠️ Drugi", "Alarm"]);
  assert.equal(alarms[2].repeat, "");
});

test("relatedItems sorts by name and drops what is gone", () => {
  const states = {
    "automation.b": { state: "on", attributes: { friendly_name: "Beta" } },
    "automation.a": { state: "off", attributes: {} },
    "script.c": { state: "off", attributes: { friendly_name: "Alpha" } },
  };
  assert.deepEqual(relatedItems(["automation.b", "automation.a", "script.c", "automation.gone"], states, ["automation.b"]), [
    { id: "script.c", name: "Alpha", off: false, script: true, phone: false },
    { id: "automation.a", name: "automation.a", off: true, script: false, phone: false },
    { id: "automation.b", name: "Beta", off: false, script: false, phone: true },
  ]);
});

test("strings picks the user's language and falls back to English", () => {
  assert.equal(strings("pl").today, "Dziś");
  assert.equal(strings("pl-PL").locale, "pl-PL");
  assert.equal(strings("en-GB").locale, "en-GB");
  assert.equal(strings("tlh").today, "Today");
  assert.equal(strings("tlh").locale, "en-US");
  const pl = strings("pl");
  assert.equal(describeRepeat(["Wednesday", "Tuesday"], pl), "wt. i śr.");
  assert.equal(describeRepeat(["Wednesday"], pl), "Co środę");
  assert.equal(describeRepeat(["Saturday", "Sunday"], pl), "Weekendy");
  assert.equal(formatEventTime("2026-11-20T06:40:00Z", ctx({ t: pl })), "pt. 07:40");
  assert.equal(formatEventTime("2026-11-10T06:40:00Z", ctx({ t: pl })), "10 lis");
});
