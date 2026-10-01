/**
 * Type definitions for the unified Resizer system.
 *
 * Two resizer types sharing a common base:
 *   HorizontalResizer -- left/right panels, X-axis drag
 *   VerticalResizer   -- top/bottom panels, Y-axis drag
 *
 * Plus the simple Resizer component API (ResizerConfig) for
 * consumers who want a BaseComponent-based interface.
 */

import type { BaseComponentConfig } from "../../_base/types";

// ── Unified resizer types (from scitex-cloud) ─────────────────────────

/** Configuration for HorizontalResizer */
export interface HorizontalConfig {
  left: string;
  right: string;
  icon: string;
  title: string;
  isMostLeft: boolean;
  isMostRight: boolean;
  thresholdPx: number;
  isInApp: boolean;
  storageKey?: string;
  onDragStart?: () => void;
  onDragEnd?: () => void;
  externalToggleBtnId?: string;
  accordion?: boolean;
  snapPoints?: number[];
  /**
   * Collapse this panel below the phone breakpoint, ignoring any size or
   * collapse state stored from a desktop session. Set via
   * `data-collapse-on-narrow` on the resizer element.
   *
   * OFF BY DEFAULT AND OPT-IN PER PANEL, deliberately. Measured on live prod
   * 2026-08-04: scitex-hub's Writer shows NO editing surface at 390px because
   * its Details aside is restored to a desktop width and occupies x=60..380 of
   * a 380px workspace. But this same resizer also drives Scholar's library
   * panes, whose mobile layout ALREADY works -- they are full-width
   * scroll-snap swipe pages. Collapsing every panel would fix one app by
   * breaking another, so the panel that needs it must ask.
   */
  collapseOnNarrow?: boolean;
  /** Media query defining "narrow" for collapseOnNarrow (default: 768px). */
  narrowQuery?: string;
}

/** Configuration for VerticalResizer */
export interface VerticalConfig {
  top: string;
  bottom: string;
  icon: string;
  title: string;
  isMostTop: boolean;
  isMostBottom: boolean;
  thresholdPx: number;
  isInApp: boolean;
  storageKey?: string;
  onDragStart?: () => void;
  onDragEnd?: () => void;
  accordion?: boolean;
  snapPoints?: number[];
}

/** Internal options passed from subclass to BaseResizer */
export interface BaseOpts {
  icon: string;
  title: string;
  firstCanCollapse: boolean;
  secondCanCollapse: boolean;
  thresholdPx: number;
  isInApp: boolean;
  storageKey: string;
  onDragStart?: () => void;
  onDragEnd?: () => void;
  externalToggleBtnId?: string;
  accordion?: boolean;
  snapPoints?: number[];
  /** See HorizontalConfig.collapseOnNarrow — opt-in, off by default. */
  collapseOnNarrow?: boolean;
  /** Media query defining "narrow" for collapseOnNarrow (default: 768px). */
  narrowQuery?: string;
}

/** Cascade propagation target tracked during a drag operation */
export interface PropagationTarget {
  panel: HTMLElement;
  storageKey: string;
  startSize: number;
  startPos: number;
  thresholdPx: number;
  toggleBtn: HTMLElement | null;
  toggleIcon: string;
}

// ── Simple Resizer component types ─────────────────────────────────────

export type ResizerDirection = "horizontal" | "vertical";

export interface ResizerConfig extends BaseComponentConfig {
  /** Resize direction: horizontal (left/right) or vertical (top/bottom) */
  direction: ResizerDirection;
  /** CSS selector or element for the first (left/top) panel */
  firstPanel: string | HTMLElement;
  /** CSS selector or element for the second (right/bottom) panel */
  secondPanel: string | HTMLElement;
  /** Minimum size in pixels for first panel (default: 48) */
  minFirst?: number;
  /** Minimum size in pixels for second panel (default: 48) */
  minSecond?: number;
  /** localStorage key for persisting size (default: none) */
  storageKey?: string;
  /** Show collapse toggle button (default: true) */
  showToggle?: boolean;
  /** Which panel collapses on toggle: "first" or "second" (default: "first") */
  collapseTarget?: "first" | "second";
  /** Callback when panel is resized */
  onResize?: (firstSize: number, secondSize: number) => void;
  /** Callback when panel is collapsed/expanded */
  onToggle?: (collapsed: boolean) => void;
}
