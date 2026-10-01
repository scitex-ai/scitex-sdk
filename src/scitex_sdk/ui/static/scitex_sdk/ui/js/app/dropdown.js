// src/scitex_ui/static/scitex_ui/ts/_base/BaseComponent.ts
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

// src/scitex_ui/static/scitex_ui/ts/_base/fuzzy.ts
function fuzzyMatch(query, hay) {
  if (!query) return true;
  let i = 0;
  for (const c of query) {
    const found = hay.indexOf(c, i);
    if (found < 0) return false;
    i = found + 1;
  }
  return true;
}

// src/scitex_ui/static/scitex_ui/ts/app/dropdown/_Dropdown.ts
var CLS = "stx-app-dropdown";
var DEFAULT_FILTER_THRESHOLD = 8;
var Dropdown = class extends BaseComponent {
  triggerEl;
  menuEl = null;
  open = false;
  query = "";
  outsideClickHandler;
  triggerClickHandler;
  constructor(config) {
    super(config);
    this.triggerEl = typeof config.trigger === "string" ? document.querySelector(config.trigger) : config.trigger;
    if (!this.triggerEl) {
      throw new Error(`Dropdown: trigger not found: ${config.trigger}`);
    }
    this.outsideClickHandler = (e) => {
      const target = e.target;
      if (this.open && !this.container.contains(target) && !this.triggerEl.contains(target)) {
        this.close();
      }
    };
    this.triggerClickHandler = (e) => {
      e.stopPropagation();
      this.toggle();
    };
    this.triggerEl.addEventListener("click", this.triggerClickHandler);
    document.addEventListener("click", this.outsideClickHandler);
  }
  /** Whether the filter input should be shown for the current item list. */
  get filterEnabled() {
    if (this.config.filter !== void 0) return this.config.filter;
    const threshold = this.config.filterThreshold ?? DEFAULT_FILTER_THRESHOLD;
    const selectable = this.config.items.filter((i) => !i.separator).length;
    return selectable > threshold;
  }
  /** Items surviving the current query. Separators are dropped while
   *  filtering — a divider between two groups is meaningless once the groups
   *  it separated have been filtered away. */
  visibleItems() {
    if (!this.query) return this.config.items;
    const q = this.query.toLowerCase();
    return this.config.items.filter(
      (item) => !item.separator && fuzzyMatch(q, item.label.toLowerCase())
    );
  }
  /** Open the dropdown. */
  show() {
    if (this.open) return;
    this.open = true;
    this.query = "";
    this.renderMenu();
    this.container.style.display = "block";
    this.positionMenu();
    this.container.querySelector(`.${CLS}__filter`)?.focus();
  }
  /** Close the dropdown. */
  close() {
    if (!this.open) return;
    this.open = false;
    this.container.style.display = "none";
  }
  /** Toggle open/close. */
  toggle() {
    this.open ? this.close() : this.show();
  }
  /** Update items dynamically. */
  setItems(items) {
    this.config.items = items;
    if (this.open) this.renderMenu();
  }
  destroy() {
    document.removeEventListener("click", this.outsideClickHandler);
    this.triggerEl.removeEventListener("click", this.triggerClickHandler);
    super.destroy();
  }
  renderMenu() {
    this.container.innerHTML = "";
    this.container.className = CLS;
    if (this.filterEnabled) this.container.appendChild(this.buildFilter());
    const items = this.visibleItems();
    const menu = document.createElement("ul");
    menu.className = `${CLS}__menu`;
    if (items.length === 0) {
      const empty = document.createElement("li");
      empty.className = `${CLS}__empty`;
      empty.textContent = this.config.emptyText ?? "No matches";
      menu.appendChild(empty);
      this.container.appendChild(menu);
      this.menuEl = menu;
      return;
    }
    for (const item of items) {
      if (item.separator) {
        const sep = document.createElement("li");
        sep.className = `${CLS}__separator`;
        menu.appendChild(sep);
        continue;
      }
      const li = document.createElement("li");
      li.className = `${CLS}__item`;
      if (item.disabled) li.classList.add(`${CLS}__item--disabled`);
      if (item.icon) {
        const icon = document.createElement("i");
        icon.className = item.icon;
        li.appendChild(icon);
      }
      const label = document.createElement("span");
      label.textContent = item.label;
      li.appendChild(label);
      if (!item.disabled) {
        li.addEventListener("click", (e) => {
          e.stopPropagation();
          this.close();
          item.onClick?.();
          this.config.onSelect?.(item);
        });
      }
      menu.appendChild(li);
    }
    this.container.appendChild(menu);
    this.menuEl = menu;
  }
  buildFilter() {
    const input = document.createElement("input");
    input.type = "text";
    input.className = `${CLS}__filter`;
    input.placeholder = this.config.filterPlaceholder ?? "Filter\u2026";
    input.value = this.query;
    input.setAttribute("aria-label", input.placeholder);
    input.addEventListener("click", (e) => e.stopPropagation());
    input.addEventListener("input", () => {
      this.query = input.value;
      const caret = input.selectionStart;
      this.renderMenu();
      const next = this.container.querySelector(
        `.${CLS}__filter`
      );
      if (next) {
        next.focus();
        if (caret !== null) next.setSelectionRange(caret, caret);
      }
    });
    input.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        this.close();
        this.triggerEl.focus();
        return;
      }
      if (e.key === "Enter") {
        const remaining = this.visibleItems().filter((i) => !i.disabled);
        if (remaining.length === 1) {
          e.preventDefault();
          const only = remaining[0];
          this.close();
          only.onClick?.();
          this.config.onSelect?.(only);
        }
      }
    });
    return input;
  }
  positionMenu() {
    const rect = this.triggerEl.getBoundingClientRect();
    this.container.style.position = "absolute";
    this.container.style.top = `${rect.bottom + window.scrollY}px`;
    if (this.config.align === "right") {
      this.container.style.right = `${window.innerWidth - rect.right}px`;
      this.container.style.left = "auto";
    } else {
      this.container.style.left = `${rect.left + window.scrollX}px`;
      this.container.style.right = "auto";
    }
    this.container.style.zIndex = "100";
  }
};
export {
  Dropdown
};
