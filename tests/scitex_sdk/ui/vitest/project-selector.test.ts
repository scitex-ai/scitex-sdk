/** Canonical picker scope/command contract through the real component and provider ports. */
import { afterEach, describe, expect, it, vi } from "vitest";
import * as sourcePicker from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/ts/app/project-selector";
import * as shippedPicker from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/js/app/project-selector.js";
import { CommandRegistry } from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/ts/shell/keymap/_registry";
import { createServer } from "node:http";
import { mountProjectSelectorByScope as sourceScopeMount, hostProjectProvider as sourceScopeProvider } from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/ts/shell/app-scope-selector";
import { mountProjectSelectorByScope as shippedScopeMount, hostProjectProvider as shippedScopeProvider } from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/js/shell/app-scope-selector.js";
import type { ProjectProvider } from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/ts/app/project-selector/provider";

const projects = [{ id: "a", name: "Authorized A" }, { id: "b", name: "Authorized B" }];
const shipped = process.env.STX_PICKER_TEST_RUNTIME === "shipped";
const { ProjectSelector, PROJECT_SELECTOR_CHANGE, projectNavigationUrl, mountProjectPickers, httpProjectProvider } = shipped ? shippedPicker : sourcePicker;
const mountProjectSelectorByScope = shipped ? shippedScopeMount : sourceScopeMount;
const scopeHostProvider = shipped ? shippedScopeProvider : sourceScopeProvider;
const instances: sourcePicker.ProjectSelector[] = [];
const httpServers: ReturnType<typeof createServer>[] = [];
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
afterEach(async () => {
  instances.splice(0).forEach((selector) => selector.destroy());
  document.body.innerHTML = ""; document.documentElement.lang = "en";
  await Promise.all(httpServers.splice(0).map((server) => new Promise<void>((done) => {
    server.closeAllConnections(); server.close(() => done());
  })));
});

interface PendingProjectPost {
  body: unknown;
  reply(body: unknown, status?: number, raw?: boolean): void;
}

/** Real HTTP requests are held until the test supplies an acceptance response. */
async function projectHttpServer(initialListing: unknown, holdListing = false) {
  let listing = initialListing, gets = 0;
  const posts: unknown[] = [];
  const pending: PendingProjectPost[] = [];
  const waiting: ((post: PendingProjectPost) => void)[] = [];
  const pendingGets: PendingProjectPost[] = [];
  const waitingGets: ((get: PendingProjectPost) => void)[] = [];
  const server = createServer(async (request, response) => {
    response.setHeader("Content-Type", "application/json");
    const reply = (value: unknown, status = 200, raw = false) => {
      response.statusCode = status;
      response.end(raw ? String(value) : JSON.stringify(value));
    };
    if (request.method === "GET") {
      gets++;
      if (holdListing) {
        const get = { body: undefined, reply }, receive = waitingGets.shift();
        if (receive) receive(get); else pendingGets.push(get);
      } else reply(listing);
      return;
    }
    const chunks = []; for await (const chunk of request) chunks.push(chunk);
    const body: unknown = JSON.parse(Buffer.concat(chunks).toString());
    posts.push(body);
    const post = { body, reply };
    const receive = waiting.shift();
    if (receive) receive(post); else pending.push(post);
  });
  await new Promise<void>((done, reject) => {
    server.once("error", reject); server.listen(0, "127.0.0.1", done);
  });
  httpServers.push(server);
  return {
    url: `http://127.0.0.1:${(server.address() as { port: number }).port}/projects`,
    posts,
    get gets() { return gets; },
    setListing(value: unknown) { listing = value; },
    nextPost(): Promise<PendingProjectPost> {
      const post = pending.shift();
      return post ? Promise.resolve(post) : new Promise((receive) => waiting.push(receive));
    },
    nextGet(): Promise<PendingProjectPost> {
      const get = pendingGets.shift();
      return get ? Promise.resolve(get) : new Promise((receive) => waitingGets.push(receive));
    },
  };
}

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

