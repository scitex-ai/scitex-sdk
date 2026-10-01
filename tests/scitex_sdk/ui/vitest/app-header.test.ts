/**
 * AppHeader: the canonical app header row — slot order, title resolution, and
 * the scitex-app version contract. `npx vitest run`
 *
 * jsdom has no layout engine, so NOTHING here claims a pixel measurement: the
 * 390px behaviour is guarded statically in
 * tests/develop/test_app_header_contract.py and measured in a real browser on
 * the card. What jsdom CAN prove is what the component renders and which value
 * it resolves, and that is all this file asserts.
 */

import { beforeEach, describe, expect, it } from "vitest";

import {
  AppHeader,
  APP_HEADER_COMMAND,
  APP_TITLE_ATTRIBUTE,
  APP_VERSION_ATTRIBUTE,
  HEADER_ATTRIBUTE,
  SHELL_PROPS_META_NAME,
  readShellProps,
  resolveAppTitle,
  resolveAppVersion,
} from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/ts/app/app-header";
import { mountAppHeader } from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/ts/app/app-header/mount";

function root(): HTMLElement {
  const el = document.createElement("div");
  document.body.appendChild(el);
  return el;
}

beforeEach(() => {
  document.body.innerHTML = "";
  document.documentElement.removeAttribute(APP_VERSION_ATTRIBUTE);
  document.head
    .querySelectorAll(`meta[name="${SHELL_PROPS_META_NAME}"]`)
    .forEach((meta) => meta.remove());
});

/** Put a shell-props payload in the page exactly as the host emits it. */
function withShellProps(props: Record<string, unknown>): void {
  const meta = document.createElement("meta");
  meta.setAttribute("name", SHELL_PROPS_META_NAME);
  meta.setAttribute("content", JSON.stringify(props));
  document.head.appendChild(meta);
}

const PROJECT_PROPS = {
  app: "figrecipe",
  title: "FigRecipe",
  version: "0.22.0",
  scope: "project",
  project: { url: "/api/projects", current: "p1", navigate: true },
};

const USER_PROPS = {
  app: "stats",
  title: "Stats",
  version: "1.0.0",
  scope: "user",
};

describe("AppHeader — the canonical row", () => {
  it("renders the four slots in the canonical order", () => {
    // Arrange
    const container = root();
    // Act
    const header = new AppHeader({ container, title: "Writer" });
    // Assert
    const classes = Array.from(header.headerEl.children).map((c) => c.className);
    expect(classes).toEqual([
      "stx-app-header__title",
      "stx-app-header__version",
      "stx-app-header__slot--project-selector",
      "stx-app-header__actions",
    ]);
  });

  it("renders a <header> with the canonical block class", () => {
    // Arrange
    const container = root();
    // Act
    const header = new AppHeader({ container, title: "Writer" });
    // Assert
    expect(header.headerEl.tagName).toBe("HEADER");
    expect(header.headerEl.classList.contains("stx-app-header")).toBe(true);
    expect(container.querySelector("header.stx-app-header")).toBe(header.headerEl);
  });

  it("keeps the title a span, so a mounted leaf adds no second heading", () => {
    // Arrange
    const container = root();
    // Act
    new AppHeader({ container, title: "Writer" });
    // Assert — a heading here would collide with the leaf's own document outline
    expect(container.querySelector("h1, h2, h3")).toBeNull();
    expect(container.querySelector(".stx-app-header__title")?.tagName).toBe("SPAN");
  });
});

describe("title resolution", () => {
  it("prefers the explicit title over the mount attribute", () => {
    // Arrange
    const container = root();
    container.setAttribute(APP_TITLE_ATTRIBUTE, "FromAttribute");
    // Act
    const header = new AppHeader({ container, title: "Explicit" });
    // Assert
    expect(header.titleEl.textContent).toBe("Explicit");
  });

  it("falls back to data-app-title on the mount root", () => {
    // Arrange
    const container = root();
    container.setAttribute(APP_TITLE_ATTRIBUTE, "FigRecipe");
    // Act
    const header = new AppHeader({ container });
    // Assert
    expect(header.titleEl.textContent).toBe("FigRecipe");
  });

  it("falls back to an ancestor's data-app-title (hub-mount shape)", () => {
    // Arrange
    const outer = root();
    outer.setAttribute(APP_TITLE_ATTRIBUTE, "Stats");
    const inner = document.createElement("div");
    outer.appendChild(inner);
    // Act
    const header = new AppHeader({ container: inner });
    // Assert
    expect(header.titleEl.textContent).toBe("Stats");
  });

  it("returns an empty string rather than a placeholder when nothing declares a title", () => {
    // Arrange
    const container = root();
    // Act
    new AppHeader({ container });
    // Assert
    expect(container.querySelector(".stx-app-header__title")?.textContent).toBe("");
  });

  it("setTitle updates the rendered title", () => {
    // Arrange
    const container = root();
    const header = new AppHeader({ container, title: "Writer" });
    // Act
    header.setTitle("Writer (JA)");
    // Assert
    expect(header.titleEl.textContent).toBe("Writer (JA)");
  });
});

