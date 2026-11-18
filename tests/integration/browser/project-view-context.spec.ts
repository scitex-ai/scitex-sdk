import { test, expect } from "@playwright/test";
import { readFile } from "node:fs/promises";
import { resolve, sep } from "node:path";

const source = resolve("src/scitex_sdk");
const ui = "/ui/static/scitex_sdk/ui";

test("page All view does not save the profile; an explicit pick does", async ({ page }) => {
  const posts: unknown[] = [];
  await page.route("http://sdk.test/**", async route => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/projects") {
      if (route.request().method() === "POST") posts.push(route.request().postDataJSON());
      await route.fulfill({ json: route.request().method() === "POST"
        ? { current: "alpha", current_scope: "project" }
        : { projects: [{ id: "alpha", name: "Alpha" }], current: "alpha", current_scope: "project", allow_user_scope: true } });
      return;
    }
    if (path === "/") {
      await route.fulfill({ contentType: "text/html", body: `<!doctype html><html><head>
        <link rel="stylesheet" href="${ui}/css/app/project-selector.css"></head><body>
        <div data-stx-project-picker data-provider-url="/api/projects" data-allow-user-scope="true"
          data-view-scope="user" data-view-project="" data-navigate=""></div>
        <script type="module" src="${ui}/js/app/project-selector.js"></script></body></html>` });
      return;
    }
    const file = resolve(source, "." + path);
    if (!file.startsWith(source + sep)) throw new Error("Escaped SDK fixture");
    await route.fulfill({ contentType: file.endsWith(".css") ? "text/css" : "text/javascript", body: await readFile(file) });
  });
  await page.goto("http://sdk.test/");
  const trigger = page.locator('.stx-app-project-selector__trigger');
  await expect(trigger).toHaveText("All Projects");
  expect(posts).toEqual([]);
  await trigger.click();
  await page.getByRole('option', { name: "Alpha" }).click();
  await expect(trigger).toHaveText("Alpha");
  expect(posts).toEqual([{ scope: "project", id: "alpha" }]);
});
