/**
 * Drawer — public types.
 */

/** Edge the drawer slides in from. */
export type DrawerSide = "left" | "right";

export const DRAWER_SIDES: readonly DrawerSide[] = ["left", "right"] as const;

export interface DrawerConfig {
  /** The panel that slides in. Supplied by the caller; the drawer never invents content. */
  panel: HTMLElement;

  /**
   * The control that opens it. Kept so the drawer can maintain
   * `aria-expanded` and return focus here on close — a keyboard user who
   * opened the drawer from this button expects to land back on it, not at the
   * top of the document.
   */
  trigger?: HTMLElement;

  side?: DrawerSide;

  /**
   * Element the scrim is appended to. Defaults to the panel's parent, so the
   * scrim shares a stacking context with the panel rather than landing in a
   * different one and rendering above or below it by accident.
   */
  host?: HTMLElement;

  /** Close when the Escape key is pressed. Defaults to true. */
  closeOnEscape?: boolean;

  /** Close when the scrim is clicked. Defaults to true. */
  closeOnScrimClick?: boolean;

  /**
   * Prevent the page behind from scrolling while open. Defaults to true —
   * on a phone, dragging over an open drawer otherwise scrolls the content
   * underneath it.
   */
  lockScroll?: boolean;

  onOpen?: () => void;
  onClose?: () => void;
}