describe("version resolution — the scitex-app mount contract", () => {
  it("renders the explicit version with the ecosystem prefix", () => {
    // Arrange
    const container = root();
    // Act
    const header = new AppHeader({ container, title: "X", version: "1.4.0" });
    // Assert
    expect(header.versionEl.textContent).toBe("v1.4.0");
    expect(header.versionEl.hidden).toBe(false);
  });

  it("reads the leaf's own data-app-version stamp", () => {
    // Arrange
    const container = root();
    container.setAttribute(APP_VERSION_ATTRIBUTE, "2.0.1");
    // Act
    const header = new AppHeader({ container, title: "X" });
    // Assert
    expect(header.versionEl.textContent).toBe("v2.0.1");
  });

  it("prefers the explicit version over the stamp", () => {
    // Arrange
    const container = root();
    container.setAttribute(APP_VERSION_ATTRIBUTE, "2.0.1");
    // Act
    const header = new AppHeader({ container, title: "X", version: "9.9.9" });
    // Assert
    expect(header.versionEl.textContent).toBe("v9.9.9");
  });

  it("falls back to an ancestor stamp before the document stamp", () => {
    // Arrange
    document.documentElement.setAttribute(APP_VERSION_ATTRIBUTE, "0.0.1");
    const outer = root();
    outer.setAttribute(APP_VERSION_ATTRIBUTE, "0.22.0");
    const inner = document.createElement("div");
    outer.appendChild(inner);
    // Act
    const header = new AppHeader({ container: inner, title: "X" });
    // Assert
    expect(header.versionEl.textContent).toBe("v0.22.0");
  });

  it("falls back to the document stamp when nothing nearer carries one", () => {
    // Arrange
    document.documentElement.setAttribute(APP_VERSION_ATTRIBUTE, "0.0.1");
    const container = root();
    // Act
    const header = new AppHeader({ container, title: "X" });
    // Assert
    expect(header.versionEl.textContent).toBe("v0.0.1");
  });

  it("hides the badge and renders NO placeholder when the version is unknown", () => {
    // Arrange
    const container = root();
    // Act
    const header = new AppHeader({ container, title: "X" });
    // Assert — absent-looking, not a plausible wrong value
    expect(header.versionEl.hidden).toBe(true);
    expect(header.versionEl.textContent).toBe("");
  });

  it("reveals the badge later without rebuilding the row", () => {
    // Arrange
    const container = root();
    const header = new AppHeader({ container, title: "X" });
    const before = header.headerEl.children.length;
    // Act
    header.setVersion("3.1.4");
    // Assert
    expect(header.versionEl.textContent).toBe("v3.1.4");
    expect(header.versionEl.hidden).toBe(false);
    expect(header.headerEl.children.length).toBe(before);
  });

  it("setVersion(null) hides it again rather than emptying the text only", () => {
    // Arrange
    const container = root();
    const header = new AppHeader({ container, title: "X", version: "1.0.0" });
    // Act
    header.setVersion(null);
    // Assert
    expect(header.versionEl.hidden).toBe(true);
    expect(header.versionEl.textContent).toBe("");
  });
});

describe("the resolver functions, in isolation", () => {
  it("resolveAppVersion returns null when nothing declares a version", () => {
    // Arrange
    const container = root();
    // Act / Assert
    expect(resolveAppVersion(container)).toBeNull();
  });

  it("resolveAppTitle returns an empty string when nothing declares a title", () => {
    // Arrange
    const container = root();
    // Act / Assert
    expect(resolveAppTitle(container)).toBe("");
  });

  it("resolveAppVersion treats whitespace-only as unknown", () => {
    // Arrange
    const container = root();
    container.setAttribute(APP_VERSION_ATTRIBUTE, "   ");
    // Act / Assert
    expect(resolveAppVersion(container)).toBeNull();
  });
});

