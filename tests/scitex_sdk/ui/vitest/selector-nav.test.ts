/**
 * SelectorNav: ONE tree, two presentations — tab strip on desktop, cascading
 * dropdown on mobile — with the keyboard model each shape needs.
 * `npx vitest run`
 *
 * The switch is at the shared 600px phone boundary (the same value
 * project-selector.css and app-header.css use), so this file stubs matchMedia
 * rather than trusting a jsdom default: which shape renders IS the contract.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  SelectorNav,
  SELECTOR_NAV_ATTRIBUTE,
  SELECTOR_NAV_CHANGE,
} from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/ts/app/selector-nav";
import { mountSelectorNavs } from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/ts/app/selector-nav/mount";

const TREE = [
  { id: "files", label: "Files", icon: "icon-folder" },
  {
    id: "figure",
    label: "Figure",
    children: [
      { id: "layout", label: "Layout" },
      {
        id: "style",
        label: "Style",
        children: [{ id: "colours", label: "Colours" }],
      },
    ],
  },
];

function container(): HTMLElement {
  const el = document.createElement("div");
  document.body.appendChild(el);
  return el;
}

/** Stub the media query so the shape is decided by the test, not by jsdom. */
function stubViewport(isPhone: boolean): void {
  vi.stubGlobal(
    "matchMedia",
    (query: string) =>
      ({
        matches: isPhone && query.includes("max-width"),
        media: query,
        addEventListener: () => {},
        removeEventListener: () => {},
      }) as unknown as MediaQueryList,
  );
}

beforeEach(() => {
  document.body.innerHTML = "";
  vi.unstubAllGlobals();
});

describe("SelectorNav — the tab shape (desktop)", () => {
  it("renders one tab per ROOT node, and only the roots", () => {
    // Arrange
    stubViewport(false);
    // Act
    const nav = new SelectorNav({ container: container(), items: TREE });
    // Assert — children are the cascade's business, not the strip's.
    const labels = Array.from(nav.itemsEl.querySelectorAll(".stx-app-selector-nav__item")).map(
      (n) => n.textContent,
    );
    expect(labels).toEqual(["Files", "Figure"]);
  });

  it("declares itself a tablist and each node a tab", () => {
    // Arrange
    stubViewport(false);
    // Act
    const nav = new SelectorNav({ container: container(), items: TREE });
    // Assert
    expect(nav.itemsEl.getAttribute("role")).toBe("tablist");
  });

  it("marks the current ROOT active when the selection is deep", () => {
    // Arrange
    stubViewport(false);
    // Act
    const nav = new SelectorNav({ container: container(), items: TREE, current: "colours" });
    // Assert — the strip shows WHICH tab owns the selection...
    const active = nav.itemsEl.querySelector(".stx-app-selector-nav__item.active");
    expect(active?.querySelector(".stx-app-selector-nav__label")?.textContent).toBe("Figure");
  });

  it("puts the hidden path on the active tab, because depth is invisible in a strip", () => {
    // Arrange
    stubViewport(false);
    // Act
    const nav = new SelectorNav({ container: container(), items: TREE, current: "colours" });
    // Assert
    expect(
      nav.itemsEl.querySelector<HTMLElement>(".stx-app-selector-nav__item.active")?.title,
    ).toBe("Figure / Style / Colours");
  });

  it("reports a selection through the event, the callback and one id", () => {
    // Arrange
    stubViewport(false);
    const host = container();
    const seen: string[] = [];
    const nav = new SelectorNav({ container: host, items: TREE });
    host.addEventListener(SELECTOR_NAV_CHANGE, (e) =>
      seen.push((e as CustomEvent<{ id: string }>).detail.id),
    );
    // Act
    (nav.itemsEl.querySelectorAll<HTMLButtonElement>(".stx-app-selector-nav__item")[0]).click();
    // Assert
    expect(seen).toEqual(["files"]);
  });

  it("refuses an id that is not in the tree, rather than showing a stale selection", () => {
    // Arrange
    stubViewport(false);
    const nav = new SelectorNav({ container: container(), items: TREE });
    // Act / Assert
    expect(() => nav.setCurrent("nope")).toThrow(/no node with that id/);
  });

  it("resolves an id to its nearest-first path and its root", () => {
    // Arrange
    stubViewport(false);
    const nav = new SelectorNav({ container: container(), items: TREE });
    // Act
    const resolved = nav.resolve("colours");
    // Assert
    expect(resolved?.path.map((n) => n.id)).toEqual(["colours", "style", "figure"]);
  });

  it("assumes the wide shape when matchMedia is unavailable", () => {
    // Arrange — an ancient browser or a jsdom without the stub: showing a strip
    // is the safe default, because a cascade needs height it may not have.
    // Act
    const nav = new SelectorNav({ container: container(), items: TREE });
    // Assert
    expect(nav.isTabs()).toBe(true);
  });
});

