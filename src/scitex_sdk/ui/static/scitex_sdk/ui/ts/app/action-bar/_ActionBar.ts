/**
 * ActionBar — the phone bottom action bar, once.
 *
 * EXTRACTED FROM REAL IMPLEMENTATIONS, as the operator's 2026-09-14 YAGNI
 * direction requires (card ui-mobile-layout-primitives-extract-from-apps-20260914).
 * scitex-writer shipped this shape first, in its own CSS
 * (`static/writer/css/editor-mobile.css`, `.writer-mobile-actions`), and its
 * comments are the specification this primitive is derived from:
 *
 *     "The action bar is fixed, so the pane has to reserve its height or the
 *      editor's last line hides behind it."
 *     "Above the hub's site dock when there is one, and above the iOS home bar
 *      always: a fixed bar at bottom: 0 puts its buttons under both."
 *
 * THREE THINGS A CONSUMER HAD TO GET RIGHT BY HAND, and the only three this
 * module exists to stop being re-derived:
 *
 *   1. The reservation. The bar is out of flow, so something must reserve its
 *      height. This publishes the MEASURED height as
 *      `--stx-action-bar-height` — measured, not a magic 56px, because a
 *      translated label or a two-line item makes the real bar taller and a
 *      hardcoded number then hides the last line of content.
 *   2. Where the reservation goes. On the bar's own container (its parent), or
 *      a host the consumer names. Never on body/html/:root — see the CSS
 *      header and `test_action_bar_contract.py`.
 *   3. Idempotency and a page API, so a Django template can load the pre-built
 *      bundle and a bundler consumer can mount it itself.
 */

import {
  ACTION_BAR_CHANGE,
  type ActionBarChangeDetail,
  type ActionBarOptions,
} from "./types";

/** Markup attribute a consumer puts on the bar element. */
export const BAR_ATTRIBUTE = "data-stx-action-bar";
/** Markup attribute a consumer puts on each control inside the bar. */
export const ITEM_ATTRIBUTE = "data-stx-action-bar-item";
/** Set once mounted, so a second mount pass is a no-op. */
export const MOUNTED_ATTRIBUTE = "data-stx-action-bar-mounted";
/** The custom property the measured height is published on. */
export const HEIGHT_PROPERTY = "--stx-action-bar-height";

const CLS = "stx-action-bar";
const CLS_ITEM = `${CLS}__item`;

export class ActionBar {
  readonly element: HTMLElement;
  private readonly reserveOn: HTMLElement | null;
  private readonly shouldMeasure: boolean;
  private observer: ResizeObserver | null = null;
  private lastHeight = 0;

  constructor(element: HTMLElement, options: ActionBarOptions = {}) {
    this.element = element;
    this.shouldMeasure = options.measure !== false;
    this.reserveOn =
      options.reserveOn === undefined
        ? (element.parentElement as HTMLElement | null)
        : options.reserveOn;

    element.classList.add(CLS);
    for (const item of Array.from(
      element.querySelectorAll<HTMLElement>(`[${ITEM_ATTRIBUTE}]`),
    )) {
      item.classList.add(CLS_ITEM);
    }

    this.refresh();
    this.observe();
  }

  /** The last measured height in CSS pixels (0 before the first measurement). */
  get height(): number {
    return this.lastHeight;
  }

  /** Re-measure now and republish. Safe to call any number of times. */
  refresh(): number {
    const height = this.shouldMeasure
      ? Math.round(this.element.getBoundingClientRect().height)
      : this.lastHeight;
    this.publish(height);
    return height;
  }

  /** Stop observing. The classes and the published height are left in place. */
  destroy(): void {
    this.observer?.disconnect();
    this.observer = null;
  }

  private observe(): void {
    if (!this.shouldMeasure || typeof ResizeObserver === "undefined") return;
    this.observer = new ResizeObserver(() => {
      this.refresh();
    });
    this.observer.observe(this.element);
  }

  private publish(height: number): void {
    if (height === this.lastHeight) return;
    this.lastHeight = height;
    this.reserveOn?.style.setProperty(HEIGHT_PROPERTY, `${height}px`);
    const detail: ActionBarChangeDetail = { height, reserveOn: this.reserveOn };
    this.element.dispatchEvent(
      new CustomEvent<ActionBarChangeDetail>(ACTION_BAR_CHANGE, { detail }),
    );
  }
}
