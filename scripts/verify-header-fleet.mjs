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
await context.addInitScript(() => {
  window.__scitexHeaderThemeInitialized = false;
  document.addEventListener("theme-changed", () => { window.__scitexHeaderThemeInitialized = true; }, { once: true });
});
const page = await context.newPage();
const rows = [], failures = [];
let themeSaveRequests = 0;
page.on("request", request => {
  if (request.method() === "POST" && new URL(request.url()).pathname === "/auth/api/save-theme/") themeSaveRequests++;
});
const themeEndpoint = new URL("/auth/api/get-theme/", base).href;
const initialTheme = await (await context.request.get(themeEndpoint)).json();
const fields = ["fontFamily", "fontSize", "fontWeight", "lineHeight", "height", "color", "backgroundColor", "padding", "margin", "borderRadius", "borderBottomWidth", "borderBottomColor"];
try {
  for (const width of [1440, 390]) {
    const references = new Map();
    await page.setViewportSize({ width, height: 1000 });
    for (const route of routes) {
      const url = new URL("apps/" + route, base.replace(/\/?$/, "/"));
      const row = { route, width, states: [] };
      try {
        const newDocument = page.url().split("#")[0] !== url.href.split("#")[0];
        const themeResponse = newDocument
          ? page.waitForResponse(r => new URL(r.url()).pathname === "/auth/api/get-theme/", { timeout: 15000 })
              .then(response => ({ response }), error => ({ error }))
          : Promise.resolve({ response: null });
        const response = await page.goto(url.href, { waitUntil: "domcontentloaded", timeout: 45000 });
        if (response && response.status() !== 200) throw new Error(`HTTP ${response.status()}`);
        await page.locator(".stx-app-header .stx-app-project-selector__trigger").waitFor({ timeout: 15000 });
        if (await page.locator(".stx-app-header").count() !== 1) throw new Error("Expected exactly one shared header");
        // Leaf modules can arrive after DOMContentLoaded. Wait for load rather
        // than network-idle: running apps legitimately poll APIs continuously.
        await page.waitForLoadState("load", { timeout: 15000 });
        // The canonical controller applies the saved theme after an async GET.
        // Wait for its real initialization event before our document-only themes.
        const initialized = await themeResponse;
        if (initialized.error) throw initialized.error;
        if (initialized.response) await initialized.response.finished();
        await page.waitForFunction(() => window.__scitexHeaderThemeInitialized === true, null, { timeout: 15000 });
        await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
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
          await page.locator(".stx-app-header .stx-app-project-selector__option").first().waitFor({ timeout: 10000 });
          await page.mouse.move(0, 0);
          await page.waitForTimeout(250);
          const providerUrl = await page.evaluate(() =>
            document.querySelector('.stx-app-header [data-stx-project-picker]')?.getAttribute('data-provider-url') ||
            document.querySelector('meta[name="stx-project-provider"]')?.getAttribute('content'));
          if (!providerUrl) throw new Error("Host project provider metadata is missing");
          const listingResponse = await context.request.get(new URL(providerUrl, page.url()).href);
          if (!listingResponse.ok()) throw new Error(`Project listing HTTP ${listingResponse.status()}`);
          const listing = await listingResponse.json();
          const choices = await page.locator(".stx-app-header .stx-app-project-selector__option").evaluateAll(es => es.map(e => ({ disabled: e.disabled, reason: e.title })));
          if (listing.allow_user_scope === true) {
            if (choices.length !== listing.projects.length + 1) throw new Error("Scoped picker must include visible All Projects alongside the project rows");
            if (choices[0].disabled !== Boolean(listing.user_scope_disabled_reason)) throw new Error("All Projects availability differs from the host policy");
            if (choices[0].disabled && choices[0].reason !== listing.user_scope_disabled_reason) throw new Error("All Projects disabled reason is missing");
            listing.projects.forEach((project, index) => {
              const choice = choices[index + 1];
              if (choice.disabled !== (project.disabled === true)) throw new Error("Project availability differs from host policy");
              if (project.disabled && choice.reason !== (project.disabled_reason || project.disabledReason || "")) throw new Error("Project disabled reason is missing");
            });
          }
          if (width === 390) {
            const geometry = await page.locator(".stx-app-header__slot--project-selector").evaluate(e => {
              const width = e.getBoundingClientRect().width;
              return { slot: width, trigger: e.querySelector('.stx-app-project-selector__trigger').getBoundingClientRect().width,
                panel: e.querySelector('.stx-app-project-selector__panel').getBoundingClientRect().width };
            });
            if (Math.abs(geometry.trigger - geometry.slot) >= 1 || Math.abs(geometry.panel - geometry.slot) >= 1) throw new Error("Phone picker and dropdown must fill the shared slot");
          }
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
            for (const field of fields) if (
              // Project rows may have an owner/detail line; content changes
              // intrinsic height, but header and trigger geometry must match.
              !(field === "height" && part !== "header" && part !== "trigger") &&
              styles[part]?.[field] !== reference[part]?.[field]
            ) {
              failures.push({ route, width, theme, part, field, expected: reference[part]?.[field], actual: styles[part]?.[field] });
            }
          }
          if (styles.title?.fontSize !== "14px" || styles.trigger?.fontSize !== "14px") failures.push({ route, width, theme, error: "Shared title/trigger typography missing" });
          row.states.push({ theme, styles });
        }
      } catch (error) { failures.push({ route, width, error: error.message }); }
      finally { await page.keyboard.press("Escape").catch(() => {}); }
      rows.push(row);
      console.log(`${route} ${width}px checked`);
    }
  }
} finally {
  const finalTheme = await (await context.request.get(themeEndpoint)).json();
  if (themeSaveRequests || finalTheme.theme !== initialTheme.theme) failures.push({ error: "Theme preference changed during the probe", themeSaveRequests });
  await browser.close();
}
await writeFile(resolve(out, "report.json"), JSON.stringify({ rows, failures, themeSaveRequests, passed: !failures.length }, null, 2), { mode: 0o600 });
if (failures.length) {
  console.error(`${failures.length} header differences or delivery failures; inspect ${resolve(out, "report.json")}`);
  process.exitCode = 1;
} else console.log(`${rows.length * 2} app/theme/viewport states match the shared header contract`);
