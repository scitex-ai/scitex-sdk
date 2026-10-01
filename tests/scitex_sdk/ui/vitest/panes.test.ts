/** Mobile panes: switching, persistence, breakpoint, swipe. `npx vitest run`

Swipe-to-switch-tab is DISABLED by default (operator mobile ruling 7724-7725):
horizontal content gestures (PDF pan, canvas drag, table scroll) must not
change the active tab. The default is explicit tab tap/click, keyboard
activation on the tablist, or a named `show()` command. Apps may opt in with
`swipeToSwitch: true`; when opted in, swipes beginning inside interactive
content (canvas, svg, table, iframe, PDF/canvas/graph/editor wrappers) are
ignored. */

import { beforeEach, describe, expect, it } from "vitest";

import {
  ACTIVE_ATTRIBUTE,
  Panes,
  PANES_CHANGE,
  SINGLE_CLASS,
} from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/ts/app/panes";
import type {
  PanesMedia,
  PanesOptions,
  PanesStorage,
} from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/ts/app/panes";

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
  set(matches: boolean): void {
    this.matches = matches;
    this.listeners.forEach((listener) => listener({ matches }));
  }
}

const MARKUP = `
  <div data-stx-panes="demo">
    <section data-stx-pane="data" data-stx-label="Data" data-stx-icon="D">
      <input id="field">
      <div id="rail" style="overflow-x: auto"><div style="width: 2000px">wide</div></div>
      <div id="pdf" class="stx-pdf-viewer"><canvas id="page"></canvas></div>
      <div id="graph" class="stx-graph"><svg width="400" height="300"></svg></div>
      <table id="table"><tr><td>cell</td></tr></table>
    </section>
    <section data-stx-pane="settings" data-stx-label="Settings" data-stx-order="3">settings</section>
    <section data-stx-pane="plot" data-stx-label="Plot" data-stx-order="2">plot</section>
  </div>`;

function root(): HTMLElement {
  document.body.innerHTML = MARKUP;
  return document.querySelector<HTMLElement>("[data-stx-panes]")!;
}

function phone(options: PanesOptions = {}): Panes {
  return new Panes(root(), { media: new FakeMedia(true), storage: new MemoryStorage(), ...options });
}

function activePane(panes: Panes): string | null {
  return panes.root.querySelector(`[${ACTIVE_ATTRIBUTE}]`)?.getAttribute("data-stx-pane") ?? null;
}

function swipe(target: Element, dx: number, dy = 0): void {
  const start = Object.assign(new Event("touchstart", { bubbles: true }), {
    touches: [{ clientX: 200, clientY: 300 }],
  });
  const end = Object.assign(new Event("touchend", { bubbles: true }), {
    touches: [],
    changedTouches: [{ clientX: 200 + dx, clientY: 300 + dy }],
  });
  target.dispatchEvent(start);
  target.dispatchEvent(end);
}

beforeEach(() => {
  document.body.innerHTML = "";
});

describe("pane switching", () => {
  it("starts on the first pane in declared order", () => {
    // Arrange
    const panes = phone();
    // Act
    const active = activePane(panes);
    // Assert
    expect(active).toBe("data");
  });

  it("orders the tabs by data-stx-order", () => {
    // Arrange
    const panes = phone();
    // Act
    const labels = Array.from(panes.tablist.querySelectorAll(".stx-panes__tab-label")).map(
      (label) => label.textContent,
    );
    // Assert
    expect(labels).toEqual(["Data", "Plot", "Settings"]);
  });

  it("shows the pane whose tab is clicked", () => {
    // Arrange
    const panes = phone();
    const tab = panes.tablist.querySelector<HTMLElement>('[data-stx-pane-tab="settings"]')!;
    // Act
    tab.click();
    // Assert
    expect(activePane(panes)).toBe("settings");
  });

  it("switches programmatically with show()", () => {
    // Arrange
    const panes = phone();
    // Act
    panes.show("plot");
    // Assert
    expect(activePane(panes)).toBe("plot");
  });

  it("marks only the active tab selected", () => {
    // Arrange
    const panes = phone();
    // Act
    panes.show("plot");
    // Assert
    expect(panes.tablist.querySelectorAll('[aria-selected="true"]').length).toBe(1);
  });

  it("rejects an unknown pane id", () => {
    // Arrange
    const panes = phone();
    // Act
    const shown = panes.show("nope");
    // Assert
    expect(shown).toBe(false);
  });

  it("emits stx-panes:change with the new pane", () => {
    // Arrange
    const panes = phone();
    let pane = "";
    panes.root.addEventListener(PANES_CHANGE, (event) => {
      pane = (event as CustomEvent<{ pane: string }>).detail.pane;
    });
    // Act
    panes.show("settings");
    // Assert
    expect(pane).toBe("settings");
  });

  it("switches on keyboard ArrowRight over the tablist", () => {
    // Arrange
    const panes = phone();
    const firstTab = panes.tablist.querySelector<HTMLElement>('[data-stx-pane-tab="data"]')!;
    firstTab.focus();
    // Act
    firstTab.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }));
    // Assert
    expect(panes.active).toBe("plot");
  });

  it("switches on keyboard ArrowLeft over the tablist", () => {
    // Arrange
    const panes = phone();
    panes.show("plot");
    const tab = panes.tablist.querySelector<HTMLElement>('[data-stx-pane-tab="plot"]')!;
    tab.focus();
    // Act
    tab.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowLeft", bubbles: true }));
    // Assert
    expect(panes.active).toBe("data");
  });
});

