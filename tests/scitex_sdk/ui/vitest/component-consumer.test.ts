import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Combobox } from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/ts/app/combobox";
import { Dropdown } from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/ts/app/dropdown";
import { DataTableManager, TableData, TableRendering, TableSelection, TableFillHandle } from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/ts/app/data-table";
import { CommandRegistry } from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/ts/shell/keymap";
import { cascadeCollapse, findAdjacentPanel, getMaxAllowedWidth } from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/ts/shell/resizer/_cascade";

const cleanups: Array<() => void> = [];
const $ = <T extends Element = HTMLElement>(selector: string): T => document.querySelector<T>(selector)!;
const input = (el: HTMLInputElement, value: string) => {
  el.value = value;
  el.setSelectionRange(value.length, value.length);
  el.dispatchEvent(new Event("input", { bubbles: true }));
};
const key = (el: HTMLElement, value: string) => el.dispatchEvent(new KeyboardEvent("keydown", { key: value, bubbles: true, cancelable: true }));

beforeEach(() => {
  document.body.innerHTML = '<button id="trigger">Choose</button><div id="menu"></div><div id="table" class="data-table-container"></div>';
  localStorage.clear();
  vi.stubGlobal("requestAnimationFrame", vi.fn(() => 1));
  const scrollDescriptor = Object.getOwnPropertyDescriptor(HTMLElement.prototype, "scrollIntoView");
  Object.defineProperty(HTMLElement.prototype, "scrollIntoView", { configurable: true, value: vi.fn() });
  cleanups.push(() => {
    if (scrollDescriptor) Object.defineProperty(HTMLElement.prototype, "scrollIntoView", scrollDescriptor);
    else Reflect.deleteProperty(HTMLElement.prototype, "scrollIntoView");
  });
});

afterEach(() => {
  for (const cleanup of cleanups.splice(0)) cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  document.body.innerHTML = "";
});

describe("consumer popovers", () => {
  it("combobox filters, rejects disabled selection, and emits the chosen value", () => {
    const onChange = vi.fn();
    const event = vi.fn();
    $("#menu").addEventListener("combobox:change", event);
    const box = new Combobox({ container: "#menu", trigger: "#trigger", items: [
      { value: "blocked", label: "Disabled", disabled: true },
      { value: "beta", label: "Beta" }, { value: "gamma", label: "Gamma" },
    ], onChange });
    cleanups.push(() => box.destroy());
    box.show();
    key($(".stx-app-combobox__input"), "Enter");
    expect(onChange).not.toHaveBeenCalled();
    expect($("#menu").style.display).toBe("block");
    input($(".stx-app-combobox__input"), "bt");
    expect(document.querySelectorAll(".stx-app-combobox__item")).toHaveLength(1);
    key($(".stx-app-combobox__input"), "Enter");
    expect(box.getValue()).toBe("beta");
    expect($("#trigger").textContent).toBe("Beta");
    expect(onChange).toHaveBeenCalledWith({ value: "beta", label: "Beta" });
    expect(event.mock.calls[0][0].detail.value).toBe("beta");
    expect($("#menu").style.display).toBe("none");
  });

  it("combobox supports arrow selection, dynamic options, creation, and escape focus", () => {
    const onCreate = vi.fn();
    const onChange = vi.fn();
    const box = new Combobox({ container: "#menu", trigger: "#trigger", items: [
      { value: "a", label: "Alpha" }, { value: "b", label: "Beta" },
    ], onChange, onCreate });
    cleanups.push(() => box.destroy());
    box.show();
    key($(".stx-app-combobox__input"), "ArrowDown");
    key($(".stx-app-combobox__input"), "Enter");
    expect(box.getValue()).toBe("b");
    box.setValue("a");
    expect(onChange).toHaveBeenCalledTimes(1);
    box.show();
    box.setItems([{ value: "c", label: "Created" }]);
    expect($(".stx-app-combobox__item").textContent).toBe("Created");
    input($(".stx-app-combobox__input"), "Novel");
    key($(".stx-app-combobox__input"), "Enter");
    expect(onCreate).toHaveBeenCalledWith("Novel");
    box.show();
    expect($<HTMLInputElement>(".stx-app-combobox__input").value).toBe("");
    key($(".stx-app-combobox__input"), "Escape");
    expect(document.activeElement).toBe($("#trigger"));
  });

  it("dropdown preserves filter caret, single-match actions, and reset on reopening", () => {
    const onClick = vi.fn();
    const onSelect = vi.fn();
    const menu = new Dropdown({ container: "#menu", trigger: "#trigger", filter: true, items: [
      { id: "a", label: "Alpha", onClick }, { id: "sep", label: "", separator: true },
      { id: "b", label: "Beta" },
    ], onSelect });
    cleanups.push(() => menu.destroy());
    $("#trigger").click();
    input($(".stx-app-dropdown__filter"), "aph");
    const filter = $<HTMLInputElement>(".stx-app-dropdown__filter");
    expect(document.activeElement).toBe(filter);
    expect(filter.selectionStart).toBe(3);
    expect(document.querySelectorAll(".stx-app-dropdown__item")).toHaveLength(1);
    expect(document.querySelector(".stx-app-dropdown__separator")).toBeNull();
    key(filter, "Enter");
    expect(onClick).toHaveBeenCalledTimes(1);
    expect(onSelect.mock.calls[0][0].id).toBe("a");
    menu.show();
    expect($<HTMLInputElement>(".stx-app-dropdown__filter").value).toBe("");
    expect(document.querySelectorAll(".stx-app-dropdown__item")).toHaveLength(2);
    input($(".stx-app-dropdown__filter"), "missing");
    expect($(".stx-app-dropdown__empty").textContent).toBe("No matches");
    menu.setItems([{ id: "new", label: "Missing item" }]);
    expect($(".stx-app-dropdown__item").textContent).toBe("Missing item");
    document.body.click();
    expect($("#menu").style.display).toBe("none");
  });

  it("destroying a dropdown permits one replacement on the same trigger", () => {
    const config = { container: "#menu", trigger: "#trigger", items: [{ id: "a", label: "Alpha" }] };
    new Dropdown(config).destroy();
    const replacement = new Dropdown(config);
    cleanups.push(() => replacement.destroy());
    $("#trigger").click();
    expect($("#menu").style.display).toBe("block");
    $("#trigger").click();
    expect($("#menu").style.display).toBe("none");
  });
});

