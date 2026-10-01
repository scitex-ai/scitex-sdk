/**
 * SelectorNav — types for the hierarchical selector/navigation primitive.
 *
 * ONE data source, TWO presentations (operator direction 2026-09-17, card
 * sdk-mobile-app-shell-primitives-20260917): a compact HIERARCHICAL selector is
 * a tab strip on desktop and a CASCADING DROPDOWN on mobile. The app declares
 * the tree once; which shape renders is the primitive's decision, at the shared
 * 600px phone boundary, so two apps cannot disagree about when to switch.
 */

import type { BaseComponentConfig } from "../../_base/types";

/** One node: a tab on desktop, a level in the cascade on mobile. */
export interface SelectorNavItem {
  /** Stable id. This is what a change event carries, and what a leaf routes on. */
  id: string;
  /** Visible label. The LEAF owns its translation. */
  label: string;
  /** Optional leading glyph (a class name, e.g. an icon font). */
  icon?: string;
  /** Omitted or empty = a leaf item: selecting it is a terminal choice. */
  children?: SelectorNavItem[];
}

/**
 * How the tree is presented.
 *
 *  ``auto``    (default) tabs at >= the phone boundary, cascade below it
 *  ``tabs``    always the strip (an app that wants the desktop form everywhere)
 *  ``cascade`` always the cascading form (a narrow pane on a wide screen)
 */
export type SelectorNavMode = "auto" | "tabs" | "cascade";

export interface SelectorNavConfig extends BaseComponentConfig {
  items?: SelectorNavItem[];
  /** Id of the selected node, at any depth. */
  current?: string | null;
  mode?: SelectorNavMode;
  /**
   * The phone boundary in CSS px. Defaults to 600 — the SAME value
   * css/app/project-selector.css and app-header.css switch at, so a page's
   * header, picker and selector all change shape on one event rather than three.
   */
  breakpoint?: number;
  /** Called with the selected node (and its ancestry) on every change. */
  onSelect?: (item: SelectorNavItem, path: SelectorNavItem[]) => void;
}

/** Emitted on the container (bubbling) whenever the selection changes. */
export interface SelectorNavChangeDetail {
  id: string;
  /** The selected node followed by its ancestors, nearest first. */
  path: SelectorNavItem[];
}

/** Where a node sits, resolved once per render. */
export interface SelectorNavResolution {
  item: SelectorNavItem;
  path: SelectorNavItem[];
  /** The top-level ancestor — the tab a cascade view is anchored in. */
  root: SelectorNavItem;
}

export const SELECTOR_NAV_CHANGE = "stx-app-selector-nav:change";
export const SELECTOR_NAV_ATTRIBUTE = "data-stx-selector-nav";