describe("persistence", () => {
  it("reopens on the pane last shown for the same app", () => {
    // Arrange
    const storage = new MemoryStorage();
    phone({ storage }).show("plot");
    // Act
    const reopened = phone({ storage });
    // Assert
    expect(reopened.active).toBe("plot");
  });

  it("keys the remembered pane by app", () => {
    // Arrange
    const storage = new MemoryStorage();
    phone({ storage }).show("plot");
    // Act
    const other = new Panes(root(), { app: "other", media: new FakeMedia(true), storage });
    // Assert
    expect(other.active).toBe("data");
  });

  it("ignores a remembered pane the page no longer has", () => {
    // Arrange
    const storage = new MemoryStorage();
    storage.setItem("stx-panes:demo", "gone");
    // Act
    const panes = phone({ storage });
    // Assert
    expect(panes.active).toBe("data");
  });
});

describe("breakpoint", () => {
  it("uses the single-pane layout when the phone query matches", () => {
    // Arrange
    const media = new FakeMedia(true);
    // Act
    const panes = new Panes(root(), { media, storage: new MemoryStorage() });
    // Assert
    expect(panes.root.classList.contains(SINGLE_CLASS)).toBe(true);
  });

  it("keeps the side-by-side layout on desktop", () => {
    // Arrange
    const media = new FakeMedia(false);
    // Act
    const panes = new Panes(root(), { media, storage: new MemoryStorage() });
    // Assert
    expect(panes.root.classList.contains(SINGLE_CLASS)).toBe(false);
  });

  it("leaves single-pane mode when the viewport widens", () => {
    // Arrange
    const media = new FakeMedia(true);
    const panes = new Panes(root(), { media, storage: new MemoryStorage() });
    // Act
    media.set(false);
    // Assert
    expect(panes.single).toBe(false);
  });
});