describe("legacy project persistence acceptance", () => {
  it.each([403, 500])("rejects actual HTTP %s before treating a project POST as accepted", async (status) => {
    // Arrange
    const posts: unknown[] = [];
    const server = createServer(async (request, response) => {
      const chunks = []; for await (const chunk of request) chunks.push(chunk);
      posts.push(JSON.parse(Buffer.concat(chunks).toString()));
      response.statusCode = status; response.end("explicit synthetic rejection");
    });
    await new Promise<void>((done) => server.listen(0, "127.0.0.1", done));
    const provider = httpProjectProvider(`http://127.0.0.1:${(server.address() as { port: number }).port}/projects`);
    // Act
    let failure: unknown;
    try { await provider.rememberProject!("b"); } catch (error) { failure = error; }
    await new Promise<void>((done, reject) => server.close((error) => error ? reject(error) : done()));
    // Assert
    expect([posts, failure instanceof Error ? failure.message : null]).toEqual([[{ id: "b" }], `project selection failed: HTTP ${status}`]);
  });

  it("waits for the optional legacy port before changing local state or the legacy event", async () => {
    // Arrange
    let accept!: () => void;
    const accepted = new Promise<void>((resolve) => { accept = resolve; });
    const ids: string[] = [];
    const provider: ProjectProvider = { listProjects: async () => ({ projects, current: "a" }), rememberProject: async (id) => { ids.push(id); await accepted; } };
    const f = fixture({ provider }); await f.selector.ready;
    // Act
    (f.container.querySelectorAll('[role="option"]')[1] as HTMLButtonElement).click();
    const before = [f.selector.getSelection(), [...f.events], (f.container.querySelector("button") as HTMLButtonElement).disabled];
    accept(); await settle();
    // Assert
    expect([before, f.selector.getSelection(), f.events, ids, (f.container.querySelector("button") as HTMLButtonElement).disabled]).toEqual([
      [{ scope: "project", id: "a" }, [], true], { scope: "project", id: "b" }, [{ id: "b", name: "Authorized B" }], ["b"], false,
    ]);
  });

  it("a rejected legacy port preserves selection and exposes the existing error surface", async () => {
    // Arrange
    const provider: ProjectProvider = { listProjects: async () => ({ projects, current: "a" }), rememberProject: async () => { throw Error("explicit rejection"); } };
    const f = fixture({ provider }); await f.selector.ready;
    // Act
    f.selector.commands.run(f.selector.selectCommandId, { via: "agent" }, { scope: "project", id: "b" }); await settle();
    // Assert
    const error = f.container.querySelector('[role="status"]') as HTMLElement | null;
    expect([f.selector.getSelection(), f.events, error?.hidden, error?.textContent, (f.container.querySelector("button") as HTMLButtonElement).disabled]).toEqual([
      { scope: "project", id: "a" }, [], false, "Could not select scope", false,
    ]);
  });

  it.each(["replace", "destroy"])("late legacy acknowledgement cannot overwrite %s", async (mutation) => {
    // Arrange
    let accept!: () => void;
    const accepted = new Promise<void>((resolve) => { accept = resolve; });
    const provider: ProjectProvider = { listProjects: async () => ({ projects, current: "a" }), rememberProject: () => accepted };
    const f = fixture({ provider }); await f.selector.ready;
    // Act
    f.selector.commands.run(f.selector.selectCommandId, { via: "agent" }, { scope: "project", id: "b" });
    if (mutation === "replace") f.selector.setProjects(projects, "a", "project"); else f.selector.destroy();
    accept(); await settle();
    // Assert
    expect([f.selector.getSelection(), f.events, mutation === "destroy" ? f.container.childElementCount : (f.container.querySelector("button") as HTMLButtonElement).disabled]).toEqual([
      { scope: "project", id: "a" }, [], mutation === "destroy" ? 0 : false,
    ]);
  });

  it("an old legacy completion does not reenable a newer pending request", async () => {
    // Arrange
    const accepts: (() => void)[] = [];
    const provider: ProjectProvider = { listProjects: async () => ({ projects, current: "a" }), rememberProject: () => new Promise<void>((resolve) => accepts.push(resolve)) };
    const f = fixture({ provider }); await f.selector.ready;
    // Act
    f.selector.commands.run(f.selector.selectCommandId, { via: "agent" }, { scope: "project", id: "b" });
    f.selector.setProjects(projects, "a", "project");
    f.selector.commands.run(f.selector.selectCommandId, { via: "agent" }, { scope: "project", id: "b" });
    accepts[0](); await settle();
    const old = [f.selector.getSelection(), [...f.events], (f.container.querySelector("button") as HTMLButtonElement).disabled];
    accepts[1](); await settle();
    // Assert
    expect([old, f.events, (f.container.querySelector("button") as HTMLButtonElement).disabled]).toEqual([
      [{ scope: "project", id: "a" }, [], true], [{ id: "b", name: "Authorized B" }], false,
    ]);
  });

  it("a replaced persistence port cannot attribute its old acknowledgement to the new port", async () => {
    // Arrange
    let accept!: () => void;
    const accepted = new Promise<void>((resolve) => { accept = resolve; });
    const provider: ProjectProvider = { listProjects: async () => ({ projects, current: "a" }), rememberProject: () => accepted };
    const f = fixture({ provider }); await f.selector.ready;
    // Act
    f.selector.commands.run(f.selector.selectCommandId, { via: "agent" }, { scope: "project", id: "b" });
    provider.rememberProject = async () => {};
    accept(); await settle();
    // Assert
    expect([f.selector.getSelection(), f.events, (f.container.querySelector("button") as HTMLButtonElement).disabled]).toEqual([{ scope: "project", id: "a" }, [], false]);
  });

  it.each(["unknown", null, false, undefined])("a configured legacy port becoming %s fails closed instead of masquerading as static", async (port) => {
    // Arrange
    const provider: ProjectProvider = { listProjects: async () => ({ projects, current: "a" }), rememberProject: async () => {} };
    const f = fixture({ provider }); await f.selector.ready;
    provider.rememberProject = port as unknown as ProjectProvider["rememberProject"];
    // Act
    const accepted = f.selector.commands.run(f.selector.selectCommandId, { via: "agent" }, { scope: "project", id: "b" }); await settle();
    // Assert
    const error = f.container.querySelector('[role="status"]') as HTMLElement | null;
    expect([accepted, f.selector.getSelection(), f.events, error?.hidden]).toEqual([false, { scope: "project", id: "a" }, [], false]);
  });

  it("a static provider without persistence retains synchronous legacy project selection", async () => {
    // Arrange
    const provider = sourcePicker.staticProjectProvider(projects, "a");
    const f = fixture({ provider }); await f.selector.ready;
    // Act
    const accepted = f.selector.commands.run(f.selector.selectCommandId, { via: "agent" }, { scope: "project", id: "b" });
    // Assert
    expect([accepted, f.selector.getSelection(), f.events, f.container.childElementCount]).toEqual([true, { scope: "project", id: "b" }, [{ id: "b", name: "Authorized B" }], 2]);
  });

  it("a synchronous persistence throw preserves selection and releases the trigger", async () => {
    // Arrange
    const provider: ProjectProvider = { listProjects: async () => ({ projects, current: "a" }), rememberProject: () => { throw Error("explicit synchronous failure"); } };
    const f = fixture({ provider }); await f.selector.ready;
    // Act
    f.selector.commands.run(f.selector.selectCommandId, { via: "agent" }, { scope: "project", id: "b" }); await settle();
    // Assert
    expect([f.selector.getSelection(), f.events, (f.container.querySelector("button") as HTMLButtonElement).disabled, (f.container.querySelector('[role="status"]') as HTMLElement).hidden]).toEqual([{ scope: "project", id: "a" }, [], false, false]);
  });

  it("acceptance keeps the provider method receiver and project-only event shape", async () => {
    // Arrange
    const ids: string[] = [];
    const provider: ProjectProvider = {
      listProjects: async () => ({ projects, current: "a" }),
      async rememberProject(id) { if (this !== provider) throw Error("provider receiver lost"); ids.push(id); },
    };
    const f = fixture({ provider }); await f.selector.ready;
    // Act
    f.selector.commands.run(f.selector.selectCommandId, { via: "agent" }, { scope: "project", id: "b" }); await settle();
    // Assert
    expect([ids, f.selector.getSelection(), f.events]).toEqual([["b"], { scope: "project", id: "b" }, [{ id: "b", name: "Authorized B" }]]);
  });
});

