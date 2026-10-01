/**
 * Context menu — public types.
 */

/** A selectable row. `kind` may be omitted; an entry without `kind` is an item. */
export interface ContextMenuItem {
  kind?: "item";
  label: string;
  /** Icon font class, e.g. "fas fa-reply". Rendered into the styled icon slot. */
  icon?: string;
  /** Right-aligned keyboard hint, e.g. "Ctrl+R". */
  shortcut?: string;
  /** Destructive styling (red). */
  danger?: boolean;
  /** Renders the real `disabled` attribute, so :disabled styling applies. */
  disabled?: boolean;
  onSelect?: () => void;
}

/** A horizontal rule between groups. */
export interface ContextMenuDivider {
  kind: "divider";
}

/** An uppercase section heading between groups. */
export interface ContextMenuLabel {
  kind: "label";
  label: string;
}

export type ContextMenuEntry =
  | ContextMenuItem
  | ContextMenuDivider
  | ContextMenuLabel;

export interface ContextMenuConfig {
  /**
   * The entries, or a function computing them from the right-clicked element.
   * Use the function form for context-aware menus — it runs on every open, so
   * the menu reflects what was actually clicked rather than a stale snapshot.
   */
  items: ContextMenuEntry[] | ((target: HTMLElement) => ContextMenuEntry[]);
  /**
   * Restrict right-click handling to this element (or the first match of this
   * selector). Omit to handle the whole document.
   */
  target?: string | HTMLElement;
  /** Minimum gap kept between the menu and the viewport edge. Default 10. */
  edgePadding?: number;
  onOpen?: () => void;
  onClose?: () => void;
}