describe("SelectorNav — the cascade shape (mobile)", () => {
  it("switches shape at the shared 600px boundary", () => {
    // Arrange
    stubViewport(true);
    // Act
    const nav = new SelectorNav({ container: container(), items: TREE });
    // Assert
    expect(nav.isTabs()).toBe(false);
  });

  it("annotates the cascade modifier class so the CSS can shape it", () => {
    // Arrange
    stubViewport(true);
    // Act
    const nav = new SelectorNav({ container: container(), items: TREE });
    // Assert
    expect(nav.rootEl.classList.contains("stx-app-selector-nav--cascade")).toBe(true);
  });

  it("descending is not a terminal selection: it opens the next level", () => {
    // Arrange
    stubViewport(true);
    const nav = new SelectorNav({ container: container(), items: TREE });
    // Act
    nav.setCurrent(null);
    (nav.itemsEl.querySelectorAll<HTMLButtonElement>(".stx-app-selector-nav__item")[1]).click();
    // Assert — level two is now rendered.
    expect(nav.itemsEl.querySelectorAll(".stx-app-selector-nav__level").length).toBe(2);
  });

  it("expands the level that CONTAINS the current selection when state is restored", () => {
    // Arrange
    stubViewport(true);
    // Act
    const nav = new SelectorNav({ container: container(), items: TREE, current: "colours" });
    // Assert — all three levels, so the deep selection is visible, not buried.
    expect(nav.itemsEl.querySelectorAll(".stx-app-selector-nav__level").length).toBe(3);
  });

  it("uses the horizontal axis for cascade navigation, not the strip's vertical one", () => {
    // Arrange
    stubViewport(true);
    const nav = new SelectorNav({ container: container(), items: TREE });
    const first = nav.itemsEl.querySelector<HTMLButtonElement>(".stx-app-selector-nav__item");
    // Act
    first?.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }));
    // Assert — focus moved, and the roving tabindex followed it.
    expect(document.activeElement?.textContent).toBe("Figure");
  });

  it("uses the vertical axis for the strip, so the two shapes are not conflated", () => {
    // Arrange
    stubViewport(false);
    const nav = new SelectorNav({ container: container(), items: TREE });
    const first = nav.itemsEl.querySelector<HTMLButtonElement>(".stx-app-selector-nav__item");
    // Act
    first?.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }));
    // Assert
    expect(document.activeElement?.textContent).toBe("Figure");
  });

  it("renders every node as a real button, so touch, mouse and keyboard share one id", () => {
    // Arrange — a deep selection opens the level that contains it, so the
    // grandchild is rendered too: the cascade's whole point is that the
    // selected node is reachable without re-navigating.
    stubViewport(true);
    // Act
    const nav = new SelectorNav({ container: container(), items: TREE, current: "style" });
    // Assert
    const ids = Array.from(
      nav.itemsEl.querySelectorAll<HTMLElement>(".stx-app-selector-nav__item"),
    ).map((n) => n.getAttribute("data-stx-selector-id"));
    expect(ids).toEqual(["files", "figure", "layout", "style", "colours"]);
  });
});

describe("mountSelectorNavs — the no-bundler path", () => {
  it("mounts a declared root and reads its tree", () => {
    // Arrange
    stubViewport(false);
    const host = container();
    host.setAttribute(SELECTOR_NAV_ATTRIBUTE, "");
    host.setAttribute("data-stx-items", JSON.stringify(TREE));
    // Act
    const mounted = mountSelectorNavs(document);
    // Assert
    expect(mounted.length).toBe(1);
  });

  it("mounts each declared root exactly once", () => {
    // Arrange
    stubViewport(false);
    const host = container();
    host.setAttribute(SELECTOR_NAV_ATTRIBUTE, "");
    host.setAttribute("data-stx-items", JSON.stringify(TREE));
    const first = mountSelectorNavs(document);
    // Act
    const second = mountSelectorNavs(document);
    // Assert
    expect([first.length, second.length]).toEqual([1, 0]);
  });

  it("refuses an unreadable items payload instead of rendering an empty selector", () => {
    // Arrange
    stubViewport(false);
    const host = container();
    host.setAttribute(SELECTOR_NAV_ATTRIBUTE, "");
    host.setAttribute("data-stx-items", "{not json");
    // Act / Assert — an empty strip looks like an app with one section.
    expect(() => mountSelectorNavs(document)).toThrow(/unreadable/);
  });
});