describe("scoped HTTP persistence and first mount", () => {
  it.each(["user", "project"] as const)("waits for a matching real HTTP %s acknowledgement before accepting", async (scope) => {
    const server = await projectHttpServer({ projects, current_scope: "project", current: "a", allow_user_scope: true });
    const provider = httpProjectProvider(server.url, { allowUserScope: true });
    expect(provider.rememberScope).toBeUndefined();
    const f = fixture({ provider, allowUserScope: true }); await f.selector.ready;
    const trigger = f.container.querySelector("button") as HTMLButtonElement;
    const target = { scope, id: scope === "user" ? null : "b" };
    trigger.click();
    (f.container.querySelectorAll('[role="option"]')[scope === "user" ? 0 : 2] as HTMLButtonElement).click();
    const post = await server.nextPost();
    expect(post.body).toEqual(target);
    expect(f.selector.commands.run(f.selector.selectCommandId, { via: "agent" }, target)).toBe(false);
    expect([server.posts, f.selector.getSelection(), f.container.querySelector(".stx-app-project-selector__current")?.textContent, f.events, trigger.disabled]).toEqual([
      [target], { scope: "project", id: "a" }, "Authorized A", [], true,
    ]);
    expect(Array.from(f.container.querySelectorAll<HTMLButtonElement>('[role="option"]')).every((option) => option.disabled)).toBe(true);
    post.reply({ current_scope: scope, current: target.id });
    await vi.waitFor(() => expect(trigger.disabled).toBe(false));
    const name = scope === "user" ? "All Projects" : "Authorized B";
    expect([f.selector.getSelection(), f.container.querySelector(".stx-app-project-selector__current")?.textContent, f.events, server.posts]).toEqual([
      target, name, [{ ...target, name }], [target],
    ]);
  });

  it.each(["user", "project"] as const)("rejects failed, malformed and mismatched real HTTP %s acknowledgements", async (scope) => {
    const server = await projectHttpServer({ projects, current_scope: "project", current: "a", allow_user_scope: true });
    const container = document.createElement("div");
    container.setAttribute("data-stx-project-picker", ""); container.setAttribute("data-provider-url", server.url);
    container.setAttribute("data-allow-user-scope", "true"); container.setAttribute("data-navigate", "?project={id}");
    document.body.append(container);
    const events: unknown[] = [];
    container.addEventListener(PROJECT_SELECTOR_CHANGE, (event) => events.push((event as CustomEvent).detail));
    const [selector] = mountProjectPickers(document); instances.push(selector); await selector.ready;
    const trigger = container.querySelector("button") as HTMLButtonElement;
    const target = { scope, id: scope === "user" ? null : "b" }, locationBefore = window.location.href;
    const replies = [
      { body: { error: "denied" }, status: 403 },
      { body: "{invalid JSON", raw: true },
      { body: { current: target.id } },
      { body: { current_scope: scope === "user" ? "project" : "user", current: scope === "user" ? "b" : null } },
    ];
    for (const reply of replies) {
      trigger.click();
      (container.querySelectorAll('[role="option"]')[scope === "user" ? 0 : 2] as HTMLButtonElement).click();
      const post = await server.nextPost();
      expect([post.body, selector.getSelection(), events, trigger.disabled]).toEqual([target, { scope: "project", id: "a" }, [], true]);
      post.reply(reply.body, reply.status ?? 200, reply.raw ?? false);
      await vi.waitFor(() => expect(trigger.disabled).toBe(false));
      const error = container.querySelector('[role="status"]') as HTMLElement;
      expect([selector.getSelection(), container.querySelector(".stx-app-project-selector__current")?.textContent, events, error.hidden, error.textContent, window.location.href]).toEqual([
        { scope: "project", id: "a" }, "Authorized A", [], false, "Could not select scope", locationBefore,
      ]);
    }
    expect(server.posts).toEqual(replies.map(() => target));
    // The same real control remains usable after a rejected acknowledgement.
    if (scope === "user") {
      (container.querySelector('[role="option"]') as HTMLButtonElement).click();
      const post = await server.nextPost(); post.reply({ current_scope: "user", current: null });
      await vi.waitFor(() => expect(trigger.disabled).toBe(false));
      expect([selector.getSelection(), events, window.location.href]).toEqual([
        { scope: "user", id: null }, [{ scope: "user", id: null, name: "All Projects" }], locationBefore,
      ]);
    }
  });

  it("the default first mount stays legacy despite a capable server", async () => {
    const server = await projectHttpServer({ projects, current_scope: "project", current: "a", allow_user_scope: true });
    const container = document.createElement("div");
    container.setAttribute("data-stx-project-picker", ""); container.setAttribute("data-provider-url", server.url);
    document.body.append(container);
    const events: unknown[] = [];
    container.addEventListener(PROJECT_SELECTOR_CHANGE, (event) => events.push((event as CustomEvent).detail));
    const [selector] = mountProjectPickers(document); instances.push(selector); await selector.ready;
    expect(options(container)).toEqual(["Authorized A", "Authorized B"]);
    expect(selector.commands.run(selector.selectCommandId, { via: "agent" }, { scope: "user", id: null })).toBe(false);
    (container.querySelectorAll('[role="option"]')[1] as HTMLButtonElement).click();
    const post = await server.nextPost(); expect(post.body).toEqual({ id: "b" });
    post.reply({ current: "b" });
    await vi.waitFor(() => expect((container.querySelector("button") as HTMLButtonElement).disabled).toBe(false));
    expect([selector.getSelection(), events]).toEqual([{ scope: "project", id: "b" }, [{ id: "b", name: "Authorized B" }]]);
  });

  it.each([undefined, false, "true"])("client opt-in cannot enable an unsupported server capability %s", async (allow_user_scope) => {
    const server = await projectHttpServer({ projects, current_scope: "project", current: "a", allow_user_scope });
    const provider = httpProjectProvider(server.url, { allowUserScope: true });
    const f = fixture({ provider, allowUserScope: true }); await f.selector.ready;
    expect([provider.rememberScope, options(f.container), f.selector.getSelection(), server.posts]).toEqual([undefined, [], null, []]);
    expect(f.selector.commands.run(f.selector.selectCommandId, { via: "agent" }, { scope: "user", id: null })).toBe(false);
  });

  it.each([
    { current_scope: "user", current: "a" },
    { current_scope: "project", current: null },
    { current_scope: null, current: null },
    { current: "a" },
  ])("invalid initial scope pair %j cannot install the scoped port", async (pair) => {
    const server = await projectHttpServer({ projects, allow_user_scope: true, ...pair });
    const provider = httpProjectProvider(server.url, { allowUserScope: true });
    const f = fixture({ provider, allowUserScope: true }); await f.selector.ready;
    expect([provider.rememberScope, f.selector.getSelection(), options(f.container), server.posts]).toEqual([undefined, null, [], []]);
  });

  it.each([
    { label: "user", pair: { current_scope: "user", current: null }, selection: { scope: "user", id: null } },
    { label: "project", pair: { current_scope: "project", current: "b" }, selection: { scope: "project", id: "b" } },
    { label: "unselected", pair: { current: null }, selection: null },
  ])("the normal first mount uses authoritative $label state over stale page attributes", async ({ pair, selection }) => {
    const server = await projectHttpServer({ projects, allow_user_scope: true, ...pair });
    const container = document.createElement("div");
    container.setAttribute("data-stx-project-picker", ""); container.setAttribute("data-provider-url", server.url);
    container.setAttribute("data-allow-user-scope", "true"); container.setAttribute("data-current", "a"); container.setAttribute("data-current-scope", "project");
    document.body.append(container);
    const [selector] = mountProjectPickers(document); instances.push(selector); await selector.ready;
    expect([selector.getSelection(), options(container), server.gets, server.posts]).toEqual([selection, ["All Projects", "Authorized A", "Authorized B"], 1, []]);
    expect(mountProjectPickers(document)).toEqual([]);
    expect([server.gets, container.querySelectorAll(".stx-app-project-selector__trigger").length]).toEqual([1, 1]);
  });

  it.each(["revoked", "replaced"])("a pending HTTP acknowledgement cannot apply after authority is %s", async (mutation) => {
    const server = await projectHttpServer({ projects, current_scope: "project", current: "a", allow_user_scope: true });
    const provider = httpProjectProvider(server.url, { allowUserScope: true });
    const f = fixture({ provider, allowUserScope: true }); await f.selector.ready;
    f.selector.commands.run(f.selector.selectCommandId, { via: "agent" }, { scope: "user", id: null });
    const post = await server.nextPost();
    if (mutation === "revoked") {
      server.setListing({ projects, current_scope: "project", current: "a", allow_user_scope: false });
      await expect(provider.listProjects()).rejects.toThrow();
      expect(provider.rememberScope).toBeUndefined();
    } else provider.rememberScope = async () => {};
    post.reply({ current_scope: "user", current: null });
    await vi.waitFor(() => expect((f.container.querySelector("button") as HTMLButtonElement).disabled).toBe(false));
    expect([f.selector.getSelection(), f.events, server.posts]).toEqual([{ scope: "project", id: "a" }, [], [{ scope: "user", id: null }]]);
  });

  it("the shell entrypoint accepts a pending scoped provider from the picker entrypoint", async () => {
    const server = await projectHttpServer(null, true);
    const provider = httpProjectProvider(server.url, { allowUserScope: true });
    const container = document.createElement("div"); document.body.append(container);
    const selector = mountProjectSelectorByScope({ container, scope: "user", allowUserScope: true, provider, current: "a", currentScope: "project" });
    expect(selector).not.toBeNull(); instances.push(selector!);
    const get = await server.nextGet();
    expect([provider.rememberScope, selector!.getSelection(), options(container)]).toEqual([undefined, null, []]);
    get.reply({ projects, allow_user_scope: true, current_scope: "user", current: null });
    await selector!.ready;
    expect([selector!.getSelection(), options(container)]).toEqual([{ scope: "user", id: null }, ["All Projects", "Authorized A", "Authorized B"]]);
  });

  it("picker first mount recognizes a scoped provider from the shell entrypoint", async () => {
    const server = await projectHttpServer({ projects, allow_user_scope: true, current_scope: "user", current: null });
    const meta = document.createElement("meta"); meta.name = "stx-project-provider"; meta.content = server.url; document.head.append(meta);
    try {
      const provider = scopeHostProvider(document, { allowUserScope: true })!;
      const container = document.createElement("div");
      container.setAttribute("data-stx-project-picker", ""); container.setAttribute("data-provider-url", server.url);
      container.setAttribute("data-allow-user-scope", "true"); container.setAttribute("data-current", "a"); container.setAttribute("data-current-scope", "project");
      document.body.append(container);
      const [selector] = mountProjectPickers(document, () => provider); instances.push(selector); await selector.ready;
      expect([selector.getSelection(), options(container)]).toEqual([{ scope: "user", id: null }, ["All Projects", "Authorized A", "Authorized B"]]);
    } finally { meta.remove(); }
  });
});
