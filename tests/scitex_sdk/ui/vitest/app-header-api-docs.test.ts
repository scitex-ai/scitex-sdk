import { beforeEach, describe, expect, it } from "vitest";
import {
  AppHeader, API_DOCS_URL_ATTRIBUTE, resolveApiDocsUrl,
} from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/ts/app/app-header";

beforeEach(() => { document.body.innerHTML = ""; document.body.removeAttribute(API_DOCS_URL_ATTRIBUTE); });

describe("Host-supplied API documentation action", () => {
  it("uses the shared action slot and preserves other controls on update/removal", () => {
    const root = document.createElement("div");
    document.body.append(root);
    root.setAttribute(API_DOCS_URL_ATTRIBUTE, "/docs?package=first");
    const action = document.createElement("button");
    action.textContent = "Existing action";
    const header = new AppHeader({ container: root, title: "Example", version: "1.0", actions: [action] });
    const picker = document.createElement("button");
    header.projectSlot?.append(picker);
    const link = root.querySelector<HTMLAnchorElement>('[data-stx-action="api-docs"]')!;
    expect([link.tagName, link.getAttribute("href"), link.getAttribute("aria-label")])
      .toEqual(["A", "/docs?package=first", "API documentation"]);
    header.setApiDocsUrl("https://docs.example.test/api", "API の説明");
    expect(root.querySelector('[data-stx-action="api-docs"]')).toBe(link);
    expect([link.getAttribute("href"), link.title]).toEqual(["https://docs.example.test/api", "API の説明"]);
    header.setApiDocsUrl(null);
    expect(root.querySelector('[data-stx-action="api-docs"]')).toBeNull();
    expect([header.actionsEl.contains(action), header.projectSlot?.contains(picker), header.versionEl.textContent])
      .toEqual([true, true, "v1.0"]);
  });

  it("inherits the nearest host mount declaration and allows explicit opt-out", () => {
    const host = document.createElement("main");
    host.setAttribute(API_DOCS_URL_ATTRIBUTE, "/api-docs?package=host");
    host.innerHTML = "<section><div></div></section>";
    document.body.append(host);
    const root = host.querySelector("div")!;
    expect(resolveApiDocsUrl(root)).toBe("/api-docs?package=host");
    expect(resolveApiDocsUrl(root, "")).toBeNull();
    expect(resolveApiDocsUrl(root, null)).toBeNull();
    expect(resolveApiDocsUrl(root, "/different-host-route")).toBe("/different-host-route");
  });

  it.each(["javascript:alert(1)", "data:text/html,unsafe", "//outside.test/docs", "/\\outside.test", "/docs\nunsafe", "https://user:password@example.test/docs"])(
    "refuses unsafe navigation %s", (url) => {
      const root = document.createElement("div");
      const header = new AppHeader({ container: root, apiDocsUrl: url });
      expect(header.actionsEl.querySelector("a")).toBeNull();
    },
  );

  it("renders no action when a standalone host supplies no documentation URL", () => {
    const root = document.createElement("div");
    const header = new AppHeader({ container: root });
    expect(header.actionsEl.children.length).toBe(0);
  });
});

describe("Workspace ownership boundaries", () => {
  it("uses the closest owner and an explicit empty region suppresses a stale body owner", () => {
    document.body.setAttribute(API_DOCS_URL_ATTRIBUTE,"/docs?package=old");
    document.body.innerHTML='<main data-stx-api-docs-url="/docs?package=new"><div id="mount"></div></main>';
    const root=document.querySelector<HTMLElement>('#mount')!;
    expect(resolveApiDocsUrl(root)).toBe('/docs?package=new');
    root.parentElement!.setAttribute(API_DOCS_URL_ATTRIBUTE,'');
    expect(resolveApiDocsUrl(root)).toBeNull();
    document.body.removeAttribute(API_DOCS_URL_ATTRIBUTE);
  });
});
