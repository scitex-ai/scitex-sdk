import { test, expect } from "@playwright/test";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

for (const theme of ["light", "dark"]) {
  test(`app boundaries have no accent stripe: ${theme}`, async ({ page }) => {
    const root = resolve("src/scitex_sdk/ui/static/scitex_sdk/ui/css/shell");
    const styles = await Promise.all(["theme.css", "app-shell.css", "stx-shell-sidebar.css"].map(file => readFile(resolve(root, file), "utf8")));
    await page.setContent(`<html data-theme="${theme}"><head><style>${styles.join("\n")}</style></head><body>
      <main id="main-content" class="stx-shell-content" data-app-accent="agents">App</main>
      <section class="stx-shell-content" data-app-accent-custom="#ff0000">Custom app</section>
      </body></html>`);
    for (const selector of ["#main-content", "section"]) {
      const stripe = await page.locator(selector).evaluate(element => getComputedStyle(element, "::before").content);
      expect(stripe).toBe("none");
    }
  });
}
