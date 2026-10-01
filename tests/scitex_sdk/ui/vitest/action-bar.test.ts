/** Bottom action bar: the reservation contract, not the pixels.
 *
 * `npx vitest run`
 *
 * The three things this file pins, because they are the three things every app
 * re-derived by hand before this primitive existed (scitex-writer's
 * `.writer-mobile-actions` is the implementation it was extracted from):
 *
 *   1. the bar publishes its MEASURED height, so a translated label or a
 *      two-item row cannot hide the last line of content behind a constant;
 *   2. the height is published on the CONSUMER'S container — never on
 *      `document.body` / `document.documentElement` (the launcher overlay
 *      shares this edge and forbids a reserved band on the page);
 *   3. mounting is idempotent, so a page that loads the bundle and also calls
 *      `mount()` does not end up with two bars' worth of state.
 */

import { beforeEach, describe, expect, it } from "vitest";

import {
  ActionBar,
  ACTION_BAR_CHANGE,
  BAR_ATTRIBUTE,
  HEIGHT_PROPERTY,
  ITEM_ATTRIBUTE,
  MOUNTED_ATTRIBUTE,
  mountActionBar,
  getActionBar,
  actionBarHeight,
} from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/ts/app/action-bar";

/** jsdom returns an all-zero rect; a bar reports its real height. */
function stubHeight(element: HTMLElement, height: number): void {
  element.getBoundingClientRect = () => ({ height } as unknown as DOMRect);
}

function markup(): HTMLElement {
  document.body.innerHTML = `
    <div class="editor-body">
      <p>content</p>
      <div ${BAR_ATTRIBUTE}>
        <button ${ITEM_ATTRIBUTE}>Compile</button>
        <button ${ITEM_ATTRIBUTE}>Preview</button>
      </div>
    </div>`;
  return document.querySelector<HTMLElement>(`[${BAR_ATTRIBUTE}]`) as HTMLElement;
}

describe("bottom action bar", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  it("mounts the declared bar and styles its items", () => {
    const bar = markup();

    const mounted = mountActionBar();

    expect(mounted).toHaveLength(1);
    expect(bar.classList.contains("stx-action-bar")).toBe(true);
    expect(bar.hasAttribute(MOUNTED_ATTRIBUTE)).toBe(true);
    expect(Array.from(bar.querySelectorAll("button")).map((b) => b.className)).toEqual([
      "stx-action-bar__item",
      "stx-action-bar__item",
    ]);
  });

  it("is idempotent: a second pass mounts nothing", () => {
    markup();
    mountActionBar();

    expect(mountActionBar()).toHaveLength(0);
  });

  it("publishes the MEASURED height on the bar's own container", () => {
    const bar = markup();
    const mounted = mountActionBar();
    const container = bar.parentElement as HTMLElement;
    stubHeight(bar, 72);

    mounted[0].refresh();

    expect(container.style.getPropertyValue(HEIGHT_PROPERTY)).toBe("72px");
    // and NOT on the page: a page-level band is the shape the launcher overlay
    // contract forbids, and it would shorten every other screen too.
    expect(document.documentElement.style.getPropertyValue(HEIGHT_PROPERTY)).toBe("");
    expect(document.body.style.getPropertyValue(HEIGHT_PROPERTY)).toBe("");
  });

  it("reports the change, so a consumer that virtualises can re-measure", () => {
    const bar = markup();
    const mounted = mountActionBar();
    stubHeight(bar, 64);
    const seen: number[] = [];
    bar.addEventListener(ACTION_BAR_CHANGE, (event) => {
      seen.push((event as CustomEvent<{ height: number }>).detail.height);
    });

    mounted[0].refresh();
    mounted[0].refresh(); // unchanged: no second event

    expect(seen).toEqual([64]);
  });

  it("honours an explicit reservation host over the default parent", () => {
    document.body.innerHTML = `
      <div class="pane">
        <div ${BAR_ATTRIBUTE}>
          <button ${ITEM_ATTRIBUTE}>Compile</button>
        </div>
      </div>
      <div class="scroller"></div>`;
    const bar = document.querySelector<HTMLElement>(`[${BAR_ATTRIBUTE}]`) as HTMLElement;
    const scroller = document.querySelector<HTMLElement>(".scroller") as HTMLElement;
    const mounted = mountActionBar(document, { reserveOn: scroller });
    stubHeight(bar, 58);

    mounted[0].refresh();

    expect(scroller.style.getPropertyValue(HEIGHT_PROPERTY)).toBe("58px");
    expect((bar.parentElement as HTMLElement).style.getPropertyValue(HEIGHT_PROPERTY)).toBe("");
  });

  it("can be told not to measure, for a bar of declared height", () => {
    const bar = markup();
    const mounted = mountActionBar(document, { measure: false });
    stubHeight(bar, 99);

    expect(mounted[0].refresh()).toBe(0);
    expect((bar.parentElement as HTMLElement).style.getPropertyValue(HEIGHT_PROPERTY)).toBe("");
  });

  it("exposes the mounted bar and its height as a page API", () => {
    const bar = markup();
    const mounted = mountActionBar();
    stubHeight(bar, 60);
    mounted[0].refresh();

    expect(getActionBar()).toBe(mounted[0]);
    expect(actionBarHeight()).toBe(60);
  });

  it("follows the bar through a resize observer when one exists", () => {
    const bar = markup();
    let trigger: (() => void) | null = null;
    class FakeObserver implements ResizeObserver {
      constructor(callback: ResizeObserverCallback) {
        trigger = () => callback([], this as unknown as ResizeObserver);
      }
      observe(): void {}
      unobserve(): void {}
      disconnect(): void {
        trigger = null;
      }
    }
    const real = (globalThis as { ResizeObserver?: unknown }).ResizeObserver;
    (globalThis as { ResizeObserver?: unknown }).ResizeObserver = FakeObserver;
    try {
      const mounted = mountActionBar();
      stubHeight(bar, 80);

      (trigger as unknown as () => void)();

      expect(mounted[0].height).toBe(80);
      mounted[0].destroy();
      expect(trigger).toBeNull();
    } finally {
      (globalThis as { ResizeObserver?: unknown }).ResizeObserver = real;
    }
  });

  it("constructs directly, for a consumer that owns the element", () => {
    const bar = markup();

    const actionBar = new ActionBar(bar, { reserveOn: null });

    expect(actionBar.element).toBe(bar);
    expect(actionBar.height).toBe(0);
  });
});
