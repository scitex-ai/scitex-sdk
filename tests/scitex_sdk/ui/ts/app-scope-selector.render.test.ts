/** app-scope-selector HOST behavior — deterministic component test.
 *
 * The directive's acceptance is behavioral, not textual: user-scoped / absent
 * marker must render NO project selector; project-scoped may opt into an
 * APP-LOCAL selector (reusing the existing ProjectSelector, not a fork); and it
 * must never restore a global Hub-header switcher. scitex-ui has no JS test
 * runner, so this is a self-contained Node strip-types script with the same
 * minimal DOM stub as project-selector.render.test.ts — it imports the
 * SELF-CONTAINED source chain (scope.ts -> app-scope-selector.ts ->
 * ProjectSelector -> BaseComponent, all relative .ts), so no bundler is needed.
 *
 * The light / dark / mobile matrix is asserted on the GATE, not the pixels:
 * scope is a document-level declaration, so the same marker must yield the same
 * mount/no-mount decision in every theme and at every viewport. The selector's
 * own light/dark/mobile rendering is ProjectSelector's (already covered by its
 * render test + the shared --role-* / --stx-* tokens).
 *
 *   node --experimental-strip-types tests/scitex_sdk/ui/ts/app-scope-selector.render.test.ts
 */

// @ts-nocheck — Node-executed DOM-stub script; stub types intentionally untyped,
// excluded from the library's tsc --noEmit.
import assert from "node:assert/strict";

// ── minimal DOM stub (mirrors project-selector.render.test.ts) ─────────────
function makeEventTarget() {
  const ls = {};
  return {
    _listeners: ls,
    addEventListener: (t, fn) => { (ls[t] = ls[t] || []).push(fn); },
    removeEventListener: (t, fn) => { ls[t] = (ls[t] || []).filter((f) => f !== fn); },
    dispatchEvent: (ev) => { (ls[ev.type] || []).slice().forEach((f) => f(ev)); return true; },
  };
}
function makeClassList() {
  const set = new Set();
  return { set, add: (...c) => c.forEach((x) => set.add(x)), remove: (...c) => c.forEach((x) => set.delete(x)), contains: (c) => set.has(c) };
}
function makeElement(tagName) {
  const el = makeEventTarget();
  el.tagName = tagName; el.children = []; el.className = ""; el.textContent = "";
  el.classList = makeClassList();
  el.setAttribute = (k, v) => { el[k] = v; };
  el.getAttribute = (k) => (k in el ? el[k] : null);
  el.appendChild = (c) => { el.children.push(c); c.parentNode = el; return c; };
  el.contains = (n) => { if (n === el) return true; for (const c of el.children) { if (c === n || (c.contains && c.contains(n))) return true; } return false; };
  el._innerHTML = "";
  Object.defineProperty(el, "innerHTML", { get: () => el._innerHTML, set: (v) => { el._innerHTML = v; if (v === "") el.children = []; } });
  return el;
}

// A document stub that can carry a scope meta AND build elements. The
// `metas` array is what scope.ts' querySelector reads; `theme`/`viewport` are
// carried so the matrix can prove they are IGNORED by the gate.
function makeDoc(metas, theme = null, viewport = "desktop") {
  const doc = makeEventTarget();
  doc._metas = metas;
  doc.documentElement = { getAttribute: (k) => (k === "data-theme" ? theme : null) };
  doc.querySelector = (sel) => {
    const m = /meta\[name="([^"]+)"\]/.exec(sel);
    if (!m) return null;
    return metas.find((x) => x.name === m[1]) || null;
  };
  doc.createElement = (t) => makeElement(t);
  doc.querySelectorAll = () => [];
  doc._viewport = viewport;
  return doc;
}
function meta(name, content) {
  return { name, content, getAttribute: (k) => (k === "content" ? content : null) };
}
globalThis.CustomEvent = class CustomEvent {
  constructor(type, opts) { this.type = type; this.detail = opts && opts.detail; this.bubbles = !!(opts && opts.bubbles); }
};

// The selector is imported AFTER the document stub is in place. Static import
// runs the module (no DOM work at import time), so ordering is safe.
// Both imports come from the SELF-CONTAINED bundle (BaseComponent + ProjectSelector
// + scope are inlined), so no module-resolution is needed — the same reason the
// project-selector render test imports its bundle rather than raw source.
import {
  mountProjectSelectorByScope,
  PROJECT_SELECTOR_CHANGE,
} from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/js/shell/app-scope-selector.js";

const PROJECTS = [
  { id: "alpha", name: "Alpha" },
  { id: "beta", name: "Beta" },
];

let passed = 0;
function ok(name, fn) { fn(); passed++; console.log("  ok - " + name); }

// Run the whole suite once per (theme x viewport) to assert the gate is
// theme/viewport-independent — that IS the light/dark/mobile matrix.
const MATRIX = [
  ["light", "desktop"], ["light", "mobile"],
  ["dark", "desktop"], ["dark", "mobile"],
  [null, "desktop"], [null, "mobile"],
];

console.log("app-scope-selector host behavior (TODO #48/#144-149 consumer):");

ok("project-scoped -> mounts a real ProjectSelector (trigger + panel appended)", () => {
  globalThis.document = makeDoc([meta("stx-app-scope", "project")]);
  const container = makeElement("div");
  const sel = mountProjectSelectorByScope({ container, projects: PROJECTS, current: "alpha" });
  assert.ok(sel, "returns the selector instance when project-scoped");
  const tags = container.children.map((c) => c.tagName.toLowerCase());
  assert.ok(tags.includes("button"), "trigger appended (got " + tags + ")");
  assert.ok(tags.includes("div"), "panel appended (got " + tags + ")");
});

