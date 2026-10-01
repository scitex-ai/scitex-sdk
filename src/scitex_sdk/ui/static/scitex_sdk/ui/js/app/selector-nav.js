// ts/_base/BaseComponent.ts
var BaseComponent = class {
  container;
  config;
  constructor(config) {
    this.config = config;
    const el = typeof config.container === "string" ? document.querySelector(config.container) : config.container;
    if (!el) {
      throw new Error(
        `${this.constructor.name}: container not found: ${config.container}`
      );
    }
    this.container = el;
  }
  /** Emit a custom event on the container. */
  emit(name, detail) {
    this.container.dispatchEvent(
      new CustomEvent(name, { detail, bubbles: true })
    );
  }
  /** Destroy the component and clean up DOM. */
  destroy() {
    this.container.innerHTML = "";
  }
};

// ts/app/selector-nav/types.ts
var SELECTOR_NAV_CHANGE = "stx-app-selector-nav:change";
var SELECTOR_NAV_ATTRIBUTE = "data-stx-selector-nav";

// ts/app/selector-nav/_SelectorNav.ts
var CLS = "stx-app-selector-nav";
var DEFAULT_BREAKPOINT = 600;
var SelectorNav = class extends BaseComponent {
  /** The strip (desktop) or the cascade levels (mobile) hang off this. */
  rootEl;
  /** The list container the items render into. */
  itemsEl;
  /** Optional footer section (the existing vocabulary already styles one). */
  footerEl;
  items;
  currentId;
  mode;
  breakpoint;
  media;
  onMediaChange = () => this.render();
  constructor(config) {
    super(config);
    this.items = config.items ?? [];
    this.currentId = config.current ?? null;
    this.mode = config.mode ?? "auto";
    this.breakpoint = config.breakpoint ?? DEFAULT_BREAKPOINT;
    this.rootEl = document.createElement("nav");
    this.rootEl.className = CLS;
    this.rootEl.setAttribute(
      "aria-label",
      this.container.getAttribute("aria-label") ?? "Sections"
    );
    this.itemsEl = document.createElement("div");
    this.itemsEl.className = `${CLS}__items`;
    this.footerEl = document.createElement("div");
    this.footerEl.className = `${CLS}__footer`;
    this.rootEl.append(this.itemsEl, this.footerEl);
    this.container.appendChild(this.rootEl);
    this.media = typeof window !== "undefined" && typeof window.matchMedia === "function" ? window.matchMedia(`(max-width: ${this.breakpoint}px)`) : null;
    this.media?.addEventListener("change", this.onMediaChange);
    this.render();
  }
  /** Set the whole tree (a leaf replacing its data source). */
  setItems(items) {
    this.items = items;
    this.render();
  }
  /** The current node and its ancestry, or null when nothing is selected. */
  getCurrent() {
    if (this.currentId === null) return null;
    return this.resolve(this.currentId);
  }
  /** The selected id, at any depth. */
  getCurrentId() {
    return this.currentId;
  }
  /**
   * Select by id. Selecting a node with children is not a terminal choice on
   * mobile (it opens the level); on desktop it is reported like any other, and
   * the app decides what to render — the primitive does not guess.
   */
  setCurrent(id) {
    if (id !== null && this.resolve(id) === null) {
      throw new Error(
        `SelectorNav: cannot select ${JSON.stringify(id)} \u2014 no node with that id is in the tree. Silently ignoring it would leave the strip on a selection the app did not ask for.`
      );
    }
    this.currentId = id;
    this.render();
  }
  /** Resolve an id to its node + ancestry (nearest-first), or null. */
  resolve(id) {
    const walk = (nodes, path) => {
      for (const node of nodes) {
        const nextPath = [node, ...path];
        if (node.id === id) {
          return { item: node, path: nextPath, root: nextPath[nextPath.length - 1] };
        }
        const found = walk(node.children ?? [], nextPath);
        if (found) return found;
      }
      return null;
    };
    return walk(this.items, []);
  }
  /** True when the strip/cascade renders tabs; false for the cascade shape. */
  isTabs() {
    if (this.mode === "tabs") return true;
    if (this.mode === "cascade") return false;
    return this.media ? !this.media.matches : true;
  }
  render() {
    this.itemsEl.replaceChildren();
    this.rootEl.classList.toggle(`${CLS}--cascade`, !this.isTabs());
    if (this.isTabs()) this.renderTabs();
    else this.renderCascade();
  }
  renderTabs() {
    const current = this.currentId === null ? null : this.resolve(this.currentId);
    this.itemsEl.setAttribute("role", "tablist");
    this.itemsEl.setAttribute("aria-orientation", "vertical");
    this.items.forEach((item, index) => {
      const button = this.buildButton(item, index, "tab");
      const isActive = current !== null && current.root.id === item.id;
      button.classList.toggle("active", isActive);
      button.setAttribute("aria-selected", String(isActive));
      button.tabIndex = isActive || current === null && index === 0 ? 0 : -1;
      if (isActive && current !== null && current.path.length > 1) {
        button.title = current.path.map((node) => node.label).reverse().join(" / ");
      }
      this.itemsEl.appendChild(button);
    });
  }
  renderCascade() {
    const current = this.currentId === null ? null : this.resolve(this.currentId);
    const openPath = current ? [...current.path].reverse() : [];
    let level = this.items;
    let depth = 0;
    while (level.length > 0) {
      const openNode = openPath[depth];
      this.itemsEl.appendChild(this.buildCascadeLevel(level, current, openNode, depth));
      if (!openNode || !(openNode.children ?? []).length) break;
      level = openNode.children ?? [];
      depth += 1;
    }
  }
  buildCascadeLevel(nodes, current, open, depth) {
    const list = document.createElement("div");
    list.className = `${CLS}__level`;
    list.setAttribute("data-stx-depth", String(depth));
    list.setAttribute("role", "listbox");
    nodes.forEach((node, index) => {
      const button = this.buildButton(node, index, "option");
      const isSelected = current !== null && current.item.id === node.id;
      button.setAttribute("aria-selected", String(isSelected));
      if (isSelected) button.classList.add("active");
      if (open && open.id === node.id) button.setAttribute("aria-expanded", "true");
      list.appendChild(button);
    });
    return list;
  }
  buildButton(item, index, role) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `${CLS}__item`;
    button.setAttribute("role", role);
    button.setAttribute("data-stx-selector-id", item.id);
    if (item.icon) {
      const glyph = document.createElement("i");
      glyph.className = item.icon;
      button.appendChild(glyph);
    }
    const label = document.createElement("span");
    label.className = `${CLS}__label`;
    label.textContent = item.label;
    button.appendChild(label);
    button.addEventListener("click", () => this.activate(item, index));
    button.addEventListener("keydown", (event) => this.onKeydown(event, index));
    return button;
  }
  /**
   * A selection is reported for BOTH shapes through one path, so a leaf wires
   * one handler and the presentation stays the primitive's business.
   */
  activate(item, index) {
    const hasChildren = (item.children ?? []).length > 0;
    if (!this.isTabs() && hasChildren) {
      this.currentId = item.id;
      this.render();
      this.emitChange();
      this.focusAt(index + 1);
      return;
    }
    this.currentId = item.id;
    this.render();
    this.emitChange();
  }
  emitChange() {
    const current = this.currentId === null ? null : this.resolve(this.currentId);
    if (!current) return;
    const detail = { id: current.item.id, path: current.path };
    this.config.onSelect?.(current.item, current.path);
    this.emit(SELECTOR_NAV_CHANGE, detail);
  }
  /** Arrow/Home/End/Escape, shared by both shapes; the axis follows the shape. */
  onKeydown(event, index) {
    const buttons = Array.from(
      this.itemsEl.querySelectorAll(`.${CLS}__item`)
    );
    const tabs = this.isTabs();
    const forward = tabs ? "ArrowDown" : "ArrowRight";
    const back = tabs ? "ArrowUp" : "ArrowLeft";
    let next = null;
    if (event.key === forward) next = index + 1;
    else if (event.key === back) next = index - 1;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = buttons.length - 1;
    else if (event.key === "Escape" && !tabs) {
      event.preventDefault();
      const parent = buttons.slice(0, index).reverse().find((node) => node.getAttribute("aria-expanded") === "true");
      parent?.focus();
      return;
    } else return;
    event.preventDefault();
    const target = buttons[next];
    if (target) {
      target.focus();
      buttons.forEach((node) => {
        node.tabIndex = node === target ? 0 : -1;
      });
    }
  }
  focusAt(index) {
    const buttons = this.itemsEl.querySelectorAll(`.${CLS}__item`);
    buttons[index]?.focus();
  }
  destroy() {
    this.media?.removeEventListener("change", this.onMediaChange);
    this.rootEl.remove();
    super.destroy();
  }
};

