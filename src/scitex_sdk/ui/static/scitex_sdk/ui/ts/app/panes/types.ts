/** Types for the mobile panes primitive. */

/** One pane an app declared with `data-stx-pane`. */
export interface PaneInfo {
  id: string;
  label: string;
  icon: string;
  order: number;
  element: HTMLElement;
}

/** The subset of MediaQueryList the panes read; lets tests pass a stand-in. */
export interface PanesMedia {
  matches: boolean;
  addEventListener(type: "change", listener: (event: { matches: boolean }) => void): void;
}

/** The subset of Storage the panes use. */
export interface PanesStorage {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

export interface PanesOptions {
  /** Storage namespace; defaults to the root's `data-stx-panes` value, then the path. */
  app?: string;
  /** Phone breakpoint query result; defaults to `matchMedia(PHONE_QUERY)`. */
  media?: PanesMedia | null;
  /** Where the active pane is remembered; defaults to sessionStorage. */
  storage?: PanesStorage | null;
  /**
   * Enable horizontal swipe-to-switch-tab on single-pane (phone) mode.
   *
   * Default: **false**. Operator mobile ruling 7724-7725: horizontal swipe
   * conflicts with pan/zoom/scroll inside Writer PDF, FigRecipe canvas,
   * graphs, editors, and tables. App tabs change only by explicit tab tap,
   * accessible keyboard activation, or a named command; content gestures
   * belong to the active pane.
   *
   * When true, the `startsInsideOwnGesture` guard still applies: swipes
   * beginning inside a horizontal scroller, a text input, or interactive
   * content (canvas, svg, table, iframe, PDF/canvas/graph/editor wrappers)
   * are ignored.
   */
  swipeToSwitch?: boolean;
}

export interface PanesChangeDetail {
  app: string;
  pane: string;
  previous: string | null;
}
