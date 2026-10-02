/** Canonical picker scope/command contract through the real component and provider ports. */
import { afterEach, describe, expect, it } from "vitest";
import * as sourcePicker from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/ts/app/project-selector";
import * as shippedPicker from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/js/app/project-selector.js";
import { CommandRegistry } from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/ts/shell/keymap/_registry";
import { createServer } from "node:http";
import { mountProjectSelectorByScope as sourceScopeMount } from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/ts/shell/app-scope-selector";
import { mountProjectSelectorByScope as shippedScopeMount } from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/js/shell/app-scope-selector.js";
import type { ProjectProvider } from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/ts/app/project-selector/provider";

const projects = [{ id: "a", name: "Authorized A" }, { id: "b", name: "Authorized B" }];
const shipped = process.env.STX_PICKER_TEST_RUNTIME === "shipped";
const { ProjectSelector, PROJECT_SELECTOR_CHANGE, projectNavigationUrl, mountProjectPickers, httpProjectProvider } = shipped ? shippedPicker : sourcePicker;
const mountProjectSelectorByScope = shipped ? shippedScopeMount : sourceScopeMount;
const instances: sourcePicker.ProjectSelector[] = [];
function fixture(options: Record<string, unknown> = {}, persist: (choice: unknown) => Promise<void> = async () => {}) {
  const container = document.createElement("div");
  document.body.append(container);
  const saved: unknown[] = [];
  const events: unknown[] = [];
  const provider: ProjectProvider = {
    listProjects: async () => ({ projects, current: "a" }),
    rememberScope: async (choice) => { saved.push(choice); await persist(choice); },
  };
  container.addEventListener(PROJECT_SELECTOR_CHANGE, (event) => events.push((event as CustomEvent).detail));
  const selector = new ProjectSelector({ container, provider, ...options });
  instances.push(selector);
  return { selector, container, saved, events };
}
function options(container: HTMLElement): string[] {
  return Array.from(container.querySelectorAll('[role="option"]')).map((row) => row.textContent ?? "");
}
async function settle(): Promise<void> { await Promise.resolve(); await Promise.resolve(); }
afterEach(() => { instances.splice(0).forEach((selector) => selector.destroy()); document.body.innerHTML = ""; document.documentElement.lang = "en"; });