// ts/app/selector-nav/mount.ts
var MOUNTED_ATTRIBUTE = "data-stx-selector-nav-mounted";
var instances = [];
function readItems(element) {
  const raw = element.getAttribute("data-stx-items");
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) throw new TypeError("not an array of nodes");
    return parsed;
  } catch (error) {
    throw new Error(
      `SelectorNav: ${SELECTOR_NAV_ATTRIBUTE} carries an unreadable data-stx-items payload (${error.message}). Refusing to render a selector with no sections.`
    );
  }
}
function mountSelectorNavs(root = document, options = {}) {
  const mounted = [];
  for (const element of Array.from(
    root.querySelectorAll(`[${SELECTOR_NAV_ATTRIBUTE}]`)
  )) {
    if (element.hasAttribute(MOUNTED_ATTRIBUTE)) continue;
    element.setAttribute(MOUNTED_ATTRIBUTE, "");
    const nav = new SelectorNav({
      ...options,
      container: element,
      items: options.items ?? readItems(element),
      current: options.current ?? element.getAttribute("data-stx-current")
    });
    instances.push(nav);
    mounted.push(nav);
  }
  return mounted;
}
function getSelectorNav() {
  return instances.length === 1 ? instances[0] : null;
}
function selectSelectorNav(id) {
  getSelectorNav()?.setCurrent(id);
}
var stxSelectorNav = {
  mount: mountSelectorNavs,
  get: getSelectorNav,
  select: selectSelectorNav
};

// ts/app/selector-nav/auto-mount.ts
window.stxSelectorNav = stxSelectorNav;
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => mountSelectorNavs());
} else {
  mountSelectorNavs();
}
export {
  SELECTOR_NAV_ATTRIBUTE,
  SELECTOR_NAV_CHANGE,
  SelectorNav
};
