import { test, expect, type Page } from "@playwright/test";
import { readFile } from "node:fs/promises";
import { resolve, sep } from "node:path";

const source = resolve("src/scitex_sdk");
const ui = "/ui/static/scitex_sdk/ui";
const labels = ["SDK", "Agent Container", "Agentic Journal", "A longer research application"];
const buttons = (count: number) => labels.slice(0, count).map((label, index) =>
  `<button class="stx-content-tabs__tab" role="tab" aria-selected="${index === 0}" tabindex="${index === 0 ? 0 : -1}"><span>${label}<br><small>v0.123.45</small></span></button>`,
).join("");

async function mount(page: Page, theme: string) {
  await page.route("http://sdk.test/**", async route => {
    const pathname = new URL(route.request().url()).pathname;
    if (pathname === "/") {
      await route.fulfill({ contentType: "text/html", body: `<!doctype html><html data-theme="${theme}"><head>
        <link rel="stylesheet" href="${ui}/css/shell/theme.css">
        <link rel="stylesheet" href="${ui}/css/app/content-tabs.css">
        <link rel="stylesheet" href="${ui}/css/app/content-tabs-sizing.css">
        <style>html{font-size:14px}body{margin:12px;font-family:sans-serif}main{max-width:960px}</style>
        </head><body><main>${[2, 3, 4].map(count => `<div class="stx-content-tabs stx-content-tabs--uniform" role="tablist">${buttons(count)}</div>`).join("")}
        <div class="stx-content-tabs custom stx-content-tabs--uniform" style="--stx-content-tabs-tab-width:11rem" role="tablist">${buttons(2)}</div>
        <div class="stx-content-tabs default" role="tablist">${buttons(2)}</div></main></body></html>` });
      return;
    }
    const path = resolve(source, "." + pathname);
    if (!path.startsWith(source + sep)) throw new Error("Fixture escaped SDK source");
    await route.fulfill({ contentType: "text/css", body: await readFile(path) });
  });
  await page.goto("http://sdk.test/");
}

for (const theme of ["light", "dark"]) {
  for (const width of [1440, 390]) {
    test(`uniform widths across different tab counts: ${theme}/${width}`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 });
      await mount(page, theme);
      const sizes = await page.locator('.stx-content-tabs--uniform:not(.custom) > button').evaluateAll(tabs => tabs.map(tab => tab.getBoundingClientRect().width));
      expect(Math.max(...sizes) - Math.min(...sizes)).toBeLessThanOrEqual(1);
      expect(sizes.every(size => Math.abs(size - 126) <= 1)).toBe(true);
      const custom = await page.locator('.custom > button').evaluateAll(tabs => tabs.map(tab => tab.getBoundingClientRect().width));
      expect(custom.every(size => Math.abs(size - 154) <= 1)).toBe(true);
      const defaults = await page.locator('.default > button').evaluateAll(tabs => tabs.map(tab => getComputedStyle(tab).flex));
      expect(defaults).toEqual(["1 0 auto", "1 0 auto"]);
      const readable = await page.locator('.stx-content-tabs--uniform > button').evaluateAll(tabs => tabs.every(tab => {
        const label = tab.querySelector('span')!;
        return tab.getBoundingClientRect().height >= 44 && label.scrollWidth <= tab.clientWidth && label.getBoundingClientRect().height <= tab.getBoundingClientRect().height;
      }));
      expect(readable).toBe(true);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      const lastRow = page.locator('.stx-content-tabs--uniform:not(.custom)').last();
      expect(await lastRow.evaluate(row => row.scrollWidth > row.clientWidth)).toBe(width === 390);
      const selected = page.locator('.stx-content-tabs--uniform > [aria-selected="true"]').first();
      expect(await selected.evaluate(tab => getComputedStyle(tab).borderBottomColor)).toBe(theme === "dark" ? "rgb(212, 168, 122)" : "rgb(26, 42, 64)");
    });
  }
}
