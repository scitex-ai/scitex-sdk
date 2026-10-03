/** Host-owned commands, shortcuts, and the shared project picker through real DOM events. */
import { afterEach, describe, expect, it, vi } from "vitest";
import { CommandRegistry, Keymap } from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/ts/shell/keymap";
import type { CommandDef } from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/ts/shell/keymap";
import { WorkspaceCommands } from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/ts/shell/workspace-commands";
import { ProjectSelector, PROJECT_SELECTOR_CHANGE, PROJECT_SELECTOR_OPEN, httpProjectProvider } from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/ts/app/project-selector";
import { mountProjectSelectorByScope } from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/ts/shell/app-scope-selector";

const mounted: Array<{ destroy(): void }> = [];
const projects = [{ id: "a", name: "Authorized A" }, { id: "b", name: "Authorized B" }];

function container(): HTMLDivElement {
  const node = document.createElement("div");
  document.body.append(node);
  return node;
}

function host(definitions: CommandDef[] = [], commandIds = definitions.map((command) => command.id)) {
  const registry = new CommandRegistry();
  definitions.forEach((definition) => registry.set(definition));
  const keymap = new Keymap({ registry });
  const node = container();
  const commands = new WorkspaceCommands({ container: node, registry, keymap, commandIds });
  mounted.push(commands);
  return { registry, keymap, commands, container: node };
}

function trigger(node: HTMLElement): HTMLButtonElement {
  return node.querySelector("button")!;
}

function filter(node: HTMLElement): HTMLInputElement {
  return node.querySelector('input[aria-label="Find command"]')!;
}

function result(node: HTMLElement, commandId: string): HTMLButtonElement {
  const button = Array.from(node.querySelectorAll<HTMLButtonElement>("button[data-command-id]"))
    .find((candidate) => candidate.dataset.commandId === commandId);
  expect(button).toBeDefined();
  return button!;
}

function shortcut(node: HTMLElement, label: string): HTMLInputElement {
  const input = Array.from(node.querySelectorAll<HTMLInputElement>("input[aria-label]"))
    .find((candidate) => candidate.getAttribute("aria-label") === `Shortcut for ${label}`);
  expect(input).toBeDefined();
  return input!;
}

function shortcutButton(node: HTMLElement, label: string, text: string): HTMLButtonElement {
  const input = shortcut(node, label);
  let row: HTMLElement | null = input.parentElement;
  while (row && row !== node) {
    const button = Array.from(row.querySelectorAll<HTMLButtonElement>("button"))
      .find((candidate) => candidate.textContent?.trim() === text);
    if (button) return button;
    row = row.parentElement;
  }
  throw new Error(`Missing ${text} control for ${label}`);
}

function applyShortcut(node: HTMLElement, label: string, sequence: string): void {
  const input = shortcut(node, label);
  input.value = sequence;
  input.dispatchEvent(new Event("input", { bubbles: true }));
  shortcutButton(node, label, "Apply shortcut").click();
}

function key(target: EventTarget, init: KeyboardEventInit): KeyboardEvent {
  const event = new KeyboardEvent("keydown", { ...init, bubbles: true, cancelable: true });
  target.dispatchEvent(event);
  return event;
}

async function settle(): Promise<void> {
  await Promise.resolve();
  await Promise.resolve();
}

afterEach(() => {
  mounted.splice(0).reverse().forEach((component) => component.destroy());
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  document.body.replaceChildren();
});