ok("project-scoped -> the mounted selector emits PROJECT_SELECTOR_CHANGE", () => {
  globalThis.document = makeDoc([meta("stx-app-scope", "project")]);
  const container = makeElement("div");
  const sel = mountProjectSelectorByScope({ container, projects: PROJECTS, current: null });
  const panel = container.children.find((c) => c.tagName.toLowerCase() === "div");
  const list = panel.children.find((c) => c.role === "listbox");
  let fired = null;
  container.addEventListener(PROJECT_SELECTOR_CHANGE, (e) => { fired = e.detail; });
  list.children[1].dispatchEvent({ type: "click" });
  assert.equal(fired && fired.id, "beta");
});

ok("user-scoped marker -> renders NOTHING (container stays empty, returns null)", () => {
  globalThis.document = makeDoc([meta("stx-app-scope", "user")]);
  const container = makeElement("div");
  const sel = mountProjectSelectorByScope({ container, projects: PROJECTS, current: "alpha" });
  assert.equal(sel, null, "no selector instance for user-scoped");
  assert.equal(container.children.length, 0, "container left byte-for-byte empty");
});

ok("absent marker (the SDK's user-scoped spelling) -> renders NOTHING", () => {
  globalThis.document = makeDoc([]);
  const container = makeElement("div");
  const sel = mountProjectSelectorByScope({ container, projects: PROJECTS, current: "alpha" });
  assert.equal(sel, null);
  assert.equal(container.children.length, 0);
});

ok("an unrelated marker (stx-mount only) -> renders NOTHING", () => {
  globalThis.document = makeDoc([meta("stx-mount", "/apps/scholar/")]);
  const container = makeElement("div");
  const sel = mountProjectSelectorByScope({ container, projects: PROJECTS });
  assert.equal(sel, null);
  assert.equal(container.children.length, 0);
});

// THE MATRIX: the gate decision must be identical in every theme and viewport.
for (const [theme, viewport] of MATRIX) {
  const label = `${theme || "no-theme"} / ${viewport}`;
  ok(`[matrix ${label}] project marker -> selector mounted`, () => {
    globalThis.document = makeDoc([meta("stx-app-scope", "project")], theme, viewport);
    const container = makeElement("div");
    const sel = mountProjectSelectorByScope({ container, projects: PROJECTS, current: "alpha" });
    assert.ok(sel, "project-scoped mounts regardless of theme/viewport");
    assert.ok(container.children.some((c) => c.tagName.toLowerCase() === "button"));
  });
  ok(`[matrix ${label}] absent marker -> nothing rendered`, () => {
    globalThis.document = makeDoc([], theme, viewport);
    const container = makeElement("div");
    const sel = mountProjectSelectorByScope({ container, projects: PROJECTS });
    assert.equal(sel, null, "user/absent renders no selector in any theme/viewport");
    assert.equal(container.children.length, 0);
  });
}

ok("it REUSES ProjectSelector (no fork): the mounted trigger is a stx-app-project-selector trigger", () => {
  globalThis.document = makeDoc([meta("stx-app-scope", "project")]);
  const container = makeElement("div");
  mountProjectSelectorByScope({ container, projects: PROJECTS, current: "alpha" });
  const trigger = container.children.find((c) => c.tagName.toLowerCase() === "button");
  // ProjectSelector sets its own container className to CLS; the trigger is the
  // first child. Reuse is proven by the trigger carrying the ProjectSelector
  // block's element class, not a bespoke app-scope block.
  assert.equal(container.className, "stx-app-project-selector", "container is ProjectSelector's, not a fork");
  assert.ok(trigger, "trigger present (ProjectSelector rendered, not re-implemented)");
});

ok("the app's own scope mounts without a page marker", () => {
  globalThis.document = makeDoc([]);
  const container = makeElement("div");
  const sel = mountProjectSelectorByScope({ container, projects: PROJECTS, scope: "project" });
  assert.ok(sel);
});

ok("without projects or provider -> the host-advertised provider is fetched", async () => {
  const fetched = [];
  globalThis.fetch = async (url) => {
    fetched.push(url);
    return { ok: true, json: async () => ({ projects: PROJECTS, current: "beta" }) };
  };
  globalThis.document = makeDoc([meta("stx-project-provider", "/host/projects/")]);
  const container = makeElement("div");
  const sel = mountProjectSelectorByScope({ container, scope: "project" });
  await sel.ready;
  assert.deepEqual(fetched, ["/host/projects/"]);
  assert.equal(sel.getCurrent().id, "beta");
});

ok("navigate -> a pick goes to the project URL", () => {
  const visited = [];
  globalThis.window = { location: { assign: (u) => visited.push(u) } };
  globalThis.document = makeDoc([]);
  const container = makeElement("div");
  mountProjectSelectorByScope({
    container, projects: PROJECTS, current: "alpha", scope: "project", navigate: "?project={id}",
  });
  const panel = container.children.find((c) => c.tagName.toLowerCase() === "div");
  panel.children.find((c) => c.role === "listbox").children[1].dispatchEvent({ type: "click" });
  assert.deepEqual(visited, ["?project=beta"]);
});

console.log("\n" + passed + " assertion-groups passed");