describe("canonical user capability", () => {
  it.each([undefined, false, null, "true", 1])("suppresses All without strict capability %s", async (capability) => {
    // Arrange
    const f = fixture({ allowUserScope: capability });
    // Act
    await f.selector.ready;
    // Assert
    expect(options(f.container)).toEqual(["Authorized A", "Authorized B"]);
  });

  it("requires a scoped provider in addition to capability", async () => {
    // Arrange
    const f = fixture({ allowUserScope: true, provider: { listProjects: async () => ({ projects, current: "a" }) } });
    // Act
    await f.selector.ready;
    // Assert
    expect(options(f.container)).toEqual(["Authorized A", "Authorized B"]);
  });

  it("disabled capability refuses user commands and keeps the legacy DOM shape", async () => {
    // Arrange
    const f = fixture({ allowUserScope: false });
    await f.selector.ready;
    // Act
    const accepted = f.selector.commands.run(f.selector.selectCommandId, { via: "agent" }, { scope: "user", id: null });
    // Assert
    expect([accepted, f.events, f.saved, f.container.children.length]).toEqual([false, [], [], 2]);
  });

  it("explicit false suppresses a provider-advertised user capability", async () => {
    // Arrange
    const f = fixture({ allowUserScope: false, provider: { listProjects: async () => ({ projects, allow_user_scope: true }), rememberScope: async () => {} } });
    // Act
    await f.selector.ready;
    // Assert
    expect(options(f.container)).toEqual(["Authorized A", "Authorized B"]);
  });

  it("provider capability is strict and still requires its scoped port", async () => {
    // Arrange
    const f = fixture({ provider: { listProjects: async () => ({ projects, allow_user_scope: "true" }), rememberScope: async () => {} } });
    // Act
    await f.selector.ready;
    // Assert
    expect(options(f.container)).toEqual(["Authorized A", "Authorized B"]);
  });

  it("supports an explicitly capable provider without a second app opt-in", async () => {
    // Arrange
    const f = fixture({ provider: { listProjects: async () => ({ projects, allow_user_scope: true, current_scope: "user" }), rememberScope: async () => {} } });
    // Act
    await f.selector.ready;
    // Assert
    expect([options(f.container), f.selector.getSelection()]).toEqual([["All Projects", "Authorized A", "Authorized B"], { scope: "user", id: null }]);
  });

  it.each([["en", "All Projects"], ["ja", "すべてのプロジェクト"]])("renders shared scope row in %s", async (language, all) => {
    // Arrange
    document.documentElement.lang = language;
    const f = fixture({ allowUserScope: true });
    // Act
    await f.selector.ready;
    // Assert
    expect(options(f.container)).toEqual([all, "Authorized A", "Authorized B"]);
  });

  it.each([undefined, null, "", "invalid"])("missing or malformed current scope %s never means user", async (currentScope) => {
    // Arrange
    const f = fixture({ allowUserScope: true, currentScope, current: null, provider: { listProjects: async () => ({ projects, current: null }), rememberScope: async () => {} } });
    // Act
    await f.selector.ready;
    // Assert
    expect(f.selector.getSelection()).toBeNull();
  });

  it("honors an explicit supported user current scope", async () => {
    // Arrange
    const f = fixture({ allowUserScope: true, currentScope: "user" });
    // Act
    await f.selector.ready;
    // Assert
    expect([f.selector.getSelection(), f.container.querySelector('[aria-current="true"]')?.textContent]).toEqual([{ scope: "user", id: null }, "All Projects"]);
  });

  it("pointer selection persists explicit user scope before emitting", async () => {
    // Arrange
    const f = fixture({ allowUserScope: true });
    await f.selector.ready;
    // Act
    (f.container.querySelector('[role="option"]') as HTMLButtonElement).click();
    await settle();
    // Assert
    expect([f.saved, f.events, f.selector.getSelection()]).toEqual([[{ scope: "user", id: null }], [{ scope: "user", id: null, name: "All Projects" }], { scope: "user", id: null }]);
  });

  it.each(["user", "project"])("rejected %s scoped persistence retains prior selection and emits no accepted change", async (scope) => {
    // Arrange
    const f = fixture({ allowUserScope: true }, async () => { throw new Error("unsupported"); });
    await f.selector.ready;
    // Act
    f.selector.commands.run(f.selector.selectCommandId, { via: "agent" }, { scope, id: scope === "user" ? null : "b" });
    await settle();
    // Assert
    expect([f.events, f.selector.getSelection(), f.container.querySelector("button")?.disabled]).toEqual([[], { scope: "project", id: "a" }, false]);
  });

  it("keyboard and touch activation use the same command as agent selection", async () => {
    // Arrange
    const f = fixture({ allowUserScope: true });
    await f.selector.ready;
    const search = f.container.querySelector("input")!;
    // Act
    (f.container.querySelector("button") as HTMLButtonElement).click();
    search.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowUp", bubbles: true }));
    search.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    await settle();
    (f.container.querySelectorAll('[role="option"]')[2] as HTMLButtonElement).dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await settle();
    // Assert
    expect(f.events).toEqual([{ scope: "user", id: null, name: "All Projects" }, { scope: "project", id: "b", name: "Authorized B" }]);
  });

  it("disabled capability keeps exact legacy project event", async () => {
    // Arrange
    const f = fixture();
    await f.selector.ready;
    // Act
    (f.container.querySelectorAll('[role="option"]')[1] as HTMLButtonElement).click();
    // Assert
    expect(f.events).toEqual([{ id: "b", name: "Authorized B" }]);
  });

  it.each([null, {}, { id: null }, { scope: "user", id: "a" }, { scope: "project", id: null }, { scope: "project", id: "private" }, { scope: "other", id: "a" }])("rejects malformed or unauthorized command %j", async (choice) => {
    // Arrange
    const f = fixture({ allowUserScope: true });
    await f.selector.ready;
    // Act
    const accepted = f.selector.commands.run(f.selector.selectCommandId, { via: "agent" }, choice);
    // Assert
    expect([accepted, f.saved, f.events, f.selector.getCurrent()?.id]).toEqual([false, [], [], "a"]);
  });

  it("does not authorize a project removed from the provider list", async () => {
    // Arrange
    const f = fixture({ allowUserScope: true });
    await f.selector.ready;
    // Act
    f.selector.setProjects([projects[0]]);
    const accepted = f.selector.commands.run(f.selector.selectCommandId, { via: "agent" }, { scope: "project", id: "b" });
    // Assert
    expect([accepted, f.events]).toEqual([false, []]);
  });

  it("an outdated initial listing cannot overwrite a newer authorized list", async () => {
    // Arrange
    let resolve!: (listing: unknown) => void;
    const listing = new Promise((done) => { resolve = done; });
    const f = fixture({ provider: { listProjects: () => listing } });
    // Act
    f.selector.setProjects([projects[0]], "a"); resolve({ projects, current: "b" }); await f.selector.ready;
    const accepted = f.selector.commands.run(f.selector.selectCommandId, { via: "agent" }, { scope: "project", id: "b" });
    // Assert
    expect([accepted, options(f.container), f.selector.getCurrent()?.id]).toEqual([false, ["Authorized A"], "a"]);
  });

  it("a pending user acknowledgement cannot overwrite a newer list/choice", async () => {
    // Arrange
    let resolve!: () => void;
    const pending = new Promise<void>((done) => { resolve = done; });
    const f = fixture({ allowUserScope: true }, () => pending); await f.selector.ready;
    // Act
    f.selector.commands.run(f.selector.selectCommandId, { via: "agent" }, { scope: "user", id: null });
    f.selector.setProjects([projects[1]], "b"); resolve(); await settle();
    // Assert
    expect([f.events, f.selector.getSelection(), f.container.querySelector("button")?.disabled]).toEqual([[], { scope: "project", id: "b" }, false]);
  });

  it("returned project objects cannot inject authorization into the list", async () => {
    // Arrange
    const f = fixture(); await f.selector.ready;
    // Act
    f.selector.getCurrent()!.id = "private";
    const accepted = f.selector.commands.run(f.selector.selectCommandId, { via: "agent" }, { scope: "project", id: "private" });
    // Assert
    expect([accepted, options(f.container), f.selector.getSelection()]).toEqual([false, ["Authorized A", "Authorized B"], { scope: "project", id: "a" }]);
  });

  it("filters malformed projects and never treats their missing ids as user scope", async () => {
    // Arrange
    const f = fixture({ provider: { listProjects: async () => ({ projects: [projects[0], { id: null, name: "User?" }, { name: "Missing" }, projects[0]], current: null }), rememberScope: async () => {} }, allowUserScope: true });
    // Act
    await f.selector.ready;
    // Assert
    expect([options(f.container), f.selector.getSelection()]).toEqual([["All Projects", "Authorized A"], null]);
  });

  it("non-array provider listing fails closed", async () => {
    // Arrange
    const f = fixture({ allowUserScope: true, provider: { listProjects: async () => ({ projects: {}, allow_user_scope: true }), rememberScope: async () => {} } });
    // Act
    await f.selector.ready;
    const accepted = f.selector.commands.run(f.selector.selectCommandId, { via: "agent" }, { scope: "user", id: null });
    // Assert
    expect([accepted, options(f.container), f.events]).toEqual([false, [], []]);
  });

  it("canonical mount uses an explicit host provider adapter and never routes user to project navigation", async () => {
    // Arrange
    const container = document.createElement("div");
    container.setAttribute("data-stx-project-picker", ""); container.setAttribute("data-provider-url", "/legacy/projects/");
    container.setAttribute("data-allow-user-scope", "true"); container.setAttribute("data-current", "a");
    container.setAttribute("data-navigate", "?project={id}"); document.body.append(container);
    const persisted: unknown[] = [];
    // Act
    const [selector] = mountProjectPickers(document, () => ({ listProjects: async () => ({ projects }), rememberScope: async (choice) => { persisted.push(choice); } }));
    instances.push(selector); await selector.ready;
    (container.querySelector('[role="option"]') as HTMLButtonElement).click(); await settle();
    // Assert
    expect([persisted, selector.getSelection(), window.location.search]).toEqual([[{ scope: "user", id: null }], { scope: "user", id: null }, ""]);
  });

  it("user-app scope gate remains absent when its opted-in provider cannot persist scoped choices", () => {
    // Arrange
    const container = document.createElement("div");
    // Act
    const selector = mountProjectSelectorByScope({ container, scope: "user", allowUserScope: true, projects });
    // Assert
    expect([selector, container.innerHTML]).toEqual([null, ""]);
  });

  it("user-app scope gate reuses the canonical supported selector", async () => {
    // Arrange
    const container = document.createElement("div");
    const provider: ProjectProvider = { listProjects: async () => ({ projects, current_scope: "user" }), rememberScope: async () => {} };
    // Act
    const selector = mountProjectSelectorByScope({ container, scope: "user", allowUserScope: true, provider })!;
    instances.push(selector); await selector.ready;
    // Assert
    expect([selector.constructor.name, container.className, options(container), selector.getSelection()]).toEqual(["ProjectSelector", "stx-app-project-selector", ["All Projects", "Authorized A", "Authorized B"], { scope: "user", id: null }]);
  });

  it("legacy HTTP provider rejects nullable id before POST while valid project contract is unchanged", async () => {
    // Arrange
    const posts: unknown[] = [];
    const server = createServer(async (request, response) => {
      const chunks = []; for await (const chunk of request) chunks.push(chunk);
      if (request.method === "POST") posts.push(JSON.parse(Buffer.concat(chunks).toString()));
      response.setHeader("Content-Type", "application/json"); response.end(JSON.stringify({ projects, current: "a" }));
    });
    await new Promise<void>((done) => server.listen(0, "127.0.0.1", done));
    const address = server.address() as { port: number };
    const provider = httpProjectProvider(`http://127.0.0.1:${address.port}/projects`);
    // Act
    let rejected = false;
    try { await provider.rememberProject!(null as unknown as string); } catch { rejected = true; }
    await provider.rememberProject!("b");
    await new Promise<void>((done, reject) => server.close((error) => error ? reject(error) : done()));
    // Assert
    expect([rejected, posts, provider.rememberScope]).toEqual([true, [{ id: "b" }], undefined]);
  });

  it("private stable command registries keep independent pickers separate", async () => {
    // Arrange
    const a = fixture({ allowUserScope: true });
    const b = fixture({ allowUserScope: true });
    await Promise.all([a.selector.ready, b.selector.ready]);
    // Act
    a.selector.commands.run(a.selector.selectCommandId, { via: "agent" }, { scope: "project", id: "b" });
    await settle();
    // Assert
    expect([a.events, b.events, a.selector.selectCommandId === b.selector.selectCommandId]).toEqual([[{ scope: "project", id: "b", name: "Authorized B" }], [], true]);
  });

  it("does not overwrite a caller registry command", () => {
    // Arrange
    const commands = new CommandRegistry();
    const original = { id: "project-selector:select", label: "Owner", action: () => false };
    commands.set(original);
    const container = document.createElement("div");
    // Act
    let rejected = false;
    try { new ProjectSelector({ container, projects, commands }); } catch { rejected = true; }
    // Assert
    expect([rejected, commands.get(original.id)?.def, container.children.length]).toEqual([true, original, 0]);
  });

  it("an old widget never dispatches a replacement owner command or removes it on destruction", async () => {
    // Arrange
    const commands = new CommandRegistry(), calls: unknown[] = [];
    const f = fixture({ commands }); await f.selector.ready;
    const replacement = { id: f.selector.selectCommandId, label: "New owner", action: (choice: unknown) => { calls.push(choice); } };
    commands.set(replacement);
    // Act
    (f.container.querySelectorAll('[role="option"]')[1] as HTMLButtonElement).click();
    f.selector.destroy();
    // Assert
    expect([calls, f.events, commands.get(replacement.id)?.def]).toEqual([[], [], replacement]);
  });

  it.each([null, undefined, "", 0])("null/malformed id %s cannot navigate a project URL", (id) => {
    // Arrange
    const navigate = "?project={id}";
    // Act
    const url = projectNavigationUrl(navigate, id);
    // Assert
    expect(url).toBeNull();
  });
});