describe("consumer data table", () => {
  it("retains CSV headers and escaped cells for both accepted array flag values", () => {
    const manager = new DataTableManager({ container: "#table", readOnly: true });
    for (const flag of [true, false]) {
      manager.loadFromArray([["Name", "Amount"], ['comma, "quote"', "2"]], flag);
      expect(manager.getCurrentData()).toEqual({ columns: ["Name", "Amount"], rows: [{ Name: 'comma, "quote"', Amount: 2 }] });
      expect(manager.exportToCSV()).toContain('"comma, ""quote"""');
      expect(document.querySelector("#table .editable-table")).toBeNull();
      expect($("#table td").textContent).toBe('comma, "quote"');
    }
  });

  it("forwards legacy status and column callbacks and preserves blank table size", () => {
    const status = vi.fn();
    const columns = vi.fn();
    const manager = new DataTableManager("#table", status, columns, vi.fn());
    manager.loadFromCSVContent("Label\tValue\nSample\t4", "sample.tsv");
    expect(columns).toHaveBeenCalledTimes(1);
    expect(status).toHaveBeenCalledWith("Loaded sample.tsv - 1 rows × 2 columns");
    expect(manager.getCurrentData()?.rows[0]).toEqual({ Label: "Sample", Value: 4 });
    const data = new TableData(status).initializeBlankTable();
    expect(data.rows).toHaveLength(1000);
    expect(data.columns).toHaveLength(32);
    expect(data.columns.slice(25, 28)).toEqual(["26", "27", "28"]);
  });

  it("edits data cells and maintains the active cell after a range drag", () => {
    const manager = new DataTableManager("#table");
    manager.loadFromCSVContent("A,B\n1,2\n3,4");
    const first = $("#table td[data-row='0'][data-col='0']");
    first.dispatchEvent(new MouseEvent("dblclick", { bubbles: true }));
    expect(first.classList.contains("editing")).toBe(true);
    first.textContent = "7";
    first.dispatchEvent(new Event("blur"));
    expect(manager.getCurrentData()?.rows[0].A).toBe(7);
    const cellAt = (row: number, col: number) => document.querySelector<HTMLElement>(`#table td[data-row='${row}'][data-col='${col}']`);
    const selection = new TableSelection(cellAt, vi.fn());
    selection.setContainerSelector("#table");
    selection.handleCellMouseDown(new MouseEvent("mousedown"), cellAt(1, 1)!);
    selection.handleCellMouseOver(cellAt(0, 0)!);
    selection.stopSelection();
    expect(selection.getSelectionBounds()).toEqual({ startRow: 0, endRow: 1, startCol: 0, endCol: 1 });
    expect(selection.getCurrentCell()).toEqual({ row: 0, col: 0 });
    expect(cellAt(0, 0)?.classList.contains("current")).toBe(true);
    expect(document.querySelectorAll("#table td.selected")).toHaveLength(4);
  });

  it("keeps column widths and moves the virtual row window when scrolling", () => {
    Object.defineProperty($("#table"), "clientHeight", { value: 330 });
    const dataset = { columns: ["A", "B"], rows: Array.from({ length: 1000 }, (_, i) => ({ A: i, B: `Row ${i}` })) };
    const rendering = new TableRendering(() => dataset, vi.fn(), vi.fn());
    rendering.setContainerSelector("#table");
    rendering.setColumnWidth(1, 140);
    rendering.renderEditableDataTable();
    expect($("#data-table-dynamic-widths").textContent).toContain("width: 140px");
    expect(document.querySelectorAll("#table tbody tr")).toHaveLength(20);
    $("#table").scrollTop = 3300;
    rendering.updateVisibleRange();
    expect(rendering.getVisibleRowRange()).toEqual({ start: 90, end: 120 });
    expect($("#table tbody tr").getAttribute("data-row-index")).toBe("90");
    expect(document.querySelectorAll("#table tbody tr")).toHaveLength(30);
    expect(rendering.getColumnWidth(1)).toBe(140);
  });

  it("fills from the selected source row and cleans up drag preview", () => {
    const manager = new DataTableManager("#table");
    manager.loadFromCSVContent("A,B\n5,6\n0,0\n0,0");
    const render = vi.fn();
    const status = vi.fn();
    const cellAt = (row: number, col: number) => document.querySelector<HTMLElement>(`#table td[data-row='${row}'][data-col='${col}']`);
    const pointDescriptor = Object.getOwnPropertyDescriptor(document, "elementFromPoint");
    Object.defineProperty(document, "elementFromPoint", { configurable: true, value: () => cellAt(2, 1) });
    cleanups.push(() => {
      if (pointDescriptor) Object.defineProperty(document, "elementFromPoint", pointDescriptor);
      else Reflect.deleteProperty(document, "elementFromPoint");
    });
    const fill = new TableFillHandle({ getCurrentData: () => manager.getCurrentData(), setCurrentData: data => manager.setCurrentData(data), getCellAt: cellAt, renderCallback: render, statusBarCallback: status });
    fill.handleFillHandleMouseDown(new MouseEvent("mousedown"), { row: 0, col: 0 }, { row: 0, col: 1 });
    document.dispatchEvent(new MouseEvent("mousemove", { clientX: 10, clientY: 10 }));
    expect(document.querySelectorAll(".fill-preview").length).toBeGreaterThan(0);
    document.dispatchEvent(new MouseEvent("mouseup"));
    expect(manager.getCurrentData()?.rows).toEqual([{ A: 5, B: 6 }, { A: 5, B: 6 }, { A: 5, B: 6 }]);
    expect(document.querySelector(".fill-preview")).toBeNull();
    expect(render).toHaveBeenCalledTimes(1);
    expect(status).toHaveBeenCalledWith("Fill completed");
    document.dispatchEvent(new MouseEvent("mousemove"));
    expect(document.querySelector(".fill-preview")).toBeNull();
  });
});

