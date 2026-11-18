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

/** The host owns its header height; nested app sidebars own their collapse. */
async function shellFixture(page: import('@playwright/test').Page, {
  width = 390, height = 844, header = 45, unused = true, newLayout = false, runtime = false,
} = {}) {
  await page.setViewportSize({ width, height });
  const root = resolve('src/scitex_sdk/ui/static/scitex_sdk/ui/css/shell');
  const styles = await Promise.all([
    'theme.css', 'app-shell.css', 'stx-shell-sidebar.css', 'workspace-three-col.css',
    'workspace.css', 'standalone-resizer-pos.css', 'mobile.css',
  ].map(file => readFile(resolve(root, file), 'utf8')));
  const utility = (kind: string) => `<section class="ws-${kind}-pane${unused ? ' ws-pane-unused' : ''}">
    <aside class="stx-shell-sidebar collapsed" id="utility-${kind}"><header class="stx-shell-sidebar__header" id="${kind}-header"><button class="panel-toggle-btn" onclick="this.closest('aside').classList.toggle('collapsed')">Toggle</button></header><div class="stx-shell-sidebar__content">
      <div class="utility-spacer"></div><button id="${kind}-action">${kind}</button>
    </div></aside></section>`;
  const module = `<main class="ws-module-pane" id="main-content"><section id="app-root">
    <header id="app-toolbar"><button id="toggle-details" aria-expanded="false">Details</button></header>
    <div id="app-scroll"><div class="app-spacer"></div><button id="last-action">Last item</button></div>
    <aside id="nested-details" class="stx-shell-sidebar collapsed" data-closed="true">
      <header id="nested-header" class="stx-shell-sidebar__header"><button class="panel-toggle-btn" id="nested-toggle" data-clicks="0" onclick="this.dataset.clicks = String(Number(this.dataset.clicks)+1)">Nested</button></header>
      <div class="stx-shell-sidebar__content">Nested app details</div>
    </aside></section></main>`;
  const shell = newLayout
    ? `<div class="workspace-layout"><div class="workspace-content"><section class="workspace-pane active" data-pane="module">${module}</section></div></div>`
    : `<div id="workspace-three-col" class="workspace-three-col">${utility('ai')}${utility('worktree')}${utility('viewer')}${module}</div>`;
  const html = `<html><head><style>${styles.join('\n')}</style><style>
    .global-header {height:${header}px; flex:none} #app-root {height:100%; min-height:0; display:flex; flex-direction:column}
    #app-toolbar {flex:none} #app-scroll {flex:1; min-height:0; overflow:auto} .app-spacer {height:1400px}
    #nested-details {width:260px; min-width:0; max-width:260px; height:auto; flex:none}
    #nested-details.collapsed {display:none; width:0; min-width:0; max-width:0}
    .utility-spacer {height:600px} .workspace-pane > .ws-module-pane {height:100%}
  </style></head><body class="workspace-page"><header class="global-header"></header>${shell}
  <script>document.querySelector('#toggle-details').onclick = () => {
    const details = document.querySelector('#nested-details'); const closed = details.classList.toggle('collapsed');
    document.querySelector('#toggle-details').setAttribute('aria-expanded', String(!closed));
  };</script></body></html>`;
  await page.route('https://sdk-frame.invalid/**', route => route.request().url() === 'https://sdk-frame.invalid/frame'
    ? route.fulfill({contentType:'text/html',body:html}) : route.abort());
  await page.goto('https://sdk-frame.invalid/frame');
  if (runtime) await page.addScriptTag({path:resolve('src/scitex_sdk/ui/static/scitex_sdk/ui/js/shell/mobile-swipe.js')});
}

for (const [height, header] of [[844, 45], [640, 83], [844, 0]]) {
  test(`declared content-only shell fills real remaining phone height ${height}/${header}`, async ({page}) => {
    await shellFixture(page, {height, header});
    const geometry = await page.evaluate(() => {
      const box = (selector: string) => document.querySelector(selector)!.getBoundingClientRect();
      return {frame:box('.workspace-three-col').toJSON(), module:box('#main-content').toJSON(), app:box('#app-root').toJSON(),
        utilities:[...document.querySelectorAll('.ws-pane-unused')].map(x => getComputedStyle(x).display)};
    });
    expect(geometry.frame.top).toBe(header);
    expect(geometry.frame.bottom).toBe(height);
    expect(geometry.module.height).toBe(height-header);
    expect(geometry.app.height).toBe(height-header);
    expect(geometry.utilities).toEqual(['none','none','none']);
    await page.locator('#app-scroll').hover();
    await page.mouse.wheel(0,1800);
    await expect.poll(() => page.locator('#app-scroll').evaluate(x => x.scrollTop)).toBeGreaterThan(0);
    await expect(page.locator('#last-action')).toBeInViewport();
  });
}

