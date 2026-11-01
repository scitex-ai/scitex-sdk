import { act, createElement, StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { describe, expect, it } from "vitest";
import { AppHeader } from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/react/app/app-header";

(globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;

describe("React canonical header binding", () => {
  it("keeps one SDK row and picker through StrictMode, text updates and unmount", () => {
    const container = document.createElement("div");
    document.body.append(container);
    const root = createRoot(container);
    const render = (title: string, version: string) => act(() => root.render(
      createElement(StrictMode, null, createElement(AppHeader, {
        title, version,
        projectSelector: createElement("button", { id: "picker" }, "Project"),
        actions: createElement("button", { id: "action" }, "Action"),
      })),
    ));
    render("Figure", "1.0");
    expect(container.querySelectorAll("header.stx-app-header")).toHaveLength(1);
    const picker = container.querySelector("#picker");
    expect(picker?.parentElement?.className).toBe("stx-app-header__slot--project-selector");
    expect(container.querySelector("#action")?.parentElement?.className).toBe("stx-app-header__actions");
    render("Updated", "2.0");
    expect(container.querySelector("#picker")).toBe(picker);
    expect(container.querySelector(".stx-app-header__title")?.textContent).toBe("Updated");
    expect(container.querySelector(".stx-app-header__version")?.textContent).toBe("v2.0");
    expect(container.querySelectorAll("#picker")).toHaveLength(1);
    act(() => root.unmount());
    expect(container.children).toHaveLength(0);
    container.remove();
  });
  it("does not create a project slot for a user-scoped render", () => {
    const container = document.createElement("div");
    const root = createRoot(container);
    act(() => root.render(createElement(AppHeader, { title: "Journal" })));
    expect(container.querySelector(".stx-app-header__slot--project-selector")).toBeNull();
    act(() => root.unmount());
  });
});
