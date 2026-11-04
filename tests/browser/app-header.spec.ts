import { test, expect, type Page } from "@playwright/test";
import { readFile } from "node:fs/promises";
import { resolve, sep } from "node:path";

const source = resolve("src/scitex_sdk");
const ui = "/ui/static/scitex_sdk/ui";

async function mount(page: Page, rootSize: number, theme: string,
  userAllowed = true, projectAllowed = true, wrapped = false, apiDocs = false) {
  await page.route("http://sdk.test/**", async route => {
    const pathname = new URL(route.request().url()).pathname;
    if (pathname === "/docs/web-api/") {
      await route.fulfill({contentType:"text/html",body:"<h1>Owned API documentation fixture</h1>"});
      return;
    }
    if (pathname === "/") {
      await route.fulfill({ contentType: "text/html", body: `<!doctype html>
        <html data-theme="${theme}"><head>
        <link rel="stylesheet" href="${ui}/css/shell/theme.css">
        <link rel="stylesheet" href="${ui}/css/primitives/spacing.css">
        <link rel="stylesheet" href="${ui}/css/app/app-header.css">
        <link rel="stylesheet" href="${ui}/css/app/project-selector.css">
        <link rel="stylesheet" href="/creator/static/scitex_sdk_creator/wizard.css">
        <style>html{font-size:${rootSize}px}body{margin:0;font-family:Georgia;line-height:1.95}.framework-project-wrapper{max-width:260px}</style>
        </head><body ${apiDocs ? 'data-stx-api-docs-url="/docs/web-api/?package=scitex-example"' : ""}><div class="stx-creator"><div id="mount"></div></div>
        <script type="module">
          import {AppHeader} from '${ui}/js/app/app-header.js';
          import {ProjectSelector} from '${ui}/js/app/project-selector.js';
          window.commits=[];
          const header=new AppHeader({container:'#mount',title:'Example App',version:'1.2.3'});
          let pickerContainer=header.projectSlot;
          if (${wrapped}) {
            const wrapper=document.createElement('div');wrapper.className='framework-project-wrapper';
            const inner=document.createElement('div');wrapper.append(inner);header.projectSlot.append(wrapper);
            pickerContainer=inner;
          }
          const provider={
            async listProjects(){return {projects:[{id:'example',name:'Example',detail:'Owner',disabled:${!projectAllowed},disabledReason:${JSON.stringify(projectAllowed ? "" : "Project unavailable")}}],current:'example',current_scope:'project',allow_user_scope:true,user_scope_disabled_reason:${JSON.stringify(userAllowed ? "" : "All Projects unavailable")}};},
            async rememberScope(scope){window.commits.push(scope);}
          };
          new ProjectSelector({container:pickerContainer,provider,allowUserScope:true});
          window.headerReady=true;
        </script></body></html>` });
      return;
    }
    const path = resolve(source, "." + pathname);
    if (!path.startsWith(source + sep)) throw new Error("Fixture path escaped SDK");
    await route.fulfill({
      contentType: path.endsWith(".css") ? "text/css" : "text/javascript",
      body: await readFile(path),
    });
  });
  await page.goto("http://sdk.test/");
  await page.waitForFunction(() => (window as Window & { headerReady?: boolean }).headerReady);
  await expect(page.locator(".stx-app-project-selector__trigger")).toBeEnabled();
  if (projectAllowed) {
    await expect(page.locator(".stx-app-project-selector__trigger")).toHaveText("Example");
  } else {
    await expect(page.locator(".stx-app-project-selector__trigger")).not.toHaveText("Example");
  }
}

