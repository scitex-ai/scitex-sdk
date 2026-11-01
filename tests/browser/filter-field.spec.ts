import { test, expect, type Page } from "@playwright/test";
import { readFile } from "node:fs/promises";
import { resolve, sep } from "node:path";

const source = resolve("src/scitex_sdk");
const ui = "/ui/static/scitex_sdk/ui";
async function mount(page: Page, theme: string, rootSize = 16) {
  await page.route("http://sdk.test/**", async route => {
    const pathname = new URL(route.request().url()).pathname;
    if (pathname === "/") {
      await route.fulfill({ contentType: "text/html", body: `<!doctype html>
        <html data-theme="${theme}"><head>
        <link rel="stylesheet" href="${ui}/css/shell/theme.css">
        <link rel="stylesheet" href="${ui}/css/app/filter-field.css">
        <style>html{font-size:${rootSize}px}body{margin:8px}</style>
        </head><body><div data-stx-filter-field data-filter-subject="agents" data-filter-id="filter"></div>
        <script type="module" src="${ui}/js/app/filter-field.js"></script></body></html>` });
      return;
    }
    const path = resolve(source, "." + pathname);
    if (!path.startsWith(source + sep)) throw new Error("Fixture path escaped SDK");
    await route.fulfill({ contentType: path.endsWith(".css") ? "text/css" : "text/javascript", body: await readFile(path) });
  });
  await page.goto("http://sdk.test/");
  await expect(page.locator("#filter")).toBeVisible();
}
for (const theme of ["light", "dark"]) {
  for (const width of [1440, 390]) {
    test(`filter lifecycle and geometry: ${theme}/${width}`, async ({ page }) => {
      await page.setViewportSize({ width, height: 844 });
      await mount(page, theme);
      const input = page.locator("#filter");
      const hint = page.locator(".stx-filter-field__hint");
      await expect(input).toHaveAttribute("placeholder", "Filter agents with keywords");
      await expect(hint).toHaveText("Ctrl+K");
      await page.keyboard.press("Control+k");
      await expect(input).toBeFocused();
      await expect(hint).toHaveText("Esc");
      await input.fill("worker");
      await page.evaluate(() => {
        const input = document.querySelector('input')!;
        input.addEventListener('input', () => input.dataset.observed = input.value);
      });
      await input.press("Escape");
      await expect(input).toHaveValue("");
      await expect(input).toHaveAttribute("data-observed", "");
      await expect(input).not.toBeFocused();
      await expect(hint).toHaveText("Ctrl+K");
      await input.click();
      await expect(hint).toHaveText("Esc");
      await input.blur();
      await expect(hint).toHaveText("Ctrl+K");
      const geometry = await page.locator('[data-stx-filter-field]').evaluate(root => {
        const icon = root.querySelector('svg')!.getBoundingClientRect();
        const input = root.querySelector('input')!.getBoundingClientRect();
        const hint = root.querySelector('kbd')!;
        return { iconBeforeInput: icon.right < input.left, right: root.getBoundingClientRect().right,
          hintRight: hint.getBoundingClientRect().right, hintOpacity: getComputedStyle(hint).opacity,
          font: getComputedStyle(root.querySelector('input')!).fontSize };
      });
      expect(geometry.iconBeforeInput).toBe(true);
      expect(geometry.hintRight).toBeLessThanOrEqual(geometry.right);
      expect(geometry.hintOpacity).toBe("0.6");
      expect(geometry.font).toBe("14px");
    });
  }
}

test("mount is idempotent and destroy releases shortcut ownership", async ({ page }) => {
  await mount(page, "light", 14);
  const result = await page.evaluate(async ui => {
    const { mountFilterFields } = await import(`${ui}/js/app/filter-field.js`);
    const [first] = mountFilterFields();
    const [again] = mountFilterFields();
    const same = first === again;
    first.destroy();
    const [fresh] = mountFilterFields();
    return { same, fresh: fresh !== first, inputs: document.querySelectorAll('input').length };
  }, ui);
  expect(result).toEqual({ same: true, fresh: true, inputs: 1 });
  await page.keyboard.press("Meta+k");
  await expect(page.locator("#filter")).toBeFocused();
});
