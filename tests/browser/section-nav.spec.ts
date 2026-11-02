import { test, expect, type Page } from "@playwright/test";
import { readFile } from "node:fs/promises";
import { resolve, sep } from "node:path";

const source = resolve("src/scitex_sdk");
const ui = "/ui/static/scitex_sdk/ui";
async function mount(page: Page, theme = "light", initial = "", script = true) {
  await page.route("http://sdk.test/**", async route => {
    const pathname = new URL(route.request().url()).pathname;
    if (pathname === "/") {
      await route.fulfill({ contentType: "text/html", body: `<!doctype html>
<html data-theme="${theme}"><head><link rel="stylesheet" href="${ui}/css/shell/theme.css">
<link rel="stylesheet" href="${ui}/css/app/content-tabs.css">
<style>:root{--header-height:64px}body{margin:0;padding-top:64px}
header{position:fixed;top:0;height:var(--header-height);width:100%;background:gray;z-index:3}
nav{position:sticky;top:var(--header-height);z-index:2}section{position:relative;scroll-margin-top:120px}
#one{height:500px}#two{height:900px}#three{height:80px}#context{position:absolute;top:0;scroll-margin-top:120px}
</style></head><body><header>Owned header</header>
<nav data-stx-section-nav aria-label="Sections" class="stx-content-tabs">
<a class="stx-content-tabs__tab" href="#one">One</a><a class="stx-content-tabs__tab" href="#two">Two</a>
<a class="stx-content-tabs__tab" href="#three">Three</a></nav>
<section id="one">First</section><section id="two"><span id="context"></span>Second</section>
<section id="three">Last, short section</section>
${script ? `<script type="module" src="${ui}/js/app/section-nav.js"></script>` : ""}</body></html>` });
      return;
    }
    const path = resolve(source, "." + pathname);
    if (!path.startsWith(source + sep)) throw new Error("Fixture path escaped SDK");
    await route.fulfill({ contentType: path.endsWith(".css") ? "text/css" : "text/javascript", body: await readFile(path) });
  });
  await page.goto("http://sdk.test/" + initial);
  if (script) await expect(page.locator("nav")).toHaveAttribute("data-stx-section-nav-mounted", "");
}
const current = (page: Page) => page.locator("nav a[aria-current=location]");

for (const width of [1440, 390]) {
  test(`native wheel and short final section, URL unchanged: ${width}`, async ({ page }) => {
    await page.setViewportSize({ width, height: 844 });
    await mount(page);
    await expect(current(page)).toHaveAttribute("href", "#one");
    await page.mouse.move(200, 400);
    await page.mouse.wheel(0, 600);
    await expect(current(page)).toHaveAttribute("href", "#two");
    await expect(page).toHaveURL("http://sdk.test/");
    await page.mouse.wheel(0, 3000);
    await expect(current(page)).toHaveAttribute("href", "#three");
    await expect(page.locator("section[hidden],nav a[aria-selected]")).toHaveCount(0);
  });
}

test("native links, history and initial aliases keep correct current section", async ({ page }) => {
  await mount(page, "light", "#context");
  await expect(current(page)).toHaveAttribute("href", "#two");
  await page.locator('nav a[href="#one"]').click();
  await expect(current(page)).toHaveAttribute("href", "#one");
  await page.locator('nav a[href="#three"]').click();
  await expect(current(page)).toHaveAttribute("href", "#three");
  await page.goBack();
  await expect(current(page)).toHaveAttribute("href", "#one");
  await page.goForward();
  await expect(current(page)).toHaveAttribute("href", "#three");
});

test("real header resizing updates the visible boundary without a scroll event", async ({ page }) => {
  await mount(page);
  await page.mouse.move(200, 400);
  await page.mouse.wheel(0, 450);
  await expect(current(page)).toHaveAttribute("href", "#one");
  await page.evaluate(() => document.documentElement.style.setProperty("--header-height", "140px"));
  await expect(current(page)).toHaveAttribute("href", "#two");
});

for (const theme of ["light", "dark"]) {
  test(`aria-current links match selected button underline: ${theme}`, async ({ page }) => {
    await mount(page, theme);
    await page.evaluate(() => {
      const button = document.createElement("button");
      button.className = "stx-content-tabs__tab";
      button.setAttribute("aria-selected", "true");
      button.id = "reference";
      document.querySelector("section")!.append(button);
      const anchor = document.createElement("a");
      anchor.className = "stx-content-tabs__tab";
      anchor.setAttribute("aria-current", "page");
      anchor.href = "#one";
      anchor.id = "page-reference";
      document.querySelector("section")!.append(anchor);
    });
    const styles = await page.evaluate(() => {
      const read = (selector: string) => {
        const style = getComputedStyle(document.querySelector(selector)!);
        return [style.borderBottomWidth, style.borderBottomColor, style.color, style.fontWeight, style.textDecorationLine];
      };
      return [read('nav a[aria-current="location"]'), read("#reference"), read("#page-reference")];
    });
    expect(styles[0]).toEqual(styles[1]);
    expect(styles[0]).toEqual(styles[2]);
    expect(styles[0][0]).toBe("2px");
    expect(styles[0][4]).toBe("none");
  });
}

test("without JS native anchors still navigate and all content remains present", async ({ page }) => {
  await mount(page, "light", "", false);
  await page.locator('nav a[href="#two"]').click();
  await expect(page).toHaveURL("http://sdk.test/#two");
  await expect(page.locator("section")).toHaveCount(3);
  await expect(page.locator("section[hidden]")).toHaveCount(0);
});
