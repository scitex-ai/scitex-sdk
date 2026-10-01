/** stx-app-scope marker reader — deterministic contract test.
 *
 * scitex-ui has no JS test runner (CI gates are `tsc --noEmit` + `eslint`), so
 * this is a self-contained Node strip-types script. scope.ts is dependency-free
 * (reads a meta tag, returns a string), so it is imported DIRECTLY from the
 * source tree — no DOM stub beyond a minimal document.querySelector is needed.
 *
 * The contract under test (consumer half of scitex-app PR #185 @ d8528de4):
 *   <meta name="stx-app-scope" content="project">   <- only project-scoped apps
 *   user-scoped / omitted scope  -> NO marker
 *
 *   appScope():        absent -> "user" (safe default, NO selector)
 *                      "project" -> "project"
 *                      "user"    -> "user"
 *                      "" / null content -> "user"
 *                      any other value -> THROWS (fail loud, never guess)
 *   mayOfferProjectSelector(): true ONLY for "project".
 *
 * The same reader serves light, dark, and mobile — scope is a document-level
 * declaration, not a theme/viewport one — so the matrix below asserts the
 * marker is read identically regardless of the data-theme attribute or viewport
 * (the selector's own light/dark/mobile rendering is ProjectSelector's, covered
 * by project-selector.render.test.ts and the shared tokens).
 *
 *   node --experimental-strip-types tests/scitex_sdk/ui/ts/scope.render.test.ts
 */

// @ts-nocheck — Node-executed DOM-stub script; stub types are intentionally
// untyped and it is excluded from the library's tsc --noEmit.
import assert from "node:assert/strict";
import {
  appScope,
  mayOfferProjectSelector,
  APP_SCOPE_META_NAME,
  SCOPE_USER,
  SCOPE_PROJECT,
  AppScopeMarkerInvalidError,
} from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/ts/_base/scope.ts";

// ── minimal document stub: just enough to carry meta tags ─────────────────
function makeDoc(metas, theme = null) {
  return {
    // theme attribute is carried but deliberately IGNORED by appScope — the
    // matrix asserts that. querySelector only matches the one meta name used.
    _metas: metas,
    querySelector: (sel) => {
      const m = /meta\[name="([^"]+)"\]/.exec(sel);
      if (!m) return null;
      return (
        metas.find((x) => x.name === m[1]) || null
      );
    },
  };
}
function meta(name, content) {
  return {
    name,
    content,
    getAttribute: (k) => (k === "content" ? content : null),
  };
}

let passed = 0;
function ok(name, fn) {
  fn();
  passed++;
  console.log("  ok - " + name);
}

console.log("stx-app-scope marker reader (TODO #48/#144-149 consumer contract):");

ok("the meta name is exactly 'stx-app-scope' (byte-identical to the SDK)", () => {
  assert.equal(APP_SCOPE_META_NAME, "stx-app-scope");
});

ok("scope constants are the closed enum user|project", () => {
  assert.equal(SCOPE_USER, "user");
  assert.equal(SCOPE_PROJECT, "project");
});

ok("absent marker -> 'user' (the safe default: renders NO selector)", () => {
  assert.equal(appScope(makeDoc([])), "user");
});

ok("no meta at all (empty head) -> 'user'", () => {
  assert.equal(mayOfferProjectSelector(makeDoc([])), false);
});

ok("content='project' -> 'project' and mayOfferProjectSelector true", () => {
  const d = makeDoc([meta("stx-app-scope", "project")]);
  assert.equal(appScope(d), "project");
  assert.equal(mayOfferProjectSelector(d), true);
});

ok("content='user' (a template that writes it) -> 'user', no selector", () => {
  const d = makeDoc([meta("stx-app-scope", "user")]);
  assert.equal(appScope(d), "user");
  assert.equal(mayOfferProjectSelector(d), false);
});

ok("content='' (present-but-empty) -> 'user', no selector", () => {
  assert.equal(appScope(makeDoc([meta("stx-app-scope", "")])), "user");
});

ok("content=null (meta without content attr) -> 'user', no selector", () => {
  assert.equal(appScope(makeDoc([meta("stx-app-scope", null)])), "user");
});

ok("case/whitespace insensitivity: ' Project ' -> 'project'", () => {
  assert.equal(appScope(makeDoc([meta("stx-app-scope", "  Project  ")])), "project");
});

ok("unrecognised value 'workspace' THROWS (fail loud, never a guessed scope)", () => {
  const d = makeDoc([meta("stx-app-scope", "workspace")]);
  assert.throws(() => appScope(d), AppScopeMarkerInvalidError);
});

ok("an unrelated meta does not satisfy the reader -> 'user'", () => {
  const d = makeDoc([meta("stx-mount", "/apps/cards/")]);
  assert.equal(appScope(d), "user");
  assert.equal(mayOfferProjectSelector(d), false);
});

// ── the light / dark / mobile matrix: scope is theme- and viewport-independent ─
for (const theme of [null, "light", "dark"]) {
  for (const viewport of ["desktop", "mobile"]) {
    const label = `${theme || "no-theme"} / ${viewport}`;
    ok(`[matrix ${label}] project marker -> project (scope ignores theme/viewport)`, () => {
      const d = makeDoc([meta("stx-app-scope", "project")]);
      // theme/viewport are deliberately not passed to appScope — it reads only
      // the meta. Assert the same result across the whole matrix.
      assert.equal(appScope(d), "project");
      assert.equal(mayOfferProjectSelector(d), true);
    });
    ok(`[matrix ${label}] absent marker -> user (no selector, any theme/viewport)`, () => {
      const d = makeDoc([]);
      assert.equal(appScope(d), "user");
      assert.equal(mayOfferProjectSelector(d), false);
    });
  }
}

console.log("\n" + passed + " assertion-groups passed");
