/** DOM regression test for the AppLauncher component (compass L624).
 *
 * scitex-ui has no JS test runner (CI gates are `tsc --noEmit` + `eslint`),
 * so this is a self-contained Node strip-types script with a minimal DOM
 * stub — it imports the SELF-CONTAINED compiled bundle (BaseComponent is
 * inlined), so no module-resolution or framework dependency. Plain JS body
 * (no TS-only syntax) so Node's strip-only transform accepts it:
 *
 *   node --experimental-strip-types tests/scitex_sdk/ui/ts/app-launcher.render.test.ts
 *
 * What it pins:
 *  1. after construction, the container holds the trigger AND the panel
 *  2. the trigger carries the grid glyph (田) + a text label
 *  3. the grid has one tile per app, in order
 *  4. clicking a tile emits APP_LAUNCHER_SELECT with {appId, appName}
 *  5. an empty app list renders the "No apps available" placeholder
 *  6. the current app's tile carries aria-current="true"
 *  7. opening the panel adds --open to the container and aria-expanded="true"
 */

// @ts-nocheck — Node-executed DOM-stub regression script; its stub types are
// intentionally untyped and it is excluded from the library's tsc --noEmit.
import assert from "node:assert/strict";

// ── minimal DOM stub (mirrors project-selector.render.test.ts) ─────────────
function makeEventTarget() {
  const ls = {};
  return {
    _listeners: ls,
    addEventListener: (t, fn) => { (ls[t] = ls[t] || []).push(fn); },
    removeEventListener: (t, fn) => { ls[t] = (ls[t] || []).filter((f) => f !== fn); },
    dispatchEvent: (ev) => {
      (ls[ev.type] || []).slice().forEach((f) => f(ev));
      return true;
    },
  };
}
function makeClassList() {
  const set = new Set();
  return {
    set,
    add: (...c) => c.forEach((x) => set.add(x)),
    remove: (...c) => c.forEach((x) => set.delete(x)),
    contains: (c) => set.has(c),
  };
}
function makeElement(tagName) {
  const el = makeEventTarget();
  el.tagName = tagName;
  el.children = [];
  el.className = "";
  el.textContent = "";
  el.classList = makeClassList();
  el.setAttribute = (k, v) => { el[k] = v; };
  el.getAttribute = (k) => (k in el ? el[k] : null);
  el.appendChild = (c) => { el.children.push(c); c.parentNode = el; return c; };
  el.contains = (n) => {
    if (n === el) return true;
    for (const c of el.children) {
      if (c === n) return true;
      if (c.contains && c.contains(n)) return true;
    }
    return false;
  };
  el._innerHTML = "";
  Object.defineProperty(el, "innerHTML", {
    get: () => el._innerHTML,
    set: (v) => { el._innerHTML = v; if (v === "") el.children = []; },
  });
  return el;
}
const documentStub = makeEventTarget();
documentStub.createElement = (t) => makeElement(t);
globalThis.document = documentStub;
globalThis.CustomEvent = class CustomEvent {
  constructor(type, opts) {
    this.type = type;
    this.detail = opts && opts.detail;
    this.bubbles = !!(opts && opts.bubbles);
  }
};

let passed = 0;
function ok(name, fn) {
  fn();
  passed++;
  console.log("  ok - " + name);
}

// Import the SELF-CONTAINED compiled bundle after the DOM stubs are in place.
import {
  AppLauncher,
  APP_LAUNCHER_SELECT,
} from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/js/app/app-launcher.js";

const APPS = [
  { id: "writer", name: "Writer" },
  { id: "scholar", name: "Scholar", icon: "\uD83D\uDCDA" },
  { id: "figrecipe", name: "FigRecipe", description: "figures" },
  { id: "console", name: "Console", icon: "\uD83D\uDCBB" },
];

console.log("AppLauncher DOM regression (compass L624):");

ok("container receives the trigger AND the panel", () => {
  const container = makeElement("div");
  new AppLauncher({ container, apps: APPS, current: "writer" });
  const tags = container.children.map((c) => c.tagName.toLowerCase());
  assert.ok(tags.includes("button"), "trigger appended (got " + tags + ")");
  assert.ok(tags.includes("div"), "panel appended (got " + tags + ")");
});

ok("trigger carries the grid glyph (田) and a text label", () => {
  const container = makeElement("div");
  new AppLauncher({ container, apps: APPS, current: null });
  const trigger = container.children.find((c) => c.tagName.toLowerCase() === "button");
  // trigger children: [glyph span, label span]
  assert.equal(trigger.children.length, 2, "trigger has glyph + label");
  assert.equal(trigger.children[0].textContent, "\u7530", "glyph is 田");
  assert.equal(trigger.children[1].textContent, "Apps", "default label is Apps");
});