describe("actions and the project slot", () => {
  it("appends actions AFTER the project slot in the DOM — the component's half of the row order", () => {
    // THE OTHER HALF IS CSS, AND IT IS NOT VISIBLE HERE. jsdom does not lay out,
    // so the `order` declarations in the stylesheets decide which element of this
    // row renders where, and this DOM order cannot see them. That gap is how the
    // header shipped rendering [title][version][actions][selector] for every app
    // that declared actions: this test was green the whole time, because its old
    // name ("appends actions AFTER the project slot, which is what keeps the
    // selector left") stated a CAUSAL claim its assertion had no way to check.
    // The CSS half is asserted as a RELATION between the two slots' `order`
    // values in tests/develop/test_app_header_contract.py.
    // Arrange
    const container = root();
    const header = new AppHeader({ container, title: "X" });
    const action = document.createElement("button");
    // Act
    header.addAction(action);
    // Assert
    const children = Array.from(header.headerEl.children);
    expect(header.projectSlot).not.toBeNull();
    expect(children.indexOf(header.actionsEl)).toBeGreaterThan(
      children.indexOf(header.projectSlot as HTMLElement),
    );
    expect(header.actionsEl.contains(action)).toBe(true);
  });

  it("takes initial actions in order", () => {
    // Arrange
    const container = root();
    const a = document.createElement("button");
    const b = document.createElement("button");
    // Act
    const header = new AppHeader({ container, title: "X", actions: [a, b] });
    // Assert
    expect(Array.from(header.actionsEl.children)).toEqual([a, b]);
  });

  it("exposes the canonical project slot for the app to mount its selector into", () => {
    // Arrange
    const container = root();
    const header = new AppHeader({ container, title: "X" });
    const selector = document.createElement("div");
    // Act
    header.projectSlot?.appendChild(selector);
    // Assert
    expect(
      container.querySelector(".stx-app-header__slot--project-selector > div"),
    ).toBe(selector);
  });

  it("destroy() removes the header row", () => {
    // Arrange
    const container = root();
    const header = new AppHeader({ container, title: "X" });
    // Act
    header.destroy();
    // Assert
    expect(container.querySelector(".stx-app-header")).toBeNull();
  });
});

describe("mountAppHeader — the no-bundler path", () => {
  it("mounts each declared root exactly once", () => {
    // Arrange
    const container = root();
    container.setAttribute(HEADER_ATTRIBUTE, "");
    container.setAttribute(APP_TITLE_ATTRIBUTE, "Writer");
    container.setAttribute(APP_VERSION_ATTRIBUTE, "1.2.3");
    // Act
    const first = mountAppHeader(document);
    const second = mountAppHeader(document);
    // Assert
    expect(first.length).toBe(1);
    expect(second.length).toBe(0);
    expect(container.querySelectorAll(".stx-app-header").length).toBe(1);
    expect(container.querySelector(".stx-app-header__title")?.textContent).toBe(
      "Writer",
    );
    expect(container.querySelector(".stx-app-header__version")?.textContent).toBe(
      "v1.2.3",
    );
  });

  it("does not touch elements that are not declared as header roots", () => {
    // Arrange
    const container = root();
    // Act
    const mounted = mountAppHeader(document);
    // Assert
    expect(mounted).toEqual([]);
    expect(container.querySelector(".stx-app-header")).toBeNull();
  });
});

