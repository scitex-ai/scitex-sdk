/** Regression test for the ProjectSelector render bug (fix branch
 * `figrecipe-fix-project-selector-render`).
 *
 * The merged component (scitex-ui PR #220 / fd9e9bb) built `this.trigger` and
 * `this.panel` but never appended them to `this.container`, so it rendered an
 * EMPTY `<div class="stx-app-project-selector">` — no dropdown, no options, no
 * current label. figrecipe's consumption of the shared primitive
 * (ProjectScopeSelector, TODO #145/#147) surfaced it live. This test pins the
 * fix: after construction the container must hold the trigger + panel, and a
 * selection must emit `PROJECT_SELECTOR_CHANGE`.
 *
 * scitex-ui has no JS test runner (CI gates are `tsc --noEmit` + `eslint`), so
 * this is a self-contained Node strip-types script with a minimal DOM stub —
 * it imports the SELF-CONTAINED compiled bundle (BaseComponent is inlined), so
 * no module-resolution or framework dependency. Plain JS body (no TS-only
 * syntax) so Node's strip-only transform accepts it:
 *
 *   node --experimental-strip-types tests/scitex_sdk/ui/ts/project-selector.render.test.ts
 */

// @ts-nocheck — Node-executed DOM-stub regression script; its stub types are
// intentionally untyped and it is excluded from the library's tsc --noEmit.
import assert from "node:assert/strict";

// ── minimal DOM stub (just enough for ProjectSelector's constructor) ──────
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
// gettext looks for json_script catalogs; the stub page has none.
documentStub.querySelectorAll = () => [];
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
// (Static import is fine — the bundle itself has no DOM work at import time.)
import {
  ProjectSelector,
  PROJECT_SELECTOR_CHANGE,
} from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/js/app/project-selector.js";

console.log("ProjectSelector render regression (fix branch):");

ok("the fix: container receives the trigger AND the panel", () => {
  const container = makeElement("div");
  new ProjectSelector({
    container,
    projects: [
      { id: "alpha", name: "alpha" },
      { id: "beta", name: "beta" },
    ],
    current: "alpha",
  });
  const tags = container.children.map((c) => c.tagName.toLowerCase());
  assert.ok(tags.includes("button"), "trigger appended (got " + tags + ")");
  assert.ok(tags.includes("div"), "panel appended (got " + tags + ")");
});

ok("the trigger shows the current selection's name", () => {
  const container = makeElement("div");
  new ProjectSelector({
    container,
    projects: [
      { id: "alpha", name: "alpha" },
      { id: "beta", name: "beta" },
    ],
    current: "alpha",
  });
  const trigger = container.children.find((c) => c.tagName.toLowerCase() === "button");
  assert.equal(trigger.children[0].textContent, "alpha");
});

ok("the panel lists one option per project", () => {
  const container = makeElement("div");
  new ProjectSelector({
    container,
    projects: [
      { id: "alpha", name: "alpha" },
      { id: "beta", name: "beta" },
      { id: "gamma", name: "gamma" },
    ],
    current: null,
  });
  const panel = container.children.find((c) => c.tagName.toLowerCase() === "div");
  const list = panel.children.find((c) => c.className.endsWith("__list"));
  assert.equal(list.children.length, 3);
});

ok("selecting a project emits PROJECT_SELECTOR_CHANGE with its id", () => {
  const container = makeElement("div");
  new ProjectSelector({
    container,
    projects: [
      { id: "alpha", name: "alpha" },
      { id: "beta", name: "beta" },
    ],
    current: "alpha",
  });
  const panel = container.children.find((c) => c.tagName.toLowerCase() === "div");
  const list = panel.children.find((c) => c.className.endsWith("__list"));
  let fired = null;
  container.addEventListener(PROJECT_SELECTOR_CHANGE, (e) => { fired = e.detail; });
  // simulate clicking the second option (its click handler calls select)
  list.children[1].dispatchEvent({ type: "click" });
  assert.equal(fired && fired.id, "beta");
  const trigger = container.children.find((c) => c.tagName.toLowerCase() === "button");
  assert.equal(trigger.children[0].textContent, "beta");
});

ok("empty project list renders the 'No projects' placeholder", () => {
  const container = makeElement("div");
  new ProjectSelector({ container, projects: [], current: null });
  const panel = container.children.find((c) => c.tagName.toLowerCase() === "div");
  const list = panel.children.find((c) => c.className.endsWith("__list"));
  assert.equal(list.children[0].textContent, "No projects");
});

console.log("\n" + passed + " assertion-groups passed");
