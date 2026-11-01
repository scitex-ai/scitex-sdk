/** Verify normally delivered app headers, without selecting a project or saving a theme. */
import { chromium } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

const base = process.env.SCITEX_HEADER_BASE_URL;
if (!base || !/^https?:\/\//.test(base)) throw new Error("Set SCITEX_HEADER_BASE_URL to the authorized host URL");
const routes = JSON.parse(process.env.SCITEX_HEADER_ROUTES || JSON.stringify([
  "cards/#dm", "cards/#board", "storage/", "scholar/", "stats/", "figrecipe/",
  "writer/", "sdk/", "live-paper/", "agentic-journal/", "agent-container/",
]));
if (!Array.isArray(routes) || !routes.length || routes.some(r => typeof r !== "string" || r.startsWith("/") || r.includes("://"))) {
  throw new Error("SCITEX_HEADER_ROUTES must be a nonempty JSON array of app-relative routes");
}
const out = resolve(process.env.SCITEX_HEADER_REPORT_DIR || "test-results/header-fleet");
await mkdir(out, { recursive: true, mode: 0o700 });
const browser = await chromium.launch(process.env.SCITEX_TEST_CHROMIUM ? { executablePath: process.env.SCITEX_TEST_CHROMIUM } : {});
const context = await browser.newContext({ storageState: process.env.SCITEX_HEADER_STORAGE_STATE || undefined });
const page = await context.newPage();
const rows = [], failures = [];
const fields = ["fontFamily", "fontSize", "fontWeight", "lineHeight", "color", "backgroundColor", "padding", "margin", "borderRadius", "borderBottomWidth", "borderBottomColor"];
try {
  for (const width of [1440, 390]) {
    const references = new Map();
    await page.setViewportSize({ width, height: 1000 });
    for (const route of routes) {
      const url = new URL("apps/" + route, base.replace(/\/?$/, "/"));
      const row = { route, width, states: [] };
      try {
        const response = await page.goto(url.href, { waitUntil: "domcontentloaded", timeout: 45000 });
        if (response && response.status() !== 200) throw new Error(`HTTP ${response.status()}`);
        await page.locator(".stx-app-header .stx-app-project-selector__trigger").waitFor({ timeout: 15000 });
        if (await page.locator(".stx-app-header").count() !== 1) throw new Error("Expected exactly one shared header");
        // Leaf modules can arrive after DOMContentLoaded. Wait for load rather
        // than network-idle: running apps legitimately poll APIs continuously.
        await page.waitForLoadState("load", { timeout: 15000 });
        await page.mouse.move(0, 0);
        for (const theme of ["light", "dark"]) {
          await page.evaluate(t => {
            document.documentElement.dataset.theme = t;
            document.documentElement.dataset.colorMode = t;
            document.body.classList.remove("dark-theme", "light-theme");
            document.body.classList.add(t + "-theme");
          }, theme);
          await page.waitForTimeout(250);
          await page.locator(".stx-app-header .stx-app-project-selector__trigger").click();
          await page.mouse.move(0, 0);
          await page.waitForTimeout(250);
          const styles = await page.evaluate(keys => {
            const pick = selector => {
              const e = document.querySelector(selector);
              if (!e) return null;
              const s = getComputedStyle(e);
              return Object.fromEntries(keys.map(k => [k, s[k]]));
            };
            return { header: pick(".stx-app-header"), title: pick(".stx-app-header__title"),
              version: pick(".stx-app-header__version:not([hidden])"),
              trigger: pick(".stx-app-header .stx-app-project-selector__trigger"),
              option: pick(".stx-app-header .stx-app-project-selector__option:not(.stx-app-project-selector__option--current)"),
              search: pick(".stx-app-header .stx-app-project-selector__search") };
          }, fields);
          await page.keyboard.press("Escape");
          const reference = references.get(theme);
          if (!reference) references.set(theme, styles);
          else for (const part of ["header", "title", "version", "trigger", "option", "search"]) {
            // An unknown version is intentionally absent; compare its appearance when present.
            if (part === "version" && (!styles[part] || !reference[part])) continue;
            if (part === "option" && (!styles[part] || !reference[part])) continue;
            for (const field of fields) if (styles[part]?.[field] !== reference[part]?.[field]) {
              failures.push({ route, width, theme, part, field, expected: reference[part]?.[field], actual: styles[part]?.[field] });
            }
          }
          if (styles.title?.fontSize !== "14px" || styles.trigger?.fontSize !== "14px") failures.push({ route, width, theme, error: "Shared title/trigger typography missing" });
          row.states.push({ theme, styles });
        }
      } catch (error) { failures.push({ route, width, error: error.message }); }
      rows.push(row);
      console.log(`${route} ${width}px checked`);
    }
  }
} finally { await browser.close(); }
await writeFile(resolve(out, "report.json"), JSON.stringify({ rows, failures, passed: !failures.length }, null, 2), { mode: 0o600 });
if (failures.length) {
  console.error(`${failures.length} header differences or delivery failures; inspect ${resolve(out, "report.json")}`);
  process.exitCode = 1;
} else console.log(`${rows.length * 2} app/theme/viewport states match the shared header contract`);
