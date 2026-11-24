// Gives Node a browser DOM (happy-dom) and loads the card into it.
import { Window } from "happy-dom";

const window = new Window({ url: "http://localhost/" });
for (const name of ["window", "document", "customElements", "HTMLElement", "CSS", "Node", "CustomEvent"]) {
  globalThis[name] = name === "window" ? window : window[name];
}

export const card = await import("../../custom_components/iphone_alarms_sync/frontend/iphone-alarms-card.js");

/** Mount a card and give it a config and `hass`. */
export function mount(config, hass) {
  const el = document.createElement("iphone-alarms-card");
  el.setConfig(config);
  el.hass = hass;
  document.body.appendChild(el);
  return el;
}

export const flush = () => new Promise((resolve) => setTimeout(resolve, 0));
