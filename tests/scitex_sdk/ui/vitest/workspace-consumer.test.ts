/** Public workspace behaviour used by consumers that bundle shared UI source. */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  WorkspaceFilesTree,
  TreeStateManager,
  TreeRenderer,
  TreeFilter,
  type FileTreeAdapter,
  type TreeItem,
} from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/ts/shell/workspace-files-tree";
import { SessionsPanel } from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/ts/shell/chat/_sessions-panel";
import { initResizer } from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/ts/shell/workspace-panel-resizer/resizer";

const entries = (): TreeItem[] => [
  { name: "alpha.csv", path: "alpha.csv", type: "file" },
  { name: "beta.csv", path: "beta.csv", type: "file" },
  { name: "plots", path: "plots", type: "directory", children: [
    { name: "figure.png", path: "plots/figure.png", type: "file" },
  ] },
];
const docListeners: Array<[string, EventListenerOrEventListenerObject]> = [];
const winListeners: Array<[string, EventListenerOrEventListenerObject]> = [];

beforeEach(() => {
  document.body.innerHTML = '<div id="files"></div>';
  localStorage.clear();
  sessionStorage.clear();
  Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
    configurable: true, value: vi.fn(),
  });
  const docAdd = document.addEventListener.bind(document);
  const winAdd = window.addEventListener.bind(window);
  vi.spyOn(document, "addEventListener").mockImplementation((type, listener, options) => {
    docListeners.push([type, listener]);
    docAdd(type, listener, options);
  });
  vi.spyOn(window, "addEventListener").mockImplementation((type, listener, options) => {
    winListeners.push([type, listener]);
    winAdd(type, listener, options);
  });
});

afterEach(() => {
  for (const [type, listener] of docListeners.splice(0)) document.removeEventListener(type, listener);
  for (const [type, listener] of winListeners.splice(0)) window.removeEventListener(type, listener);
  vi.restoreAllMocks();
});

async function mount(adapterOverrides: Partial<FileTreeAdapter> = {}) {
  const adapter: FileTreeAdapter = {
    fetchTree: vi.fn(async () => ({ success: true, tree: entries() })),
    getCsrfToken: () => "test-token",
    ...adapterOverrides,
  };
  const opened = vi.fn();
  const tree = new WorkspaceFilesTree({
    mode: "all", containerId: "files", ownerUsername: "test-owner",
    projectSlug: "test-project", adapter, onFileSelect: opened,
  });
  await tree.initialize();
  return { tree, adapter, opened, container: document.getElementById("files")! };
}

