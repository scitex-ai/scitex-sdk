/** Selected-tab DOM contract: the producer emits what the stylesheet reads.
 *
 * Card ui-tabs-selected-state-standard-20260918. `panes.css` and
 * `content-tabs.css` style selection exclusively through
 * `[aria-selected="true"]` on `role="tab"` elements with roving tabindex.
 * These tests pin the Panes producer to that markup contract: exactly one
 * tab selected, roving tabindex following selection, arrow keys moving
 * selection, and the stylesheet's selected selector matching the selected
 * tab and nothing else.
 */

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import { Panes } from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/ts/app/panes";
import type {
  PanesMedia,
  PanesStorage,
} from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/ts/app/panes";

const CSS_DIR = join(
  dirname(fileURLToPath(import.meta.url)),
  "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/css/app",
);

class MemoryStorage implements PanesStorage {
  private items = new Map<string, string>();
  getItem(key: string): string | null {
    return this.items.get(key) ?? null;
  }
  setItem(key: string, value: string): void {
    this.items.set(key, value);
  }
}

class FakeMedia implements PanesMedia {
  private listeners: Array<(event: { matches: boolean }) => void> = [];
  constructor(public matches: boolean) {}
  addEventListener(_type: "change", listener: (event: { matches: boolean }) => void): void {
    this.listeners.push(listener);
  }
}

const MARKUP = `
  <div data-stx-panes="demo">
    <section data-stx-pane="data" data-stx-label="Data">data</section>
    <section data-stx-pane="plot" data-stx-label="Plot">plot</section>
  </div>`;

function phone(): Panes {
  document.body.innerHTML = MARKUP;
  const root = document.querySelector<HTMLElement>("[data-stx-panes]")!;
  return new Panes(root, { media: new FakeMedia(true), storage: new MemoryStorage() });
}

function tabs(panes: Panes): HTMLElement[] {
  return Array.from(panes.tablist.querySelectorAll<HTMLElement>('[role="tab"]'));
}

describe("selected-tab DOM contract", () => {
  it("renders tabs with the tablist/tab roles and a single aria-selected", () => {
    const panes = phone();
    expect(panes.tablist.getAttribute("role")).toBe("tablist");
    const all = tabs(panes);
    expect(all).toHaveLength(2);
    expect(all.filter((t) => t.getAttribute("aria-selected") === "true")).toHaveLength(1);
    expect(all.filter((t) => t.getAttribute("aria-selected") === "false")).toHaveLength(1);
  });

  it("keeps roving tabindex on the selected tab", () => {
    const panes = phone();
    const selected = tabs(panes).find((t) => t.getAttribute("aria-selected") === "true")!;
    expect(selected.getAttribute("tabindex")).toBe("0");
    for (const t of tabs(panes).filter((t) => t !== selected)) {
      expect(t.getAttribute("tabindex")).toBe("-1");
    }
    panes.show("plot");
    const now = tabs(panes).find((t) => t.getAttribute("aria-selected") === "true")!;
    expect(now.textContent).toContain("Plot");
    expect(now.getAttribute("tabindex")).toBe("0");
  });

  it("moves selection with arrow keys", () => {
    const panes = phone();
    const first = tabs(panes)[0];
    first.focus();
    first.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }));
    expect(panes.active).toBe("plot");
    expect(
      tabs(panes).filter((t) => t.getAttribute("aria-selected") === "true"),
    ).toHaveLength(1);
  });

  it("stylesheet selected selectors match the selected tab and nothing else", () => {
    const panes = phone();
    for (const file of ["content-tabs.css", "panes.css"]) {
      const css = readFileSync(join(CSS_DIR, file), "utf-8");
      const selector = file === "content-tabs.css"
        ? '.stx-content-tabs__tab[aria-selected="true"]'
        : '.stx-panes__tab[aria-selected="true"]';
      expect(css).toContain(selector);
    }
    // The panes producer contract, read back through the panes selector:
    const matched = panes.tablist.querySelectorAll('.stx-panes__tab[aria-selected="true"]');
    expect(matched).toHaveLength(1);
    expect(matched[0].getAttribute("aria-selected")).toBe("true");
  });
});