describe("swipe is disabled by default", () => {
  it("does not move to the next tab on a left swipe", () => {
    // Arrange
    const panes = phone();
    // Act
    swipe(panes.panes[0].element, -120);
    // Assert
    expect(panes.active).toBe("data");
  });

  it("does not move to the previous tab on a right swipe", () => {
    // Arrange
    const panes = phone();
    panes.show("settings");
    // Act
    swipe(panes.panes[2].element, 120);
    // Assert
    expect(panes.active).toBe("settings");
  });

  it("does not switch tabs when panning a PDF (canvas inside the pane)", () => {
    // Arrange — the card's core case: horizontal/diagonal pan in the PDF viewer.
    const panes = phone();
    const page = document.getElementById("page")!;
    // Act
    swipe(page, -150);
    swipe(page, -100, 60); // diagonal
    // Assert
    expect(panes.active).toBe("data");
  });

  it("does not switch tabs when panning a graph (svg)", () => {
    // Arrange
    const panes = phone();
    const svg = document.querySelector<HTMLElement>("#graph svg")!;
    // Act
    swipe(svg, -150);
    // Assert
    expect(panes.active).toBe("data");
  });

  it("does not switch tabs when swiping a table", () => {
    // Arrange
    const panes = phone();
    // Act
    swipe(document.getElementById("table")!, -150);
    // Assert
    expect(panes.active).toBe("data");
  });

  it("does not switch tabs on a vertical scroll gesture", () => {
    // Arrange
    const panes = phone();
    // Act — vertical swipe (dy dominates) must not switch.
    swipe(panes.panes[0].element, -20, 300);
    // Assert
    expect(panes.active).toBe("data");
  });

  it("does not switch tabs when scrolling a horizontal scroller", () => {
    // Arrange
    const panes = phone();
    const rail = document.getElementById("rail")!;
    Object.defineProperty(rail, "scrollWidth", { value: 2000 });
    Object.defineProperty(rail, "clientWidth", { value: 390 });
    // Act
    swipe(rail, -120);
    // Assert
    expect(panes.active).toBe("data");
  });

  it("does not switch tabs when swiping over a text field", () => {
    // Arrange
    const panes = phone();
    // Act
    swipe(document.getElementById("field")!, -120);
    // Assert
    expect(panes.active).toBe("data");
  });

  it("does not switch tabs on desktop", () => {
    // Arrange
    const panes = new Panes(root(), { media: new FakeMedia(false), storage: new MemoryStorage() });
    // Act
    swipe(panes.panes[0].element, -120);
    // Assert
    expect(panes.active).toBe("data");
  });

  it("switches with an explicit tab click even with swipe disabled", () => {
    // Arrange
    const panes = phone();
    const tab = panes.tablist.querySelector<HTMLElement>('[data-stx-pane-tab="plot"]')!;
    // Act
    tab.click();
    // Assert
    expect(panes.active).toBe("plot");
  });
});

describe("swipe is enabled by opt-in (swipeToSwitch: true)", () => {
  it("moves to the next tab on a left swipe", () => {
    // Arrange
    const panes = phone({ swipeToSwitch: true });
    // Act
    swipe(panes.panes[0].element, -120);
    // Assert
    expect(panes.active).toBe("plot");
  });

  it("moves to the previous tab on a right swipe", () => {
    // Arrange
    const panes = phone({ swipeToSwitch: true });
    panes.show("settings");
    // Act
    swipe(panes.panes[2].element, 120);
    // Assert
    expect(panes.active).toBe("plot");
  });

  it("ignores a mostly vertical gesture even when opted in", () => {
    // Arrange
    const panes = phone({ swipeToSwitch: true });
    // Act
    swipe(panes.panes[0].element, -80, 200);
    // Assert
    expect(panes.active).toBe("data");
  });

  it("does not swipe panes from inside a horizontal scroller (opted in)", () => {
    // Arrange
    const panes = phone({ swipeToSwitch: true });
    const rail = document.getElementById("rail")!;
    Object.defineProperty(rail, "scrollWidth", { value: 2000 });
    Object.defineProperty(rail, "clientWidth", { value: 390 });
    // Act
    swipe(rail, -120);
    // Assert
    expect(panes.active).toBe("data");
  });

  it("does not swipe panes from a text field (opted in)", () => {
    // Arrange
    const panes = phone({ swipeToSwitch: true });
    // Act
    swipe(document.getElementById("field")!, -120);
    // Assert
    expect(panes.active).toBe("data");
  });

  it("does not switch when panning a PDF even when opted in", () => {
    // Arrange — the card's hard requirement: never from PDF/canvas elements.
    const panes = phone({ swipeToSwitch: true });
    const page = document.getElementById("page")!;
    // Act
    swipe(page, -150);
    // Assert
    expect(panes.active).toBe("data");
  });

  it("does not switch when panning a graph (svg) even when opted in", () => {
    // Arrange
    const panes = phone({ swipeToSwitch: true });
    const svg = document.querySelector<HTMLElement>("#graph svg")!;
    // Act
    swipe(svg, -150);
    // Assert
    expect(panes.active).toBe("data");
  });

  it("does not switch when swiping a table even when opted in", () => {
    // Arrange
    const panes = phone({ swipeToSwitch: true });
    // Act
    swipe(document.getElementById("table")!, -150);
    // Assert
    expect(panes.active).toBe("data");
  });
});