describe("workspace consumer events", () => {
  it("retains the public renderer call form and per-item git badges", () => {
    const state = new TreeStateManager("owner", "project");
    const renderer = new TreeRenderer({
      mode: "all", containerId: "files", ownerUsername: "owner", projectSlug: "project",
      adapter: { fetchTree: async () => ({ success: true, tree: [] }), getCsrfToken: () => "" },
    }, state, new TreeFilter("all"));
    const files: TreeItem[] = [
      { name: "figure.png", path: "figure.png", type: "file", git_status: { status: "M", staged: false } },
    ];
    const output = renderer.render(files, { staged: 0, modified: 1, untracked: 0 });
    expect(output).toContain('data-git-status="M"');
    expect(output).toContain("wft-icon-modified");
  });

  it("opens the selected file through both pointer and arrow-key navigation", async () => {
    const { container, opened } = await mount();
    container.querySelector('[data-path="alpha.csv"]')!.dispatchEvent(
      new MouseEvent("dblclick", { bubbles: true }),
    );
    expect(opened).toHaveBeenLastCalledWith("alpha.csv", expect.objectContaining({ type: "file" }));
    container.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }));
    container.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    expect(opened).toHaveBeenLastCalledWith("beta.csv", expect.objectContaining({ type: "file" }));
  });

  it("retains search wiring after initialization", async () => {
    const { container, tree } = await mount();
    container.dispatchEvent(new KeyboardEvent("keydown", { key: "k", ctrlKey: true, bubbles: true }));
    expect(container.querySelector(".wft-search-hidden")).toBeNull();
    const input = container.querySelector("input")!;
    input.value = "alpha";
    input.dispatchEvent(new Event("input", { bubbles: true }));
    await vi.waitFor(() => expect(tree.getSearchQuery()).toBe("alpha"));
    expect(container.querySelector('[data-path="alpha.csv"]')!.classList).toContain("wft-search-match");
    input.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    expect(tree.getSearchQuery()).toBe("");
    expect(container.querySelector(".wft-search-hidden")).not.toBeNull();
  });

  it("keeps root git counts and action callbacks in their intended positions", async () => {
    const stageAll = vi.fn(async () => ({ success: true }));
    const { container } = await mount({
      fetchGitStatus: async () => ({ success: true, files: [
        { path: "alpha.csv", status: "M", staged: false },
        { path: "beta.csv", status: "A", staged: true },
      ] }),
      gitStageAll: stageAll,
    });
    container.querySelector(".wft-root")!.dispatchEvent(
      new MouseEvent("contextmenu", { bubbles: true, clientX: 20, clientY: 20 }),
    );
    const stage = [...document.querySelectorAll<HTMLElement>(".wft-context-item")]
      .find(el => el.textContent?.includes("Stage All (1)"))!;
    expect(stage).toBeDefined();
    stage.click();
    await vi.waitFor(() => expect(stageAll).toHaveBeenCalledOnce());
  });

  it("passes drag-drop operations to the adapter and refreshes the tree", async () => {
    const moveFile = vi.fn(async () => ({ success: true }));
    const { container, adapter } = await mount({ moveFile });
    const data = new Map([
      ["text/plain", "alpha.csv"],
      ["application/x-wft-operation", "move"],
    ]);
    const drop = new Event("drop", { bubbles: true, cancelable: true });
    Object.defineProperty(drop, "dataTransfer", { value: {
      files: [], types: ["application/x-wft-internal"],
      getData: (key: string) => data.get(key) || "",
    } });
    container.querySelector('[data-path="plots"]')!.dispatchEvent(drop);
    await vi.waitFor(() => expect(moveFile).toHaveBeenCalledWith("alpha.csv", "plots/alpha.csv"));
    await vi.waitFor(() => expect(adapter.fetchTree).toHaveBeenCalledTimes(2));
  });

  it("shares expansion while retaining selection separately for each workspace mode", () => {
    const figures = new TreeStateManager("owner", "project", "vis");
    figures.expand("plots");
    figures.selectSingle("plots/figure.png");
    const writer = new TreeStateManager("owner", "project", "writer");
    expect(writer.isExpanded("plots")).toBe(true);
    expect(writer.getSelected()).toBeNull();
    writer.selectSingle("manuscript.tex");
    expect(new TreeStateManager("owner", "project", "vis").getSelected()).toBe("plots/figure.png");
  });

  it("persists panel collapse through the shared resizer", () => {
    document.body.innerHTML = '<div class="workspace-three-col" style="display:flex;flex-direction:row">' +
      '<div class="ws-worktree-pane"><div id="panel" class="stx-shell-sidebar"></div></div>' +
      '<div id="handle"></div><div class="ws-module-pane"></div></div>';
    const panel = document.getElementById("panel")!;
    Object.defineProperty(panel, "offsetWidth", { get: () => 200 });
    const layout = document.querySelector<HTMLElement>(".workspace-three-col")!;
    Object.defineProperty(layout, "offsetWidth", { get: () => 1000 });
    initResizer("consumer", {
      resizerId: "handle", targetPanel: "#panel", minWidth: 80,
      storageKey: "width", collapseStorageKey: "panel-collapsed", resizeDirection: "left",
    });
    document.getElementById("handle")!.dispatchEvent(new MouseEvent("mousedown", { clientX: 200 }));
    document.dispatchEvent(new MouseEvent("mousemove", { clientX: 0 }));
    document.dispatchEvent(new MouseEvent("mouseup"));
    expect(panel.classList).toContain("collapsed");
    expect(localStorage.getItem("panel-collapsed")).toBe("true");
  });
});

it("renders and switches sessions using the supplied adapter", async () => {
  document.body.innerHTML = '<button class="stx-shell-ai-new-chat">New Chat</button><div id="sessions"></div>';
  const switched = vi.fn();
  const cleared = vi.fn();
  const panel = new SessionsPanel();
  panel.init(document.getElementById("sessions")!, {
    listSessions: async () => [
      { id: 1, title: "First", updated_at: "" },
      { id: 2, title: "Second", updated_at: "" },
    ],
    getMessages: async id => ({ session_id: id, title: "Second", messages: [
      { role: "assistant", content: "Saved reply" },
    ] }),
    createSession: async () => ({ id: 3, title: "New" }),
    deleteSession: async () => {},
    addMessage: async () => {},
  }, switched, cleared);
  await vi.waitFor(() => expect(document.querySelectorAll(".stx-shell-ai-session-item")).toHaveLength(2));
  document.querySelector<HTMLElement>('[data-session-id="2"]')!.click();
  await vi.waitFor(() => expect(switched).toHaveBeenCalledWith(
    [{ role: "assistant", content: "Saved reply" }], 2,
  ));
  expect(panel.getSessionId()).toBe(2);
  document.querySelector<HTMLButtonElement>(".stx-shell-ai-new-chat")!.click();
  expect(panel.getSessionId()).toBeNull();
  expect(cleared).toHaveBeenCalledOnce();
});