for (const theme of ["light", "dark"]) {
  for (const rootSize of [14, 16]) {
    test(`framework wrappers fill phone slot: ${theme}, root ${rootSize}`, async ({ page }) => {
      await page.setViewportSize({ width: 390, height: 844 });
      await mount(page, rootSize, theme, true, true, true);
      const slot = await page.locator(".stx-app-header__slot--project-selector").boundingBox();
      const trigger = page.locator(".stx-app-project-selector__trigger");
      expect(Math.abs((await trigger.boundingBox())!.width - slot!.width)).toBeLessThan(1);
      await trigger.click();
      const panel = await page.locator(".stx-app-project-selector__panel").boundingBox();
      expect(Math.abs(panel!.width - slot!.width)).toBeLessThan(1);
      expect(panel!.x).toBeGreaterThanOrEqual(0);
      expect(panel!.x + panel!.width).toBeLessThanOrEqual(390);
    });
  }
  for (const rootSize of [14, 16]) {
    for (const width of [1440, 390]) {
      test(`identical header metrics: ${theme}, root ${rootSize}, width ${width}`, async ({ page }) => {
        await page.setViewportSize({ width, height: 900 });
        await mount(page, rootSize, theme);
        const metrics = await page.evaluate(() => {
          const get = (selector: string) => {
            const e = document.querySelector<HTMLElement>(selector)!;
            const s = getComputedStyle(e);
            return { font: s.fontFamily, size: s.fontSize, weight: s.fontWeight,
              line: s.lineHeight, radius: s.borderRadius, padding: s.padding,
              height: e.getBoundingClientRect().height };
          };
          return { header: get(".stx-app-header"), title: get(".stx-app-header__title"),
            version: get(".stx-app-header__version"), trigger: get(".stx-app-project-selector__trigger"),
            overflow: document.documentElement.scrollWidth > innerWidth };
        });
        expect(metrics.title.size).toBe("14px");
        expect(metrics.title.line).toBe("16.8px");
        expect(metrics.version.size).toBe("12px");
        expect(metrics.version.line).toBe("18px");
        expect(metrics.version.weight).toBe("600");
        expect(metrics.trigger.size).toBe("14px");
        expect(metrics.trigger.line).toBe("21px");
        expect(metrics.trigger.padding).toBe("0px 12px");
        expect(metrics.trigger.radius).toBe("4px");
        expect(metrics.trigger.height).toBe(width === 390 ? 44 : 36);
        expect(metrics.title.font).toBe(metrics.trigger.font);
        expect(metrics.title.font).not.toContain("Georgia");
        expect(metrics.header.padding).toBe("4px 12px");
        expect(metrics.overflow).toBe(false);
        await page.getByRole("button", { name: "Example", exact: true }).click();
        const option = page.getByRole("option", { name: "All Projects", exact: true });
        await expect(option).toHaveCSS("font-size", "14px");
        await expect(option).toHaveCSS("font-family", metrics.title.font);
        await expect(page.locator(".stx-app-project-selector__search")).toHaveCSS("margin", "4px");
        await expect(page.locator(".stx-app-project-selector__list")).toHaveCSS("padding", "4px");
        if (width === 390) expect((await option.boundingBox())!.height).toBeGreaterThanOrEqual(44);
      });
    }
  }
  for (const userAllowed of [false, true]) {
    for (const projectAllowed of [false, true]) {
      test(`scope choices ${theme}: user=${userAllowed}, project=${projectAllowed}`, async ({ page }) => {
        await mount(page, 16, theme, userAllowed, projectAllowed);
        await page.locator(".stx-app-project-selector__trigger").click();
        const all = page.getByRole("option", { name: "All Projects", exact: true });
        const project = page.getByRole("option", { name: "Example Owner", exact: true });
        await expect(all).toBeVisible();
        await expect(project).toBeVisible();
        if (userAllowed) await expect(all).toBeEnabled();
        else { await expect(all).toBeDisabled(); await expect(all).toHaveAttribute("title", "All Projects unavailable"); }
        if (projectAllowed) await expect(project).toBeEnabled();
        else { await expect(project).toBeDisabled(); await expect(project).toHaveAttribute("title", "Project unavailable"); }
        // DOM click() also respects native disabled semantics: no persisted choice.
        for (const option of [all, project]) {
          if (await option.isDisabled()) await option.evaluate((e: HTMLButtonElement) => e.click());
        }
        expect(await page.evaluate(() => (window as Window & { commits?: unknown[] }).commits)).toEqual([]);
      });
    }
  }
}

for (const width of [1440, 390]) {
  for (const keyboard of [false, true]) {
    test(`API docs native navigation width=${width}, keyboard=${keyboard}`, async ({page}) => {
      await page.setViewportSize({width,height:900});
      await mount(page,16,"light",true,true,false,true);
      const action=page.getByRole("link",{name:"API documentation",exact:true});
      await expect(action).toHaveAttribute("href","/docs/web-api/?package=scitex-example");
      await expect(page.locator(".stx-app-project-selector__trigger")).toHaveText("Example");
      if (keyboard) { await action.focus(); await page.keyboard.press("Enter"); }
      else await action.click();
      await expect(page).toHaveURL("http://sdk.test/docs/web-api/?package=scitex-example");
      await expect(page.getByRole("heading",{name:"Owned API documentation fixture"})).toBeVisible();
    });
  }
}