describe("consumer command and cascade contracts", () => {
  it("keeps caller metadata separate from third-slot payload and consumption", () => {
    const registry = new CommandRegistry();
    const action = vi.fn(() => false);
    registry.set({ id: "save", label: "Save", action });
    const payload = { document: "example" };
    expect(registry.run("save", { via: "keyboard" }, payload)).toBe(false);
    expect(action).toHaveBeenLastCalledWith(payload);
    registry.run("save", undefined, payload);
    expect(action).toHaveBeenLastCalledWith(payload);
    registry.run("save", { via: "button" });
    expect(action).toHaveBeenLastCalledWith(undefined);
  });

  it("skips collapsed and non-resizable siblings and persists cascade collapse", () => {
    document.body.innerHTML = '<div class="workspace-three-col"><div class="ws-ai-pane"><div id="first" class="stx-shell-sidebar"></div><div data-h-resizer></div></div><div class="ws-module-pane"></div><div class="ws-worktree-pane"><div class="stx-shell-sidebar collapsed"></div><div data-h-resizer></div></div><div class="ws-viewer-pane"><div id="last" class="stx-shell-sidebar" style="width:200px;flex-grow:1;flex-shrink:0"></div><div data-h-resizer data-storage-key="viewer" data-threshold="60"></div></div></div>';
    const adjacent = findAdjacentPanel($("#first"), "right");
    expect(adjacent).toEqual({ panel: $("#last"), storageKey: "viewer", thresholdPx: 60 });
    cascadeCollapse(adjacent!.panel, adjacent!.storageKey);
    expect($("#last").classList.contains("collapsed")).toBe(true);
    expect($("#last").style.width).toBe("");
    expect($("#last").style.flexGrow).toBe("");
    expect(localStorage.getItem("viewer-collapsed")).toBe("true");
    expect(findAdjacentPanel($("#first"), "right")).toBeNull();
    expect(findAdjacentPanel($("#last"), "left")?.panel).toBe($("#first"));
  });

  it("reserves the module minimum and actual other pane widths", () => {
    document.body.innerHTML = '<div class="workspace-three-col"><div class="ws-ai-pane"><div id="first"></div></div><div class="ws-module-pane"></div><div class="ws-viewer-pane"></div></div>';
    Object.defineProperty($(".workspace-three-col"), "clientWidth", { value: 1000 });
    Object.defineProperty($(".ws-module-pane"), "offsetWidth", { value: 500 });
    Object.defineProperty($(".ws-viewer-pane"), "offsetWidth", { value: 200 });
    expect(getMaxAllowedWidth($("#first"))).toBe(760);
    document.body.innerHTML = '<div id="standalone"></div>';
    expect(getMaxAllowedWidth($("#standalone"))).toBe(Infinity);
  });
});
