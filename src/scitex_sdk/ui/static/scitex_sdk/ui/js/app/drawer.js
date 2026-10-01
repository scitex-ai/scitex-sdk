// src/scitex_ui/static/scitex_ui/ts/app/drawer/_Drawer.ts
var FOCUSABLE = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  '[tabindex]:not([tabindex="-1"])'
].join(",");
var Drawer = class {
  panel;
  scrim;
  trigger;
  side;
  closeOnEscape;
  closeOnScrimClick;
  lockScroll;
  onOpen;
  onClose;
  /** The single source of truth. Both elements are rendered FROM this. */
  isOpen = false;
  /** Focus to restore on close — captured at open, not assumed to be the trigger. */
  previouslyFocused = null;
  onKeydown = (event) => {
    if (!this.isOpen) return;
    if (this.closeOnEscape && event.key === "Escape") {
      event.preventDefault();
      this.close();
      return;
    }
    if (event.key === "Tab") this.trapFocus(event);
  };
  onScrimClick = () => {
    if (this.closeOnScrimClick) this.close();
  };
  constructor(config) {
    this.panel = config.panel;
    this.trigger = config.trigger ?? null;
    this.side = config.side ?? "left";
    this.closeOnEscape = config.closeOnEscape ?? true;
    this.closeOnScrimClick = config.closeOnScrimClick ?? true;
    this.lockScroll = config.lockScroll ?? true;
    this.onOpen = config.onOpen;
    this.onClose = config.onClose;
    this.panel.classList.add("stx-drawer");
    this.panel.dataset.side = this.side;
    this.scrim = document.createElement("div");
    this.scrim.className = "stx-drawer-scrim";
    this.scrim.setAttribute("aria-hidden", "true");
    const host = config.host ?? this.panel.parentElement ?? document.body;
    host.appendChild(this.scrim);
    this.render();
  }
  /** Wire listeners. Idempotent. */
  attach() {
    this.scrim.addEventListener("click", this.onScrimClick);
    document.addEventListener("keydown", this.onKeydown);
    this.trigger?.addEventListener("click", this.toggleFromTrigger);
    return this;
  }
  open() {
    if (this.isOpen) return this;
    this.previouslyFocused = document.activeElement;
    this.isOpen = true;
    this.render();
    this.focusFirst();
    this.onOpen?.();
    return this;
  }
  close() {
    if (!this.isOpen) return this;
    this.isOpen = false;
    this.render();
    this.restoreFocus();
    this.onClose?.();
    return this;
  }
  toggle() {
    return this.isOpen ? this.close() : this.open();
  }
  get open_() {
    return this.isOpen;
  }
  /** Remove listeners, the scrim, and any scroll lock. */
  destroy() {
    this.scrim.removeEventListener("click", this.onScrimClick);
    document.removeEventListener("keydown", this.onKeydown);
    this.trigger?.removeEventListener("click", this.toggleFromTrigger);
    document.body.classList.remove("stx-drawer-scroll-locked");
    this.scrim.remove();
  }
  toggleFromTrigger = () => {
    this.toggle();
  };
  /** Derive both elements from `isOpen`. The only place either is mutated. */
  render() {
    this.panel.classList.toggle("stx-drawer--open", this.isOpen);
    this.scrim.classList.toggle("stx-drawer-scrim--open", this.isOpen);
    this.panel.toggleAttribute("inert", !this.isOpen);
    this.trigger?.setAttribute("aria-expanded", String(this.isOpen));
    if (this.lockScroll) {
      document.body.classList.toggle("stx-drawer-scroll-locked", this.isOpen);
    }
  }
  focusables() {
    return Array.from(
      this.panel.querySelectorAll(FOCUSABLE)
    ).filter((el) => el.offsetParent !== null || el === document.activeElement);
  }
  focusFirst() {
    const [first] = this.focusables();
    if (first) {
      first.focus();
      return;
    }
    if (!this.panel.hasAttribute("tabindex")) {
      this.panel.setAttribute("tabindex", "-1");
    }
    this.panel.focus();
  }
  restoreFocus() {
    const target = this.previouslyFocused ?? this.trigger;
    this.previouslyFocused = null;
    if (target?.isConnected) target.focus();
  }
  trapFocus(event) {
    const items = this.focusables();
    if (items.length === 0) {
      event.preventDefault();
      return;
    }
    const first = items[0];
    const last = items[items.length - 1];
    const active = document.activeElement;
    if (event.shiftKey && (active === first || active === this.panel)) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && active === last) {
      event.preventDefault();
      first.focus();
    }
  }
};
function createDrawer(config) {
  return new Drawer(config).attach();
}

// src/scitex_ui/static/scitex_ui/ts/app/drawer/types.ts
var DRAWER_SIDES = ["left", "right"];
export {
  DRAWER_SIDES,
  Drawer,
  createDrawer
};
