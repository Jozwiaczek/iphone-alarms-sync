// Screenshots of the dashboard card, from tests/frontend/preview.html and its fake data.
//   node scripts/card_screenshots.mjs [out-dir]   every scenario, light and dark (default out: card-screenshots/)
//   node scripts/card_screenshots.mjs --readme    rewrites assets/card-light.png and assets/card-dark.png
//   add --lang=pl for the card in another language (the README pictures stay in English)
// Uses the Google Chrome installed on this machine (playwright-core downloads no browser).
import { createReadStream } from "node:fs";
import { mkdir } from "node:fs/promises";
import { createServer } from "node:http";
import { extname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright-core";

import { NOW } from "../tests/frontend/fixtures.js";

const ROOT = fileURLToPath(new URL("..", import.meta.url));
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".json": "application/json" };
const args = process.argv.slice(2);
const readme = args.includes("--readme");
const lang = readme ? "en" : (args.find((arg) => arg.startsWith("--lang="))?.slice(7) ?? "en");
const outDir = readme ? join(ROOT, "assets") : (args.find((arg) => !arg.startsWith("--")) ?? join(ROOT, "card-screenshots"));

const server = createServer((req, res) => {
  const path = normalize(join(ROOT, decodeURIComponent(new URL(req.url, "http://x").pathname)));
  if (!path.startsWith(ROOT)) return res.writeHead(403).end();
  res.setHeader("Content-Type", TYPES[extname(path)] ?? "application/octet-stream");
  createReadStream(path)
    .on("error", () => res.writeHead(404).end())
    .pipe(res);
});
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
const base = `http://127.0.0.1:${server.address().port}/tests/frontend/preview.html`;

const browser = await chromium.launch({ channel: "chrome" });
const errors = [];
try {
  await mkdir(outDir, { recursive: true });
  const shots = [];
  if (readme) {
    for (const theme of ["light", "dark"]) shots.push({ scenario: "readme", theme, width: 390, file: `card-${theme}.png` });
  } else {
    const page = await browser.newPage();
    await page.goto(base);
    const scenarios = await page.waitForFunction(() => window.SCENARIOS).then((h) => h.jsonValue());
    await page.close();
    for (const scenario of scenarios) {
      for (const theme of ["light", "dark"]) shots.push({ scenario, theme, width: 390, file: `${scenario}-${theme}.png` });
    }
    for (const width of [180, 300, 600]) shots.push({ scenario: "expanded", theme: "dark", width, file: `expanded-dark-${width}.png` });
  }
  for (const shot of shots) {
    const page = await browser.newPage({ deviceScaleFactor: 2, viewport: { width: shot.width + 32, height: 800 } });
    page.on("console", (msg) => msg.type() === "error" && errors.push(`${shot.file}: ${msg.text()}`));
    page.on("pageerror", (err) => errors.push(`${shot.file}: ${err.message}`));
    await page.clock.setFixedTime(NOW);
    await page.goto(`${base}?scenario=${shot.scenario}&theme=${shot.theme}&width=${shot.width}&lang=${lang}${readme ? "&transparent" : ""}`);
    await page.waitForSelector("body[data-ready]");
    await page.locator("#stage").screenshot({ path: join(outDir, shot.file), omitBackground: readme });
    await page.close();
  }
  console.log(`${shots.length} screenshots in ${outDir}`);
} finally {
  await browser.close();
  server.close();
}
if (errors.length) {
  console.error(errors.join("\n"));
  process.exit(1);
}
