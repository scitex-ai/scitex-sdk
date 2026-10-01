// src/scitex_ui/static/scitex_ui/ts/_base/gettext.ts
var JS_CATALOG_ELEMENT_PREFIX = "scitex-i18n-catalog-";
var state = null;
function installCatalog(payload) {
  const current = state ?? { entries: {}, plural: null };
  state = {
    entries: { ...current.entries, ...payload.catalog },
    plural: payload.plural ?? current.plural
  };
}
function loadCatalogsFromDocument(doc) {
  const elements = doc.querySelectorAll(
    `script[type="application/json"][id^="${JS_CATALOG_ELEMENT_PREFIX}"]`
  );
  for (const element of Array.from(elements)) {
    installCatalog(JSON.parse(element.textContent || "{}"));
  }
}
function activeCatalog() {
  if (state === null) {
    state = { entries: {}, plural: null };
    if (typeof document !== "undefined") loadCatalogsFromDocument(document);
  }
  return state;
}
function gettext(msgid) {
  const entry = activeCatalog().entries[msgid];
  if (entry === void 0) return msgid;
  const translated = typeof entry === "string" ? entry : entry[0];
  return translated || msgid;
}

// src/scitex_ui/static/scitex_ui/ts/app/panes/_Panes.ts
var PANES_ATTRIBUTE = "data-stx-panes";
var PANE_ATTRIBUTE = "data-stx-pane";
var ACTIVE_ATTRIBUTE = "data-stx-pane-active";
var SINGLE_CLASS = "stx-panes--single";
var PANES_CHANGE = "stx-panes:change";
var PHONE_QUERY = "(max-width: 640px)";
var STORAGE_PREFIX = "stx-panes:";
var CLS = "stx-panes";
var SWIPE_MIN_PX = 60;
var SWIPE_AXIS_RATIO = 1.5;
var NO_SWIPE_SELECTOR = "input, textarea, select, [contenteditable=''], [contenteditable='true'], [data-stx-no-swipe], canvas, svg, table, iframe, embed, object, [role='img'], [role='application'], [data-stx-interactive], .stx-pdf-viewer, .stx-canvas, .stx-graph, .stx-editor";
function defaultMedia() {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") return null;
  return window.matchMedia(PHONE_QUERY);
}
function defaultStorage() {
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}
function slug(value) {
  return value.replace(/[^A-Za-z0-9_-]+/g, "-");
}
function startsInsideOwnGesture(target, root) {
  for (let el = target; el && el !== root; el = el.parentElement) {
    if (el.matches(NO_SWIPE_SELECTOR)) return true;
    if (el.scrollWidth > el.clientWidth + 1) {
      const overflow = getComputedStyle(el).overflowX;
      if (overflow === "auto" || overflow === "scroll") return true;
    }
  }
  return false;
}
var Panes = class {
  root;
  app;
  panes;
  tablist;
  tabs = /* @__PURE__ */ new Map();
  storage;
  activeId;
  touchStart = null;
  constructor(root, options = {}) {
    this.root = root;
    this.app = options.app || root.getAttribute(PANES_ATTRIBUTE) || (typeof location !== "undefined" ? location.pathname : "default");
    this.storage = options.storage === void 0 ? defaultStorage() : options.storage;
    this.panes = this.collectPanes();
    root.classList.add(CLS);
    this.tablist = this.renderTabs();
    root.insertBefore(this.tablist, root.firstChild);
    this.activeId = this.initialPane();
    this.apply(this.activeId);
    const media = options.media === void 0 ? defaultMedia() : options.media;
    this.setSingle(Boolean(media?.matches));
    media?.addEventListener("change", (event) => this.setSingle(event.matches));
    if (options.swipeToSwitch) {
      root.addEventListener("touchstart", (event) => this.onTouchStart(event), { passive: true });
      root.addEventListener("touchend", (event) => this.onTouchEnd(event), { passive: true });
    }
  }
  get active() {
    return this.activeId;
  }
  get single() {
    return this.root.classList.contains(SINGLE_CLASS);
  }
  /** Make `id` the active pane. Returns false for an unknown id. */
  show(id) {
    if (!this.panes.some((pane) => pane.id === id)) return false;
    const previous = this.activeId;
    this.apply(id);
    try {
      this.storage?.setItem(STORAGE_PREFIX + this.app, id);
    } catch {
    }
    if (previous !== id) {
      const detail = { app: this.app, pane: id, previous };
      this.root.dispatchEvent(new CustomEvent(PANES_CHANGE, { detail, bubbles: true }));
    }
    return true;
  }
  /** Move by `step` panes in tab order, clamped at the ends. */
  step(step) {
    const index = this.panes.findIndex((pane) => pane.id === this.activeId);
    const next = this.panes[index + step];
    return next ? this.show(next.id) : false;
  }
  collectPanes() {
    const elements = Array.from(this.root.children).filter(
      (child) => child instanceof HTMLElement && child.hasAttribute(PANE_ATTRIBUTE)
    );
    return elements.map((element, index) => {
      const id = element.getAttribute(PANE_ATTRIBUTE) || String(index);
      const declared = element.getAttribute("data-stx-order");
      const order = declared === null || declared === "" ? NaN : Number(declared);
      if (Number.isFinite(order)) element.style.order = String(order);
      return {
        id,
        label: element.getAttribute("data-stx-label") || id,
        icon: element.getAttribute("data-stx-icon") || "",
        order: Number.isFinite(order) ? order : index,
        element,
        index
      };
    }).sort((a, b) => a.order - b.order || a.index - b.index).map(({ id, label, icon, order, element }) => ({ id, label, icon, order, element }));
  }
  renderTabs() {
    const tablist = document.createElement("div");
    tablist.className = `${CLS}__tabs`;
    tablist.setAttribute("role", "tablist");
    tablist.setAttribute("aria-label", gettext("Sections"));
    for (const pane of this.panes) {
      const paneDomId = pane.element.id || `${CLS}-${slug(this.app)}-${slug(pane.id)}`;
      pane.element.id = paneDomId;
      pane.element.classList.add(`${CLS}__pane`);
      const tab = document.createElement("button");
      tab.type = "button";
      tab.className = `${CLS}__tab`;
      tab.id = `${paneDomId}-tab`;
      tab.setAttribute("role", "tab");
      tab.setAttribute("aria-controls", paneDomId);
      tab.dataset.stxPaneTab = pane.id;
      if (pane.icon) {
        const icon = document.createElement("span");
        icon.className = `${CLS}__tab-icon`;
        icon.setAttribute("aria-hidden", "true");
        icon.textContent = pane.icon;
        tab.appendChild(icon);
      }
      const label = document.createElement("span");
      label.className = `${CLS}__tab-label`;
      label.textContent = pane.label;
      tab.appendChild(label);
      tab.addEventListener("click", () => this.show(pane.id));
      pane.element.setAttribute("aria-labelledby", tab.id);
      this.tabs.set(pane.id, tab);
      tablist.appendChild(tab);
    }
    tablist.addEventListener("keydown", (event) => {
      const delta = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
      if (!delta || !this.step(delta)) return;
      event.preventDefault();
      this.tabs.get(this.activeId)?.focus();
    });
    return tablist;
  }
  initialPane() {
    const known = (id) => Boolean(id) && this.panes.some((pane) => pane.id === id);
    let stored = null;
    try {
      stored = this.storage?.getItem(STORAGE_PREFIX + this.app) ?? null;
    } catch {
      stored = null;
    }
    if (known(stored)) return stored;
    const declared = this.root.getAttribute("data-stx-active");
    if (known(declared)) return declared;
    return this.panes[0]?.id ?? "";
  }
  apply(id) {
    this.activeId = id;
    for (const pane of this.panes) {
      const isActive = pane.id === id;
      pane.element.toggleAttribute(ACTIVE_ATTRIBUTE, isActive);
      const tab2 = this.tabs.get(pane.id);
      tab2?.setAttribute("aria-selected", String(isActive));
      tab2?.setAttribute("tabindex", isActive ? "0" : "-1");
    }
    const tab = this.tabs.get(id);
    if (this.single && tab && typeof tab.scrollIntoView === "function") {
      tab.scrollIntoView({ block: "nearest", inline: "nearest" });
    }
  }
  setSingle(single) {
    this.root.classList.toggle(SINGLE_CLASS, single);
    for (const pane of this.panes) {
      if (single) pane.element.setAttribute("role", "tabpanel");
      else pane.element.removeAttribute("role");
    }
  }
  onTouchStart(event) {
    this.touchStart = null;
    if (!this.single || event.touches.length !== 1) return;
    if (startsInsideOwnGesture(event.target, this.root)) return;
    this.touchStart = { x: event.touches[0].clientX, y: event.touches[0].clientY };
  }
  onTouchEnd(event) {
    const start = this.touchStart;
    this.touchStart = null;
    const touch = event.changedTouches[0];
    if (!start || !touch) return;
    const dx = touch.clientX - start.x;
    const dy = touch.clientY - start.y;
    if (Math.abs(dx) < SWIPE_MIN_PX || Math.abs(dx) < Math.abs(dy) * SWIPE_AXIS_RATIO) return;
    this.step(dx < 0 ? 1 : -1);
  }
};

