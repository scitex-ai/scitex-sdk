/**
 * Empty state — public types.
 */

export interface EmptyStateConfig {
  /**
   * The primary line. Required: an empty state with no words is a blank area
   * the user cannot distinguish from a loading failure.
   */
  title: string;
  /** Secondary line — usually what to do about it. */
  hint?: string;
  /** Icon-font class, e.g. "fas fa-inbox". Hidden in compact. */
  iconClass?: string;
  /**
   * Optional call to action, which is what turns a dead end into a next step.
   * Hidden in compact.
   */
  action?: HTMLElement;
  /**
   * Compact renders a single muted line for dropdowns and narrow panes.
   * Default is the full-panel form.
   */
  compact?: boolean;
}