ok("custom label is honoured", () => {
  const container = makeElement("div");
  new AppLauncher({ container, apps: APPS, label: "Home" });
  const trigger = container.children.find((c) => c.tagName.toLowerCase() === "button");
  assert.equal(trigger.children[1].textContent, "Home");
});

ok("the grid has one tile per app, in order", () => {
  const container = makeElement("div");
  new AppLauncher({ container, apps: APPS, current: null });
  const panel = container.children.find((c) => c.tagName.toLowerCase() === "div");
  const grid = panel.children[0];
  assert.equal(grid.children.length, APPS.length);
  for (let i = 0; i < APPS.length; i++) {
    const tile = grid.children[i];
    assert.ok(tile.tagName.toLowerCase() === "button", "tile is a real <button>");
    assert.equal(tile.getAttribute("aria-label"), APPS[i].name);
  }
});

ok("the current app's tile carries aria-current=true", () => {
  const container = makeElement("div");
  new AppLauncher({ container, apps: APPS, current: "scholar" });
  const panel = container.children.find((c) => c.tagName.toLowerCase() === "div");
  const grid = panel.children[0];
  const tiles = [...grid.children];
  const current = tiles.find((t) => t.getAttribute("aria-current") === "true");
  assert.ok(current, "one tile is marked current");
  assert.equal(current.getAttribute("aria-label"), "Scholar");
});

ok("clicking a tile emits APP_LAUNCHER_SELECT with {appId, appName}", () => {
  const container = makeElement("div");
  new AppLauncher({ container, apps: APPS, current: "writer" });
  const panel = container.children.find((c) => c.tagName.toLowerCase() === "div");
  const grid = panel.children[0];
  let fired = null;
  container.addEventListener(APP_LAUNCHER_SELECT, (e) => { fired = e.detail; });
  // tile[2] is figrecipe
  grid.children[2].dispatchEvent({ type: "click" });
  assert.equal(fired && fired.appId, "figrecipe");
  assert.equal(fired && fired.appName, "FigRecipe");
});

ok("selecting closes the panel", () => {
  const container = makeElement("div");
  const launcher = new AppLauncher({ container, apps: APPS, current: null });
  const panel = container.children.find((c) => c.tagName.toLowerCase() === "div");
  const grid = panel.children[0];
  launcher.toggle(); // open via public API so internal state is in sync
  assert.equal(container.classList.contains("stx-app-launcher--open"), true, "opened");
  grid.children[0].dispatchEvent({ type: "click" });
  assert.equal(
    container.classList.contains("stx-app-launcher--open"),
    false,
    "panel closed after select"
  );
});

ok("toggling open adds --open and aria-expanded=true", () => {
  const container = makeElement("div");
  const launcher = new AppLauncher({ container, apps: APPS, current: null });
  assert.equal(container.classList.contains("stx-app-launcher--open"), false);
  launcher.toggle();
  assert.equal(container.classList.contains("stx-app-launcher--open"), true);
  const trigger = container.children.find((c) => c.tagName.toLowerCase() === "button");
  assert.equal(trigger.getAttribute("aria-expanded"), "true");
  launcher.toggle();
  assert.equal(container.classList.contains("stx-app-launcher--open"), false);
  assert.equal(trigger.getAttribute("aria-expanded"), "false");
});

ok("empty app list renders the 'No apps available' placeholder", () => {
  const container = makeElement("div");
  new AppLauncher({ container, apps: [], current: null });
  const panel = container.children.find((c) => c.tagName.toLowerCase() === "div");
  const grid = panel.children[0];
  assert.equal(grid.children.length, 1);
  assert.equal(grid.children[0].textContent, "No apps available");
});

ok("tiles without a custom icon default to the grid glyph", () => {
  const container = makeElement("div");
  new AppLauncher({ container, apps: [{ id: "a", name: "A" }], current: null });
  const panel = container.children.find((c) => c.tagName.toLowerCase() === "div");
  const grid = panel.children[0];
  const tile = grid.children[0];
  const icon = tile.children[0];
  assert.equal(icon.textContent, "\u7530", "default icon is 田");
});

ok("custom icon replaces the default glyph on that tile only", () => {
  const container = makeElement("div");
  new AppLauncher({
    container,
    apps: [
      { id: "a", name: "A" },
      { id: "b", name: "B", icon: "\uD83D\uDCDA" },
    ],
    current: null,
  });
  const panel = container.children.find((c) => c.tagName.toLowerCase() === "div");
  const grid = panel.children[0];
  assert.equal(grid.children[0].children[0].textContent, "\u7530", "tile A keeps default");
  assert.equal(grid.children[1].children[0].textContent, "\uD83D\uDCDA", "tile B uses custom");
});

console.log("\n" + passed + " assertion-groups passed");