// src/scitex_ui/static/scitex_ui/ts/app/panes/mount.ts
var MOUNTED_ATTRIBUTE = "data-stx-panes-mounted";
var instances = [];
function mountPanes(root = document, options = {}) {
  const mounted = [];
  for (const element of Array.from(root.querySelectorAll(`[${PANES_ATTRIBUTE}]`))) {
    if (element.hasAttribute(MOUNTED_ATTRIBUTE)) continue;
    element.setAttribute(MOUNTED_ATTRIBUTE, "");
    const panes = new Panes(element, options);
    instances.push(panes);
    mounted.push(panes);
  }
  return mounted;
}
function getPanes(app, pane) {
  if (app) return instances.find((item) => item.app === app) ?? null;
  if (pane) {
    const holder = instances.find((item) => item.panes.some((info) => info.id === pane));
    if (holder) return holder;
  }
  return instances.length === 1 ? instances[0] : null;
}
function showPane(pane, app) {
  return getPanes(app, pane)?.show(pane) ?? false;
}
var stxPanes = { mount: mountPanes, get: getPanes, show: showPane };

// src/scitex_ui/static/scitex_ui/ts/app/panes/auto-mount.ts
window.stxPanes = stxPanes;
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => mountPanes());
} else {
  mountPanes();
}
export {
  ACTIVE_ATTRIBUTE,
  PANES_ATTRIBUTE,
  PANES_CHANGE,
  PANE_ATTRIBUTE,
  PHONE_QUERY,
  Panes,
  SINGLE_CLASS,
  STORAGE_PREFIX,
  getPanes,
  mountPanes,
  showPane,
  startsInsideOwnGesture,
  stxPanes
};
