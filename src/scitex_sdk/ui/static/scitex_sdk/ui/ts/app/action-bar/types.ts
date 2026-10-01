/**
 * Bottom action bar — public types.
 */

export interface ActionBarOptions {
  /**
   * The element that receives `--stx-action-bar-height` (the reservation).
   *
   * Defaults to the bar's own parent element — the container the app scrolls —
   * and deliberately NOT `document.body` / `document.documentElement`: see the
   * CSS header. Pass `null` to publish the height nowhere.
   */
  reserveOn?: HTMLElement | null;
  /**
   * Measure the rendered bar and republish its height. Default true. A bar
   * whose height is genuinely static may turn this off and declare its own
   * `--stx-action-bar-height`.
   */
  measure?: boolean;
}

export interface ActionBarChangeDetail {
  /** The measured bar height in CSS pixels. */
  height: number;
  /** The element the height was published on, or null. */
  reserveOn: HTMLElement | null;
}

/** Fired on the bar element whenever its measured height changes. */
export const ACTION_BAR_CHANGE = "stx-action-bar:change";
