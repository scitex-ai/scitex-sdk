/**
 * Drawer — off-canvas panel with a scrim.
 *
 * Harvested from scitex-cards' chat.js mobile drawer. That implementation is
 * ten lines and works visually; what it lacks is everything a keyboard or
 * screen-reader user needs, plus one state bug:
 *
 *   1. THE CLOSED DRAWER WAS STILL FOCUSABLE. The panel is `position: fixed`
 *      pushed off-screen with `transform: translateX(-105%)`. A transform
 *      moves pixels — it does NOT remove the element from the tab order or
 *      the accessibility tree. So on a phone-width layout, tabbing from the
 *      header walked into an invisible agent list: focus vanished off-screen
 *      with no visible ring, and the next Enter activated a link the user
 *      could not see. `inert` is what actually closes it.
 *
 *   2. NO ESCAPE. An overlay you can open with the keyboard but only close
 *      with a pointer is a trap on any device with a keyboard attached.
 *
 *   3. FOCUS WAS NEVER MOVED OR RESTORED. Opening left focus behind the
 *      scrim; closing left it on an element that had just become inert.
 *
 *   4. TWO INDEPENDENT `.open` TOGGLES. `$agents.classList.toggle("open")`
 *      and `$scrim.classList.toggle("open")` are separate flips of separate
 *      elements. Any path that clears one without the other — and `closeDrawer`
 *      is called from elsewhere in that file — desynchronises them, after
 *      which one click puts them in OPPOSITE states: a scrim with no drawer,
 *      or a drawer with no scrim to dismiss it. One boolean owns the state
 *      here and both elements are derived from it.
 *
 *   5. NO `aria-expanded` on the trigger, so the control announced nothing
 *      about what it did.
 *
 * The scrim is owned rather than borrowed: the original required a
 * hand-placed `<div id="scrim">` in every template that wanted a drawer.
 */

import type { DrawerConfig, DrawerSide } from "./types";

/**
 * Focusable candidates. `:not([inert])` is deliberately absent — inert
 * subtrees are filtered by checking the element's own visibility below, since
 * inertness is inherited and a selector cannot see ancestors.
 */
const FOCUSABLE = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  '[tabindex]:not([tabindex="-1"])',
].join(",");

export class Drawer {
  readonly panel: HTMLElement;
  readonly scrim: HTMLDivElement;

  private readonly trigger: HTMLElement | null;
  private readonly side: DrawerSide;
  private readonly closeOnEscape: boolean;
  private readonly closeOnScrimClick: boolean;
  private readonly lockScroll: boolean;
  private readonly onOpen?: () => void;
  private readonly onClose?: () => void;

  /** The single source of truth. Both elements are rendered FROM this. */
  private isOpen = false;

  /** Focus to restore on close — captured at open, not assumed to be the trigger. */
  private previouslyFocused: HTMLElement | null = null;

  private readonly onKeydown = (event: KeyboardEvent): void => {
    if (!this.isOpen) return;
    if (this.closeOnEscape && event.key === "Escape") {
      event.preventDefault();
      this.close();
      return;
    }
    if (event.key === "Tab") this.trapFocus(event);
  };

  private readonly onScrimClick = (): void => {
    if (this.closeOnScrimClick) this.close();
  };

  constructor(config: DrawerConfig) {
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
    // The scrim is decoration for a state already announced by aria-expanded
    // and by focus being inside the panel.
    this.scrim.setAttribute("aria-hidden", "true");

    const host = config.host ?? this.panel.parentElement ?? document.body;
    host.appendChild(this.scrim);

    this.render();
  }

  /** Wire listeners. Idempotent. */
  attach(): this {
    this.scrim.addEventListener("click", this.onScrimClick);
    document.addEventListener("keydown", this.onKeydown);
    this.trigger?.addEventListener("click", this.toggleFromTrigger);
    return this;
  }

  open(): this {
    if (this.isOpen) return this;
    this.previouslyFocused = document.activeElement as HTMLElement | null;
    this.isOpen = true;
    this.render();
    this.focusFirst();
    this.onOpen?.();
    return this;
  }

  close(): this {
    if (!this.isOpen) return this;
    this.isOpen = false;
    this.render();
    // Restore focus BEFORE the caller's onClose, so a handler that moves
    // focus deliberately wins rather than being overwritten by us.
    this.restoreFocus();
    this.onClose?.();
    return this;
  }

  toggle(): this {
    return this.isOpen ? this.close() : this.open();
  }

  get open_(): boolean {
    return this.isOpen;
  }

  /** Remove listeners, the scrim, and any scroll lock. */
  destroy(): void {
    this.scrim.removeEventListener("click", this.onScrimClick);
    document.removeEventListener("keydown", this.onKeydown);
    this.trigger?.removeEventListener("click", this.toggleFromTrigger);
    // Releasing the lock matters: destroying an open drawer would otherwise
    // leave the page permanently unscrollable.
    document.body.classList.remove("stx-drawer-scroll-locked");
    this.scrim.remove();
  }

  private readonly toggleFromTrigger = (): void => {
    this.toggle();
  };

  /** Derive both elements from `isOpen`. The only place either is mutated. */
  private render(): void {
    this.panel.classList.toggle("stx-drawer--open", this.isOpen);
    this.scrim.classList.toggle("stx-drawer-scrim--open", this.isOpen);

    // `inert` is the point of this component. Without it the closed panel is
    // off-screen but still tabbable, and focus disappears into it.
    this.panel.toggleAttribute("inert", !this.isOpen);

    this.trigger?.setAttribute("aria-expanded", String(this.isOpen));

    if (this.lockScroll) {
      document.body.classList.toggle("stx-drawer-scroll-locked", this.isOpen);
    }
  }

  private focusables(): HTMLElement[] {
    return Array.from(
      this.panel.querySelectorAll<HTMLElement>(FOCUSABLE),
    ).filter((el) => el.offsetParent !== null || el === document.activeElement);
  }

  private focusFirst(): void {
    const [first] = this.focusables();
    if (first) {
      first.focus();
      return;
    }
    // An empty drawer still needs to hold focus, or Tab immediately escapes
    // to the page behind the scrim.
    if (!this.panel.hasAttribute("tabindex")) {
      this.panel.setAttribute("tabindex", "-1");
    }
    this.panel.focus();
  }

  private restoreFocus(): void {
    const target = this.previouslyFocused ?? this.trigger;
    this.previouslyFocused = null;
    // Only restore if the element is still in the document; a drawer that
    // replaced the page content would otherwise throw or focus a detached node.
    if (target?.isConnected) target.focus();
  }

  private trapFocus(event: KeyboardEvent): void {
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
}

/** Create, wire, and return a drawer. Starts closed. */
export function createDrawer(config: DrawerConfig): Drawer {
  return new Drawer(config).attach();
}
