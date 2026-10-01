/* AUTO-GENERATED from ts/app/context-menu/index.ts via esbuild — do not edit by hand. Rebuild: npx esbuild ts/app/context-menu/index.ts --bundle --format=esm --outfile=js/app/context-menu.js */
var __defProp = Object.defineProperty;
var __defNormalProp = (obj, key, value) => key in obj ? __defProp(obj, key, { enumerable: true, configurable: true, writable: true, value }) : obj[key] = value;
var __publicField = (obj, key, value) => __defNormalProp(obj, typeof key !== "symbol" ? key + "" : key, value);

// ts/app/context-menu/_ContextMenu.ts
var EDGE_PADDING_DEFAULT = 10;
function isItem(entry) {
  return entry.kind === void 0 || entry.kind === "item";
}
var ContextMenu = class {
  constructor(config) {
    this.config = config;
    __publicField(this, "menu", null);
    __publicField(this, "open", false);
    __publicField(this, "edgePadding");
    __publicField(this, "onContextMenu", null);
    __publicField(this, "boundHost", null);
    __publicField(this, "onOutside", (e) => {
      if (this.menu && !this.menu.contains(e.target)) this.close();
    });
    __publicField(this, "onDismiss", () => {
      this.close();
    });
    __publicField(this, "onKeydown", (e) => {
      if (!this.open) return;
      const items = this.items();
      if (items.length === 0) return;
      const current = items.indexOf(document.activeElement);
      switch (e.key) {
        case "Escape":
          e.preventDefault();
          this.close();
          break;
        case "ArrowDown":
          e.preventDefault();
          items[(current + 1) % items.length].focus();
          break;
        case "ArrowUp":
          e.preventDefault();
          items[(current - 1 + items.length) % items.length].focus();
          break;
        case "Home":
          e.preventDefault();
          items[0].focus();
          break;
        case "End":
          e.preventDefault();
          items[items.length - 1].focus();
          break;
        default:
          break;
      }
    });
    this.edgePadding = config.edgePadding ?? EDGE_PADDING_DEFAULT;
  }
  /** Bind the right-click handler. Returns this, so callers can chain. */
  attach() {
    const host = this.resolveHost();
    if (!host) return this;
    this.onContextMenu = (e) => {
      const target = e.target;
      if (!target) return;
      e.preventDefault();
      this.openAt(e.clientX, e.clientY, target);
    };
    host.addEventListener("contextmenu", this.onContextMenu);
    this.boundHost = host;
    return this;
  }
  /** Open at viewport coordinates. `target` feeds the items() callback. */
  openAt(x, y, target) {
    this.close();
    const entries = typeof this.config.items === "function" ? this.config.items(target ?? document.body) : this.config.items;
    if (entries.length === 0) return;
    this.menu = this.render(entries);
    document.body.appendChild(this.menu);
    this.position(x, y);
    this.open = true;
    document.addEventListener("pointerdown", this.onOutside, true);
    document.addEventListener("keydown", this.onKeydown, true);
    document.addEventListener("scroll", this.onDismiss, true);
    window.addEventListener("resize", this.onDismiss);
    window.addEventListener("blur", this.onDismiss);
    this.config.onOpen?.();
  }
  close() {
    if (!this.open || !this.menu) return;
    document.removeEventListener("pointerdown", this.onOutside, true);
    document.removeEventListener("keydown", this.onKeydown, true);
    document.removeEventListener("scroll", this.onDismiss, true);
    window.removeEventListener("resize", this.onDismiss);
    window.removeEventListener("blur", this.onDismiss);
    this.menu.remove();
    this.menu = null;
    this.open = false;
    this.config.onClose?.();
  }
  /** Remove the right-click binding and any open menu. */
  destroy() {
    this.close();
    if (this.boundHost && this.onContextMenu) {
      this.boundHost.removeEventListener(
        "contextmenu",
        this.onContextMenu
      );
    }
    this.boundHost = null;
    this.onContextMenu = null;
  }
  // --- internals ---
  resolveHost() {
    const t = this.config.target;
    if (t === void 0) return document;
    if (typeof t === "string") return document.querySelector(t);
    return t;
  }
  render(entries) {
    const menu = document.createElement("div");
    menu.className = "stx-app-context-menu";
    menu.setAttribute("role", "menu");
    for (const entry of entries) {
      if (entry.kind === "divider") {
        const el = document.createElement("div");
        el.className = "stx-app-context-menu__divider";
        menu.appendChild(el);
        continue;
      }
      if (entry.kind === "label") {
        const el = document.createElement("div");
        el.className = "stx-app-context-menu__label";
        el.textContent = entry.label;
        menu.appendChild(el);
        continue;
      }
      if (!isItem(entry)) continue;
      menu.appendChild(this.renderItem(entry));
    }
    return menu;
  }
  renderItem(item) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "stx-app-context-menu__item";
    if (item.danger) btn.classList.add("stx-app-context-menu__item--danger");
    btn.setAttribute("role", "menuitem");
    if (item.disabled) btn.disabled = true;
    if (item.icon) {
      const i = document.createElement("i");
      i.className = item.icon;
      btn.appendChild(i);
    }
    btn.appendChild(document.createTextNode(item.label));
    if (item.shortcut) {
      const s = document.createElement("span");
      s.className = "stx-app-context-menu__shortcut";
      s.textContent = item.shortcut;
      btn.appendChild(s);
    }
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      if (item.disabled) return;
      this.close();
      item.onSelect?.();
    });
    return btn;
  }
  position(x, y) {
    const menu = this.menu;
    if (!menu) return;
    const pad = this.edgePadding;
    menu.style.left = "-9999px";
    menu.style.top = "-9999px";
    const { offsetWidth: w, offsetHeight: h } = menu;
    let left = x;
    let top = y;
    if (x + w > window.innerWidth - pad) left = Math.max(pad, x - w);
    if (y + h > window.innerHeight - pad) top = Math.max(pad, y - h);
    menu.style.left = `${left}px`;
    menu.style.top = `${top}px`;
  }
  items() {
    if (!this.menu) return [];
    return Array.from(
      this.menu.querySelectorAll(
        ".stx-app-context-menu__item:not(:disabled)"
      )
    );
  }
};
function initContextMenu(config) {
  return new ContextMenu(config).attach();
}
export {
  ContextMenu,
  initContextMenu
};
