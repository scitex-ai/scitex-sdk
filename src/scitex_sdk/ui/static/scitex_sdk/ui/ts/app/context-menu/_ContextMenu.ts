/**
 * ContextMenu — right-click menu behaviour for the `.stx-app-context-menu` CSS.
 *
 * Base shipped the LOOK and none of the MECHANICS: three context-menu
 * stylesheets and zero reusable lines of positioning or dismissal. So every
 * adopter wrote the same forty lines, and base itself grew a private one welded
 * into the data table (`data-table/_TableContextMenu.ts`, on its own
 * `.data-table-context-menu` class names). The clamping logic here is extracted
 * from that working implementation rather than reinvented.
 *
 * Fixed on the way out, because the welded version leaks: it registers document
 * `click` / `scroll` / `keydown` listeners in its constructor and never removes
 * them, so `destroy()` frees the element while the handlers live on forever.
 * Everything here is torn down in `destroy()`, and the dismissal listeners only
 * exist while the menu is actually open.
 */

import type { ContextMenuConfig, ContextMenuEntry, ContextMenuItem } from "./types";

const EDGE_PADDING_DEFAULT = 10;

function isItem(entry: ContextMenuEntry): entry is ContextMenuItem {
  return entry.kind === undefined || entry.kind === "item";
}

export class ContextMenu {
  private menu: HTMLElement | null = null;
  private open = false;
  private readonly edgePadding: number;
  private onContextMenu: ((e: MouseEvent) => void) | null = null;
  private boundHost: EventTarget | null = null;

  constructor(private readonly config: ContextMenuConfig) {
    this.edgePadding = config.edgePadding ?? EDGE_PADDING_DEFAULT;
  }

  /** Bind the right-click handler. Returns this, so callers can chain. */
  attach(): this {
    const host = this.resolveHost();
    if (!host) return this;
    this.onContextMenu = (e: MouseEvent) => {
      const target = e.target as HTMLElement | null;
      if (!target) return;
      e.preventDefault();
      this.openAt(e.clientX, e.clientY, target);
    };
    host.addEventListener("contextmenu", this.onContextMenu as EventListener);
    this.boundHost = host;
    return this;
  }

  /** Open at viewport coordinates. `target` feeds the items() callback. */
  openAt(x: number, y: number, target?: HTMLElement): void {
    this.close();
    const entries =
      typeof this.config.items === "function"
        ? this.config.items(target ?? document.body)
        : this.config.items;
    if (entries.length === 0) return;

    this.menu = this.render(entries);
    document.body.appendChild(this.menu);
    this.position(x, y);
    this.open = true;

    // Bound only while open — see the leak note in the class docstring.
    document.addEventListener("pointerdown", this.onOutside, true);
    document.addEventListener("keydown", this.onKeydown, true);
    document.addEventListener("scroll", this.onDismiss, true);
    window.addEventListener("resize", this.onDismiss);
    window.addEventListener("blur", this.onDismiss);

    this.config.onOpen?.();
  }

  close(): void {
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
  destroy(): void {
    this.close();
    if (this.boundHost && this.onContextMenu) {
      this.boundHost.removeEventListener(
        "contextmenu",
        this.onContextMenu as EventListener,
      );
    }
    this.boundHost = null;
    this.onContextMenu = null;
  }

  // --- internals ---

  private resolveHost(): EventTarget | null {
    const t = this.config.target;
    if (t === undefined) return document;
    if (typeof t === "string") return document.querySelector(t);
    return t;
  }

  private render(entries: ContextMenuEntry[]): HTMLElement {
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

  private renderItem(item: ContextMenuItem): HTMLButtonElement {
    // <button> is load-bearing: the stylesheet resets its background/border and
    // restores the inherited font, and `:disabled` only styles a real button.
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
      // Must be the LAST child: the stylesheet right-aligns it with margin-left:auto.
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

  private position(x: number, y: number): void {
    const menu = this.menu;
    if (!menu) return;
    const pad = this.edgePadding;

    // Measure off-screen first so the flip decision never flickers on screen.
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

  private items(): HTMLButtonElement[] {
    if (!this.menu) return [];
    return Array.from(
      this.menu.querySelectorAll<HTMLButtonElement>(
        ".stx-app-context-menu__item:not(:disabled)",
      ),
    );
  }

  private onOutside = (e: Event): void => {
    if (this.menu && !this.menu.contains(e.target as Node)) this.close();
  };

  private onDismiss = (): void => {
    this.close();
  };

  private onKeydown = (e: KeyboardEvent): void => {
    if (!this.open) return;
    const items = this.items();
    if (items.length === 0) return;
    const current = items.indexOf(document.activeElement as HTMLButtonElement);

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
  };
}

/** Convenience: construct and attach in one call. */
export function initContextMenu(config: ContextMenuConfig): ContextMenu {
  return new ContextMenu(config).attach();
}