for (const width of [390, 1440]) {
  test(`nested sidebar collapse stays app-owned at ${width}`, async ({page}) => {
    await shellFixture(page, {width});
    await expect(page.locator('#nested-details')).toBeHidden();
    await page.locator('#toggle-details').click();
    await expect(page.locator('#nested-details')).toBeVisible();
    expect((await page.locator('#nested-details').boundingBox())!.width).toBe(260);
    await page.locator('#toggle-details').click();
    await expect(page.locator('#nested-details')).toBeHidden();
  });
}

test('new shell module does not force nested app sidebar open', async ({page}) => {
  await shellFixture(page,{newLayout:true});
  await expect(page.locator('#nested-details')).toBeHidden();
  await page.locator('#toggle-details').click();
  const box = (await page.locator('#nested-details').boundingBox())!;
  expect(box.width).toBe(260);
  expect(box.height).toBeLessThan(100);
});

test('used utility panes remain user-scroll reachable on phone', async ({page}) => {
  await shellFixture(page,{unused:false,runtime:true});
  for (const pane of ['ai','worktree','viewer']) {
    await expect(page.locator(`#utility-${pane}`)).toBeVisible();
    expect((await page.locator(`#utility-${pane}`).boundingBox())!.width).toBeGreaterThan(300);
  }
  await page.locator('.global-header').hover();
  await page.mouse.wheel(0,1800);
  await expect.poll(() => page.evaluate(() => Math.max(window.scrollY,document.body.scrollTop))).toBeGreaterThan(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
});


test('mobile runtime expands only shell utilities and preserves nested state', async ({page}) => {
  await shellFixture(page,{unused:false,runtime:true});
  await expect(page.locator('#utility-ai')).not.toHaveClass(/collapsed/);
  await expect(page.locator('#nested-details')).toHaveClass(/collapsed/);
  await expect(page.locator('#toggle-details')).toHaveAttribute('aria-expanded','false');
  await page.locator('#ai-header').dispatchEvent('dblclick');
  await expect(page.locator('#utility-ai')).toHaveClass(/collapsed/);
});

test('mobile breakpoint and nested header gestures retain app ownership', async ({page}) => {
  await shellFixture(page,{width:1440,runtime:true});
  await page.setViewportSize({width:390,height:844});
  await expect(page.locator('#nested-details')).toHaveClass(/collapsed/);
  await page.locator('#toggle-details').click();
  await page.locator('#nested-header').dispatchEvent('dblclick');
  await page.locator('#nested-header').dispatchEvent('mousedown',{clientY:200});
  await page.mouse.move(100,300);
  await page.mouse.up();
  await expect(page.locator('#nested-toggle')).toHaveAttribute('data-clicks','0');
  expect(await page.evaluate(() => document.body.style.cursor)).toBe('');
  await page.setViewportSize({width:1440,height:900});
  await expect(page.locator('#nested-details')).not.toHaveClass(/collapsed/);
});


test('saved utility preferences cannot overwrite an app sidebar state', async ({page}) => {
  await shellFixture(page);
  await page.locator('#toggle-details').click();
  await page.evaluate(() => localStorage.setItem('scitex-mobile-collapsed-panes',JSON.stringify(['nested-details'])));
  await page.addScriptTag({path:resolve('src/scitex_sdk/ui/static/scitex_sdk/ui/js/shell/mobile-swipe.js')});
  await expect(page.locator('#nested-details')).not.toHaveClass(/collapsed/);
  await expect(page.locator('#toggle-details')).toHaveAttribute('aria-expanded','true');
});


for (const wrapped of [false,true]) {
  test(`host utility ${wrapped ? 'editor wrapper' : 'direct pane'} retains full width`, async ({page}) => {
    await shellFixture(page,{newLayout:true});
    await page.locator('.workspace-content').evaluate((element,wrapped) => {
      const utility = '<aside id="host-utility" class="stx-shell-sidebar collapsed"><div class="stx-shell-sidebar__content">Files</div></aside>';
      element.innerHTML = '<section class="workspace-pane active" data-pane="editor">' +
        (wrapped ? '<div class="editor-split-layout" style="display:flex"><div class="editor-split-left"><div class="ws-worktree-pane" style="height:100%">' + utility + '</div></div></div>' : utility) + '</section>';
    },wrapped);
    await expect(page.locator('#host-utility')).toBeVisible();
    expect((await page.locator('#host-utility').boundingBox())!.width).toBe(390);
  });
}