describe("the scitex-app shell contract (reader half)", () => {
  it("mirrors the meta name scitex-app writes — byte for byte", () => {
    // Arrange / Act / Assert — a reader looking for a name nobody writes
    // reaches nobody (the stx-mount history).
    expect(SHELL_PROPS_META_NAME).toBe("stx-app-shell");
  });

  it("reads the payload the host emits", () => {
    // Arrange
    withShellProps(PROJECT_PROPS);
    // Act
    const props = readShellProps(document);
    // Assert
    expect(props?.title).toBe("FigRecipe");
    expect(props?.version).toBe("0.22.0");
    expect(props?.scope).toBe("project");
  });

  it("returns null when the page carries no payload at all", () => {
    // Arrange / Act / Assert — absence is not an error
    expect(readShellProps(document)).toBeNull();
  });

  it("refuses to render a header from an unreadable payload", () => {
    // Arrange
    const meta = document.createElement("meta");
    meta.setAttribute("name", SHELL_PROPS_META_NAME);
    meta.setAttribute("content", "{not json");
    document.head.appendChild(meta);
    // Act / Assert — a silently action-less header looks exactly like an app
    // that declares no actions
    expect(() => readShellProps(document)).toThrow(/unreadable payload/);
  });

  it("takes the title and version from the payload", () => {
    // Arrange
    withShellProps(PROJECT_PROPS);
    // Act
    const header = new AppHeader({ container: root() });
    // Assert
    expect(header.titleEl.textContent).toBe("FigRecipe");
    expect(header.versionEl.textContent).toBe("v0.22.0");
  });

  it("prefers the payload over the mount attributes, and an explicit argument over both", () => {
    // Arrange
    withShellProps(PROJECT_PROPS);
    const container = root();
    container.setAttribute(APP_TITLE_ATTRIBUTE, "FromAttribute");
    container.setAttribute(APP_VERSION_ATTRIBUTE, "9.9.9");
    // Act
    const payloadDriven = new AppHeader({ container });
    const explicit = new AppHeader({
      container,
      title: "Explicit",
      version: "1.0.0",
    });
    // Assert
    expect(payloadDriven.titleEl.textContent).toBe("FigRecipe");
    expect(payloadDriven.versionEl.textContent).toBe("v0.22.0");
    expect(explicit.titleEl.textContent).toBe("Explicit");
    expect(explicit.versionEl.textContent).toBe("v1.0.0");
  });

  it("renders the project slot for a project-scoped app with a provider", () => {
    // Arrange
    withShellProps(PROJECT_PROPS);
    // Act
    const header = new AppHeader({ container: root() });
    // Assert
    expect(header.projectSlot).not.toBeNull();
    expect(header.shellProps?.project?.url).toBe("/api/projects");
  });

  it("refuses to render the project slot for a user-scoped app (scitex-app refuses to emit the provider)", () => {
    // Arrange
    withShellProps(USER_PROPS);
    // Act
    const header = new AppHeader({ container: root() });
    // Assert — the global header must never force a selector on a user-scoped app
    expect(header.projectSlot).toBeNull();
    expect(
      header.headerEl.querySelector(".stx-app-header__slot--project-selector"),
    ).toBeNull();
  });

  it("still renders the slot for an app that drives the component directly", () => {
    // Arrange — no payload on the page at all
    // Act
    const header = new AppHeader({ container: root(), title: "FigRecipe" });
    // Assert
    expect(header.projectSlot).not.toBeNull();
  });

  it("renders payload actions in order, as a command button or an href link", () => {
    // Arrange
    withShellProps({
      ...PROJECT_PROPS,
      actions: [
        { id: "share", label: "Share", command: "figrecipe.share", order: 2 },
        { id: "docs", label: "Docs", href: "/docs", order: 1 },
      ],
    });
    // Act
    const header = new AppHeader({ container: root() });
    // Assert
    const controls = Array.from(header.actionsEl.children);
    expect(controls.map((c) => c.textContent)).toEqual(["Docs", "Share"]);
    expect(controls[0].tagName).toBe("A");
    expect((controls[0] as HTMLAnchorElement).getAttribute("href")).toBe("/docs");
    expect(controls[1].tagName).toBe("BUTTON");
    expect(
      (controls[1] as HTMLElement).getAttribute("data-stx-command"),
    ).toBe("figrecipe.share");
  });

  it("emits ONE command id that keyboard, touch and mouse all resolve", () => {
    // Arrange
    withShellProps({
      ...PROJECT_PROPS,
      actions: [{ id: "share", label: "Share", command: "figrecipe.share" }],
    });
    const container = root();
    const header = new AppHeader({ container });
    const seen: string[] = [];
    container.addEventListener(APP_HEADER_COMMAND, (event) => {
      seen.push((event as CustomEvent<{ command: string }>).detail.command);
    });
    // Act
    (header.actionsEl.firstElementChild as HTMLButtonElement).click();
    // Assert
    expect(seen).toEqual(["figrecipe.share"]);
  });

  it("refuses to render an action that names neither a command nor an href", () => {
    // Arrange
    withShellProps({
      ...PROJECT_PROPS,
      actions: [{ id: "dead", label: "Nothing" }],
    });
    // Act / Assert — a control that does nothing renders like a working one
    expect(() => new AppHeader({ container: root() })).toThrow(
      /neither a command nor an href/,
    );
  });

  it("mountAppHeader renders the header from the page's payload", () => {
    // Arrange
    withShellProps({
      ...USER_PROPS,
      actions: [{ id: "help", label: "Help", command: "stats.help" }],
    });
    const container = root();
    container.setAttribute(HEADER_ATTRIBUTE, "");
    // Act
    const mounted = mountAppHeader(document);
    // Assert
    expect(mounted.length).toBe(1);
    expect(container.querySelector(".stx-app-header__title")?.textContent).toBe(
      "Stats",
    );
    expect(container.querySelector(".stx-app-header__action")?.textContent).toBe(
      "Help",
    );
  });
});
