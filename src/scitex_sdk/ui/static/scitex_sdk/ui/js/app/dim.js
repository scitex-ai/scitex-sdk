/* AUTO-GENERATED from ts/app/dim/index.ts via esbuild — do not edit by hand. Rebuild: npx esbuild ts/app/dim/index.ts --bundle --format=esm --outfile=js/app/dim.js */

// ts/_base/aria-describedby.ts
var ATTR = "aria-describedby";
function ids(el) {
  const raw = el.getAttribute(ATTR);
  return raw ? raw.split(/\s+/).filter(Boolean) : [];
}
function write(el, list) {
  if (list.length === 0) {
    el.removeAttribute(ATTR);
    return;
  }
  el.setAttribute(ATTR, list.join(" "));
}
function addDescribedBy(el, id, position = "last") {
  const list = ids(el);
  if (list.includes(id)) return;
  write(el, position === "first" ? [id, ...list] : [...list, id]);
}
function removeDescribedBy(el, id) {
  const list = ids(el);
  if (!list.includes(id)) return;
  write(
    el,
    list.filter((each) => each !== id)
  );
}

// ts/app/dim/types.ts
var ALLOWED = "allowed";
var DENIED = "denied";
var DENIED_NOT_SIGNED_IN = "denied-because-not-signed-in";
var DENIED_NOT_ENTITLED = "denied-because-not-entitled";

// ts/app/dim/_Dim.ts
var CLS = "stx-app-dim";
var CLS_ACTIONABLE = `${CLS}--actionable`;
var CLS_REASON = `${CLS}__reason`;
var ATTR_SIGN_IN_URL = "data-stx-dim-sign-in-url";
var DEFAULT_LABELS = {
  denied: "Not available.",
  deniedNotSignedIn: "Sign in to use this.",
  deniedNotEntitled: "Requires {entitlement}."
};
var seq = 0;
var reasonNodes = /* @__PURE__ */ new WeakMap();
function reasonTextFor(verdict, labels) {
  switch (verdict.kind) {
    case ALLOWED:
      return null;
    case DENIED:
      return labels.denied;
    case DENIED_NOT_SIGNED_IN:
      return labels.deniedNotSignedIn;
    case DENIED_NOT_ENTITLED:
      return labels.deniedNotEntitled.replace(
        "{entitlement}",
        verdict.entitlement
      );
    default:
      return assertNever(verdict);
  }
}
function assertNever(value) {
  throw new Error(`Dim: unhandled verdict kind: ${JSON.stringify(value)}`);
}
function routeFor(verdict) {
  return verdict.kind === DENIED_NOT_SIGNED_IN ? verdict.sign_in_url : null;
}
function clear(el) {
  el.classList.remove(CLS, CLS_ACTIONABLE);
  el.removeAttribute("aria-disabled");
  el.removeAttribute(ATTR_SIGN_IN_URL);
  el.removeAttribute("data-tooltip");
  const node = reasonNodes.get(el);
  if (node) {
    removeDescribedBy(el, node.id);
    node.remove();
    reasonNodes.delete(el);
  }
}
function reasonNodeFor(el) {
  const existing = reasonNodes.get(el);
  if (existing) return existing;
  const node = document.createElement("span");
  node.className = CLS_REASON;
  node.id = `${CLS}-reason-${++seq}`;
  (el.parentElement ?? document.body).appendChild(node);
  reasonNodes.set(el, node);
  return node;
}
function applyVerdict(el, verdict, config = {}) {
  const labels = { ...DEFAULT_LABELS, ...config.labels };
  const reason = reasonTextFor(verdict, labels);
  if (reason === null) {
    clear(el);
    return;
  }
  el.classList.add(CLS);
  el.setAttribute("aria-disabled", "true");
  el.setAttribute("data-tooltip", reason);
  const node = reasonNodeFor(el);
  node.textContent = reason;
  addDescribedBy(el, node.id, "first");
  const route = routeFor(verdict);
  if (route === null) {
    el.classList.remove(CLS_ACTIONABLE);
    el.removeAttribute(ATTR_SIGN_IN_URL);
  } else {
    el.classList.add(CLS_ACTIONABLE);
    el.setAttribute(ATTR_SIGN_IN_URL, route);
  }
}
export {
  ALLOWED,
  DENIED,
  DENIED_NOT_ENTITLED,
  DENIED_NOT_SIGNED_IN,
  applyVerdict
};