describe("WorkspaceCommands interactions", () => {
  it("offers a native inline palette, filters configured commands, and restores trigger focus on Escape", () => {
    const run = vi.fn();
    const h = host([
      { id: "search", label: "Search projects", action: run },
      { id: "export", label: "Export figure", action: run },
      { id: "unlisted", label: "Unlisted command", action: run },
    ], ["search", "export"]);
    const button = trigger(h.container);
    expect(button.type).toBe("button");
    expect(button.textContent).toBe("Commands");
    expect(button.getAttribute("aria-expanded")).toBe("false");
    const panelId = button.getAttribute("aria-controls");
    expect(panelId).toBeTruthy();
    const panel = document.getElementById(panelId!);
    expect(panel?.tagName).toBe("SECTION");
    expect(panel?.getAttribute("aria-label")).toBe("Workspace commands");
    expect(h.container.querySelector('[role="dialog"], [aria-modal="true"]')).toBeNull();

    button.click();
    expect(button.getAttribute("aria-expanded")).toBe("true");
    expect(document.activeElement).toBe(filter(h.container));
    expect(h.container.querySelector('[data-command-id="unlisted"]')).toBeNull();
    filter(h.container).value = "export";
    filter(h.container).dispatchEvent(new Event("input", { bubbles: true }));
    expect(Array.from(h.container.querySelectorAll<HTMLButtonElement>("button[data-command-id]"))
      .map((row) => row.dataset.commandId)).toEqual(["export"]);
    expect(result(h.container, "export").type).toBe("button");

    key(filter(h.container), { key: "Escape" });
    expect(button.getAttribute("aria-expanded")).toBe("false");
    expect(document.activeElement).toBe(button);
    expect(run).not.toHaveBeenCalled();
  });

  it("opens the same project picker by pointer, palette, program, and a rebound shortcut without selecting or posting", async () => {
    const fetchRequest = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => new Response(JSON.stringify({ projects, current: "a" }), {
      status: 200, headers: { "Content-Type": "application/json" },
    }));
    vi.stubGlobal("fetch", fetchRequest);
    const registry = new CommandRegistry();
    const keymap = new Keymap({ registry });
    const pickerNode = container();
    const picker = new ProjectSelector({ container: pickerNode, commands: registry,
      openCommandId: PROJECT_SELECTOR_OPEN, provider: httpProjectProvider("/projects") });
    mounted.push(picker);
    await picker.ready;
    expect(picker.openCommandId).toBe(PROJECT_SELECTOR_OPEN);
    const search = pickerNode.querySelector<HTMLInputElement>('input[aria-label="Search projects"]')!;
    const originalPanel = pickerNode.querySelector("[role=listbox]");
    const changed = vi.fn();
    pickerNode.addEventListener(PROJECT_SELECTOR_CHANGE, changed);
    expect(keymap.bind("global", "C-p", PROJECT_SELECTOR_OPEN)).toBeNull();
    const commandsNode = container();
    const commands = new WorkspaceCommands({ container: commandsNode, registry, keymap, commandIds: [PROJECT_SELECTOR_OPEN] });
    mounted.push(commands);

    trigger(pickerNode).click();
    expect([trigger(pickerNode).getAttribute("aria-expanded"), document.activeElement]).toEqual(["true", search]);
    picker.close();
    trigger(commandsNode).click();
    result(commandsNode, PROJECT_SELECTOR_OPEN).click();
    expect(trigger(commandsNode).getAttribute("aria-expanded")).toBe("false");
    expect([trigger(pickerNode).getAttribute("aria-expanded"), document.activeElement]).toEqual(["true", search]);
    picker.close();
    commands.open();
    expect(key(filter(commandsNode), { key: "Enter" }).defaultPrevented).toBe(true);
    expect(trigger(commandsNode).getAttribute("aria-expanded")).toBe("false");
    expect([trigger(pickerNode).getAttribute("aria-expanded"), document.activeElement]).toEqual(["true", search]);
    picker.close();
    expect(registry.run(PROJECT_SELECTOR_OPEN, { via: "program" })).toBe(true);
    expect(document.activeElement).toBe(search);
    picker.close();

    commands.open();
    const label = registry.get(PROJECT_SELECTOR_OPEN)!.def.label;
    applyShortcut(commandsNode, label, "C-j");
    commands.close();
    const previous = key(document.body, { key: "p", ctrlKey: true });
    expect([previous.defaultPrevented, trigger(pickerNode).getAttribute("aria-expanded")]).toEqual([false, "false"]);
    const rebound = key(document.body, { key: "j", ctrlKey: true });
    expect([rebound.defaultPrevented, trigger(pickerNode).getAttribute("aria-expanded"), document.activeElement]).toEqual([true, "true", search]);
    expect(pickerNode.querySelector("[role=listbox]")).toBe(originalPanel);
    expect(document.querySelectorAll('[aria-label="Search projects"]')).toHaveLength(1);
    expect(picker.getSelection()).toEqual({ scope: "project", id: "a" });
    expect(changed).not.toHaveBeenCalled();
    expect(fetchRequest).toHaveBeenCalledTimes(1);
    expect(fetchRequest.mock.calls[0][1]?.method).not.toBe("POST");
  });

  it("rolls back conflicting edits and resets one command while preserving another user's shortcut", () => {
    const first = vi.fn(), second = vi.fn();
    const h = host([
      { id: "first", label: "First", action: first },
      { id: "second", label: "Second", action: second },
    ]);
    h.keymap.bind("global", "C-a", "first");
    h.keymap.bind("global", "C-b", "second");
    h.commands.open();
    applyShortcut(h.container, "First", "C-x");
    applyShortcut(h.container, "Second", "C-y");
    const saved = h.keymap.serializeOverrides();
    applyShortcut(h.container, "First", "C-y");
    expect(h.keymap.serializeOverrides()).toEqual(saved);
    expect(h.keymap.overrideConflicts()).toEqual([]);
    expect(h.container.querySelector('[role="status"]')?.textContent).toContain("Shortcut already used");
    h.commands.close();
    expect(key(document.body, { key: "a", ctrlKey: true }).defaultPrevented).toBe(false);
    expect(key(document.body, { key: "x", ctrlKey: true }).defaultPrevented).toBe(true);
    expect(key(document.body, { key: "y", ctrlKey: true }).defaultPrevented).toBe(true);
    expect([first.mock.calls.length, second.mock.calls.length]).toEqual([1, 1]);

    h.commands.open();
    shortcutButton(h.container, "First", "Reset shortcut").click();
    expect(h.keymap.serializeOverrides()).toEqual({ overrides: { second: "C-Y" }, unbound: [] });
    h.commands.close();
    expect(key(document.body, { key: "x", ctrlKey: true }).defaultPrevented).toBe(false);
    expect(key(document.body, { key: "a", ctrlKey: true }).defaultPrevented).toBe(true);
    expect(key(document.body, { key: "b", ctrlKey: true }).defaultPrevented).toBe(false);
    expect(key(document.body, { key: "y", ctrlKey: true }).defaultPrevented).toBe(true);
    expect([first.mock.calls.length, second.mock.calls.length]).toEqual([2, 2]);
  });

  it("refuses picker opening while a selection is awaiting acknowledgement and keeps selection payload validation", async () => {
    let accept!: () => void;
    const acknowledgement = new Promise<void>((resolve) => { accept = resolve; });
    const remember = vi.fn(() => acknowledgement);
    const registry = new CommandRegistry();
    const pickerNode = container();
    const picker = new ProjectSelector({ container: pickerNode, commands: registry,
      openCommandId: PROJECT_SELECTOR_OPEN,
      provider: { listProjects: async () => ({ projects, current: "a" }), rememberProject: remember } });
    mounted.push(picker);
    await picker.ready;
    const keymap = new Keymap({ registry });
    keymap.bind("global", "C-p", PROJECT_SELECTOR_OPEN);
    const commandsNode = container();
    const commands = new WorkspaceCommands({ container: commandsNode, registry, keymap, commandIds: [PROJECT_SELECTOR_OPEN] });
    mounted.push(commands);
    const changed = vi.fn();
    pickerNode.addEventListener(PROJECT_SELECTOR_CHANGE, changed);
    expect(registry.run(picker.selectCommandId, { via: "program" }, { scope: "project", id: "private" })).toBe(false);
    expect(remember).not.toHaveBeenCalled();

    trigger(pickerNode).click();
    (pickerNode.querySelectorAll<HTMLButtonElement>('[role="option"]')[1]).click();
    picker.close();
    expect(trigger(pickerNode).disabled).toBe(true);
    expect(registry.run(PROJECT_SELECTOR_OPEN, { via: "program" })).toBe(false);
    expect(key(document.body, { key: "p", ctrlKey: true }).defaultPrevented).toBe(false);
    commands.open();
    result(commandsNode, PROJECT_SELECTOR_OPEN).click();
    expect(trigger(pickerNode).getAttribute("aria-expanded")).toBe("false");
    expect(picker.getSelection()).toEqual({ scope: "project", id: "a" });
    expect(changed).not.toHaveBeenCalled();
    expect(remember).toHaveBeenCalledExactlyOnceWith("b");

    accept();
    await settle();
    expect(picker.getSelection()).toEqual({ scope: "project", id: "b" });
    expect(changed).toHaveBeenCalledTimes(1);
    expect(trigger(pickerNode).disabled).toBe(false);
  });

  it("refuses a shorter shortcut that would make an existing command sequence unreachable", () => {
    const first = vi.fn(), second = vi.fn();
    const h = host([
      { id: "first", label: "First", action: first },
      { id: "second", label: "Second", action: second },
    ]);
    h.keymap.bind("global", "C-a", "first");
    h.keymap.bind("global", "C-x C-b", "second");
    const saved = h.keymap.serializeOverrides();
    h.commands.open();
    applyShortcut(h.container, "First", "C-x");
    expect(h.keymap.serializeOverrides()).toEqual(saved);
    expect(h.container.querySelector('[role="status"]')?.textContent).toContain("Shortcut already used");
    h.commands.close();
    expect(key(document.body, { key: "x", ctrlKey: true }).defaultPrevented).toBe(true);
    expect([first.mock.calls.length, second.mock.calls.length]).toEqual([0, 0]);
    expect(key(document.body, { key: "b", ctrlKey: true }).defaultPrevented).toBe(true);
    expect(second).toHaveBeenCalledTimes(1);
    expect(key(document.body, { key: "a", ctrlKey: true }).defaultPrevented).toBe(true);
    expect(first).toHaveBeenCalledTimes(1);
  });

  it("keeps shortcut recovery usable when a mode or loaded preference hides a factory binding", () => {
    const first = vi.fn(), second = vi.fn();
    const h = host([
      { id: "first", label: "First", action: first },
      { id: "second", label: "Second", action: second },
    ]);
    h.keymap.bind("global", "C-a", "first");
    h.keymap.bind("global", "C-b", "second");
    h.keymap.bind("editor", "C-a", "second");
    h.keymap.activateMode("editor");
    h.commands.open();
    expect(shortcut(h.container, "First").value).toBe("");
    for (const label of ["Apply shortcut", "Disable shortcut", "Reset shortcut"]) {
      expect(shortcutButton(h.container, "First", label).disabled).toBe(false);
    }
    applyShortcut(h.container, "First", "C-j");
    h.commands.close();
    expect(key(document.body, { key: "j", ctrlKey: true }).defaultPrevented).toBe(true);
    expect(key(document.body, { key: "a", ctrlKey: true }).defaultPrevented).toBe(true);
    expect([first.mock.calls.length, second.mock.calls.length]).toEqual([1, 1]);

    h.keymap.loadOverrides({ overrides: { second: "C-a" } });
    h.commands.open();
    expect(shortcut(h.container, "First").value).toBe("");
    expect(shortcutButton(h.container, "First", "Apply shortcut").disabled).toBe(false);
    applyShortcut(h.container, "First", "C-j");
    expect(h.keymap.serializeOverrides()).toEqual({ overrides: { second: "C-A", first: "C-J" }, unbound: [] });
    h.commands.close();
    expect(key(document.body, { key: "j", ctrlKey: true }).defaultPrevented).toBe(true);
    expect(key(document.body, { key: "a", ctrlKey: true }).defaultPrevented).toBe(true);
    expect([first.mock.calls.length, second.mock.calls.length]).toEqual([2, 2]);
  });

  it("rolls back reset when another user shortcut occupies the factory chord, then succeeds after that shortcut is reset", () => {
    const first = vi.fn(), second = vi.fn();
    const h = host([
      { id: "first", label: "First", action: first },
      { id: "second", label: "Second", action: second },
    ]);
    h.keymap.bind("global", "C-a", "first");
    h.keymap.bind("global", "C-b", "second");
    h.commands.open();
    applyShortcut(h.container, "First", "C-x");
    applyShortcut(h.container, "Second", "C-a");
    const saved = h.keymap.serializeOverrides();
    shortcutButton(h.container, "First", "Reset shortcut").click();
    expect(h.keymap.serializeOverrides()).toEqual(saved);
    expect(h.container.querySelector('[role="status"]')?.textContent).toContain("Shortcut already used");
    h.commands.close();
    expect(key(document.body, { key: "x", ctrlKey: true }).defaultPrevented).toBe(true);
    expect(key(document.body, { key: "a", ctrlKey: true }).defaultPrevented).toBe(true);
    expect([first.mock.calls.length, second.mock.calls.length]).toEqual([1, 1]);

    h.commands.open();
    shortcutButton(h.container, "Second", "Reset shortcut").click();
    shortcutButton(h.container, "First", "Reset shortcut").click();
    expect(h.keymap.serializeOverrides()).toEqual({ overrides: {}, unbound: [] });
    h.commands.close();
    expect(key(document.body, { key: "x", ctrlKey: true }).defaultPrevented).toBe(false);
    expect(key(document.body, { key: "a", ctrlKey: true }).defaultPrevented).toBe(true);
    expect(key(document.body, { key: "b", ctrlKey: true }).defaultPrevented).toBe(true);
    expect([first.mock.calls.length, second.mock.calls.length]).toEqual([2, 2]);
  });

  it("mounts the existing scoped picker into the shared registry and leaves user scope without a picker or command", async () => {
    const registry = new CommandRegistry();
    const listProjects = vi.fn(async () => ({ projects, current: "a" }));
    const userNode = container();
    expect(mountProjectSelectorByScope({ container: userNode, scope: "user", provider: { listProjects },
      commands: registry, selectCommandId: "user:select", openCommandId: "user:open" })).toBeNull();
    expect(userNode.childNodes).toHaveLength(0);
    expect(registry.ids()).toEqual([]);
    expect(listProjects).not.toHaveBeenCalled();

    const pickerNode = container();
    const picker = mountProjectSelectorByScope({ container: pickerNode, scope: "project", provider: { listProjects },
      commands: registry, selectCommandId: "workspace:select", openCommandId: "workspace:open" });
    expect(picker).toBeInstanceOf(ProjectSelector);
    mounted.push(picker!);
    await picker!.ready;
    expect(picker!.commands).toBe(registry);
    expect(registry.ids()).toEqual(["workspace:open", "workspace:select"]);
    const commandsNode = container();
    const commands = new WorkspaceCommands({ container: commandsNode, registry,
      keymap: new Keymap({ registry }), commandIds: ["workspace:open"] });
    mounted.push(commands);
    commands.open();
    result(commandsNode, "workspace:open").click();
    expect(trigger(pickerNode).getAttribute("aria-expanded")).toBe("true");
    expect(document.activeElement).toBe(pickerNode.querySelector("input"));
    expect(document.querySelectorAll('[aria-label="Search projects"]')).toHaveLength(1);
    expect(listProjects).toHaveBeenCalledTimes(1);
  });

  it("returns focus to the visible trigger when palette Enter invokes a command that reports no effect", () => {
    const run = vi.fn(() => false);
    const h = host([{ id: "noop", label: "No effect", action: run }]);
    h.commands.open();
    expect(key(filter(h.container), { key: "Enter" }).defaultPrevented).toBe(false);
    expect(run).toHaveBeenCalledTimes(1);
    expect(trigger(h.container).getAttribute("aria-expanded")).toBe("false");
    expect(document.activeElement).toBe(trigger(h.container));
  });

  it("preserves native keys for disabled shortcuts, inactive modes, and missing commands", () => {
    const disabled = vi.fn(), inactive = vi.fn();
    const h = host([
      { id: "disabled", label: "Disabled", action: disabled },
      { id: "mode", label: "Mode command", action: inactive, modes: new Set(["editor"]) },
    ], ["disabled", "mode", "missing"]);
    h.keymap.bind("global", "C-d", "disabled");
    h.keymap.bind("global", "C-m", "mode");
    h.keymap.bind("global", "C-u", "missing");
    h.commands.open();
    shortcutButton(h.container, "Disabled", "Disable shortcut").click();
    expect(h.container.querySelector('[data-command-id="missing"]')).toBeNull();
    h.keymap.activateMode("editor");
    h.commands.refresh();
    const staleModeResult = result(h.container, "mode");
    h.keymap.deactivateMode();
    staleModeResult.click();
    h.commands.close();
    for (const letter of ["d", "m", "u"]) {
      expect(key(document.body, { key: letter, ctrlKey: true }).defaultPrevented).toBe(false);
    }
    expect([disabled.mock.calls.length, inactive.mock.calls.length]).toEqual([0, 0]);
    h.keymap.activateMode("editor");
    h.commands.refresh();
    expect(key(document.body, { key: "m", ctrlKey: true }).defaultPrevented).toBe(true);
    expect(inactive).toHaveBeenCalledTimes(1);
  });

  it("leaves editable text keys alone and suppresses composing Enter in both palette and picker", async () => {
    const ordinary = vi.fn(), optedIn = vi.fn();
    const h = host([
      { id: "ordinary", label: "Ordinary", action: ordinary },
      { id: "opted-in", label: "Opted in", action: optedIn },
    ]);
    h.keymap.bind("global", "C-r", "ordinary");
    h.keymap.bind("global", "C-i", "opted-in", true);
    h.commands.open();
    expect(key(filter(h.container), { key: "r", ctrlKey: true }).defaultPrevented).toBe(false);
    const editor = document.createElement("div");
    editor.setAttribute("contenteditable", "true");
    document.body.append(editor);
    expect(key(editor, { key: "r", ctrlKey: true }).defaultPrevented).toBe(false);
    expect(key(filter(h.container), { key: "i", ctrlKey: true, isComposing: true }).defaultPrevented).toBe(false);
    for (const ime of [{ isComposing: true }, { keyCode: 229 }]) {
      expect(key(filter(h.container), { key: "Enter", ...ime }).defaultPrevented).toBe(false);
    }
    filter(h.container).dispatchEvent(new CompositionEvent("compositionstart", { bubbles: true }));
    expect(key(filter(h.container), { key: "Enter", isComposing: false, keyCode: 0 }).defaultPrevented).toBe(false);
    filter(h.container).dispatchEvent(new CompositionEvent("compositionend", { bubbles: true }));
    expect([ordinary.mock.calls.length, optedIn.mock.calls.length]).toEqual([0, 0]);
    expect(trigger(h.container).getAttribute("aria-expanded")).toBe("true");

    const remember = vi.fn(async () => {});
    const pickerNode = container();
    const picker = new ProjectSelector({ container: pickerNode,
      provider: { listProjects: async () => ({ projects, current: "a" }), rememberProject: remember } });
    mounted.push(picker);
    await picker.ready;
    const changed = vi.fn();
    pickerNode.addEventListener(PROJECT_SELECTOR_CHANGE, changed);
    trigger(pickerNode).click();
    const search = pickerNode.querySelector<HTMLInputElement>("input")!;
    search.value = "Authorized B";
    search.dispatchEvent(new Event("input", { bubbles: true }));
    for (const ime of [{ isComposing: true }, { keyCode: 229 }]) {
      expect(key(search, { key: "Enter", ...ime }).defaultPrevented).toBe(false);
    }
    search.dispatchEvent(new CompositionEvent("compositionstart", { bubbles: true }));
    expect(key(search, { key: "Enter", isComposing: false, keyCode: 0 }).defaultPrevented).toBe(false);
    search.dispatchEvent(new CompositionEvent("compositionend", { bubbles: true }));
    await settle();
    expect(remember).not.toHaveBeenCalled();
    expect(changed).not.toHaveBeenCalled();
    expect(picker.getSelection()).toEqual({ scope: "project", id: "a" });
    expect(trigger(pickerNode).getAttribute("aria-expanded")).toBe("true");
    expect(key(search, { key: "Enter" }).defaultPrevented).toBe(true);
    await settle();
    expect(remember).toHaveBeenCalledExactlyOnceWith("b");
    expect(changed).toHaveBeenCalledTimes(1);
    expect(picker.getSelection()).toEqual({ scope: "project", id: "b" });
  });

  it("detaches on destroy, rejects concurrent ownership, and remounts without duplicate dispatch", () => {
    const run = vi.fn();
    const h = host([{ id: "run", label: "Run", action: run }]);
    h.keymap.bind("global", "C-r", "run");
    expect(() => new WorkspaceCommands({ container: container(), registry: h.registry,
      keymap: h.keymap, commandIds: ["run"] })).toThrow();
    expect(() => new WorkspaceCommands({ container: container(), registry: new CommandRegistry(),
      keymap: h.keymap, commandIds: ["run"] })).toThrow();
    expect(key(document.body, { key: "r", ctrlKey: true }).defaultPrevented).toBe(true);
    h.commands.open();
    const staleResult = result(h.container, "run");
    h.commands.destroy();
    staleResult.click();
    expect(run).toHaveBeenCalledTimes(1);
    expect(key(document.body, { key: "r", ctrlKey: true }).defaultPrevented).toBe(false);
    const remounted = new WorkspaceCommands({ container: h.container, registry: h.registry,
      keymap: h.keymap, commandIds: ["run"] });
    mounted.push(remounted);
    expect(key(document.body, { key: "r", ctrlKey: true }).defaultPrevented).toBe(true);
    expect(run).toHaveBeenCalledTimes(2);
    expect(h.registry.has("run")).toBe(true);
  });

  it("cleans up only the picker's owned commands and leaves opening opt-in", async () => {
    const registry = new CommandRegistry();
    const legacy = new ProjectSelector({ container: container(), commands: registry, projects });
    mounted.push(legacy);
    expect(legacy.openCommandId).toBeNull();
    expect(registry.has(PROJECT_SELECTOR_OPEN)).toBe(false);
    legacy.destroy();
    const owned = new ProjectSelector({ container: container(), commands: registry, projects,
      openCommandId: PROJECT_SELECTOR_OPEN });
    mounted.push(owned);
    await owned.ready;
    expect(registry.ids()).toEqual([PROJECT_SELECTOR_OPEN, owned.selectCommandId]);
    owned.destroy();
    expect(registry.ids()).toEqual([]);
    const picker = new ProjectSelector({ container: container(), commands: registry, projects,
      openCommandId: PROJECT_SELECTOR_OPEN });
    mounted.push(picker);
    await picker.ready;
    const selectId = picker.selectCommandId;
    const replacement = vi.fn();
    registry.set({ id: PROJECT_SELECTOR_OPEN, label: "Replacement", action: replacement });
    trigger(picker.container).click();
    expect(replacement).not.toHaveBeenCalled();
    expect(trigger(picker.container).getAttribute("aria-expanded")).toBe("false");
    picker.destroy();
    expect(registry.has(selectId)).toBe(false);
    expect(registry.has(PROJECT_SELECTOR_OPEN)).toBe(true);
    registry.run(PROJECT_SELECTOR_OPEN);
    expect(replacement).toHaveBeenCalledTimes(1);
  });

  it("renders command labels and editable shortcut text without interpreting markup", () => {
    const label = '<img src=x onerror="alert(1)">Open <script>alert(2)</script>';
    const h = host([{ id: "unsafe", label, action: vi.fn() }]);
    h.keymap.bind("global", "C-o", "unsafe");
    h.commands.open();
    expect(result(h.container, "unsafe").textContent).toContain(label);
    expect(shortcut(h.container, label).getAttribute("aria-label")).toBe(`Shortcut for ${label}`);
    expect(h.container.querySelector("img, script")).toBeNull();
    filter(h.container).value = "<img>";
    filter(h.container).dispatchEvent(new Event("input", { bubbles: true }));
    expect(h.container.querySelector("img, script")).toBeNull();
  });
});
