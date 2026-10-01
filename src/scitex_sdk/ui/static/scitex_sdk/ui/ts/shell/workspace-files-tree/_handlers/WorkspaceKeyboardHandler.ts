/**
 * Workspace Keyboard Handler - Ported from scitex-cloud (no API deps)
 */
import type { TreeConfig, TreeItem } from "../types";
import type { TreeStateManager } from "../_TreeState";
import type { SelectionHandler } from "./SelectionHandler";
import type { ClipboardHandler } from "./ClipboardHandler";
import type { UndoRedoHandler } from "./UndoRedoHandler";
import type { ContextMenuHandler } from "./ContextMenuHandler";
import type { FileActions } from "./FileActions";
import { TreeUtils } from "./TreeUtils";

export interface KeyboardHandlerCallbacks {
  isItemDirectory: (path: string) => boolean;
  getParentPath: (path: string) => string;
  showSearchInput: () => void;
  showMessage: (message: string, type: "success" | "error" | "info") => void;
  handleContextMenuAction: (action: string, path: string) => Promise<void>;
  refresh: () => Promise<void>;
  getTreeData: () => TreeItem[];
}

export class WorkspaceKeyboardHandler {
  private boundHandler: ((e: KeyboardEvent) => void) | null = null;

  constructor(
    private config: TreeConfig,
    private container: HTMLElement,
    private stateManager: TreeStateManager,
    private selectionHandler: SelectionHandler,
    private clipboardHandler: ClipboardHandler,
    private undoRedoHandler: UndoRedoHandler,
    private contextMenuHandler: ContextMenuHandler,
    private fileActions: FileActions,
    private callbacks: KeyboardHandlerCallbacks,
  ) {}

  initialize(): void {
    this.container.setAttribute("tabindex", "0");
    this.container.addEventListener("click", (e) => {
      const target = e.target as HTMLElement;
      if (
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.tagName === "BUTTON" ||
        target.closest("button") ||
        target.isContentEditable
      )
        return;
      this.container.focus();
    });
    this.boundHandler = (e: KeyboardEvent) => this.handleKeydown(e);
    document.addEventListener("keydown", this.boundHandler);
  }

  destroy(): void {
    if (this.boundHandler) {
      document.removeEventListener("keydown", this.boundHandler);
      this.boundHandler = null;
    }
  }

  private handleKeydown(e: KeyboardEvent): void {
    const target = e.target as HTMLElement;
    if (
      target.tagName === "INPUT" ||
      target.tagName === "TEXTAREA" ||
      target.isContentEditable
    )
      return;
    const activeElement = document.activeElement as HTMLElement;
    if (
      activeElement?.closest(
        ".monaco-editor, .xterm, .terminal-container, #editor-container",
      )
    )
      return;

    const ctrlOrMeta = e.ctrlKey || e.metaKey;
    if (ctrlOrMeta && e.key === "k") {
      e.preventDefault();
      e.stopPropagation();
      this.callbacks.showSearchInput();
      return;
    }

    const sidebar = this.container.closest(
      ".stx-shell-sidebar, .stx-shell-sidebar__content",
    );
    const isOurTree =
      this.container.contains(e.target as Node) ||
      document.activeElement === this.container ||
      this.container.contains(document.activeElement) ||
      (sidebar &&
        (sidebar.contains(e.target as Node) ||
          sidebar.contains(document.activeElement)));
    if (!isOurTree) return;

    if (!ctrlOrMeta && !e.altKey && !e.shiftKey) {
      if (e.key === "g") {
        e.preventDefault();
        this.callbacks.refresh();
        return;
      }
      if (e.key === "+" || e.key === "=") {
        e.preventDefault();
        const sel = this.stateManager.getSelected();
        const tp =
          sel && this.callbacks.isItemDirectory(sel)
            ? sel
            : sel
              ? this.callbacks.getParentPath(sel)
              : "";
        this.fileActions.createNewFolder(tp);
        return;
      }
      if (e.key === "/") {
        e.preventDefault();
        this.callbacks.showSearchInput();
        return;
      }
    }

    const selectedPaths = this.selectionHandler.getSelectedPaths();
    const selected = this.stateManager.getSelected();

    if (ctrlOrMeta && e.key === "z" && !e.shiftKey) {
      e.preventDefault();
      e.stopPropagation();
      this.undoRedoHandler.undo();
      return;
    }
    if (
      (ctrlOrMeta && e.key === "y") ||
      (ctrlOrMeta && e.shiftKey && e.key === "Z")
    ) {
      e.preventDefault();
      e.stopPropagation();
      this.undoRedoHandler.redo();
      return;
    }
    if (e.key === "Escape") {
      e.preventDefault();
      this.selectionHandler.clearSelection();
      this.contextMenuHandler.hide();
      if (this.clipboardHandler.hasClipboard()) {
        this.clipboardHandler.clearClipboard();
        this.callbacks.showMessage("Cut cancelled", "info");
      }
      return;
    }
    if (ctrlOrMeta && e.shiftKey && (e.key === "N" || e.key === "n")) {
      e.preventDefault();
      e.stopPropagation();
      const tp =
        selected && this.callbacks.isItemDirectory(selected)
          ? selected
          : selected
            ? this.callbacks.getParentPath(selected)
            : "";
      this.fileActions.createNewFolder(tp);
      return;
    }
    if (ctrlOrMeta && !e.shiftKey && (e.key === "N" || e.key === "n")) {
      e.preventDefault();
      e.stopPropagation();
      const tp =
        selected && this.callbacks.isItemDirectory(selected)
          ? selected
          : selected
            ? this.callbacks.getParentPath(selected)
            : "";
      this.fileActions.createNewFile(tp);
      return;
    }

    if (selectedPaths.length === 0 && !selected) return;

    if (ctrlOrMeta && e.key === "c") {
      e.preventDefault();
      e.stopPropagation();
      this.clipboardHandler.copy();
    } else if (ctrlOrMeta && e.key === "x") {
      e.preventDefault();
      e.stopPropagation();
      this.clipboardHandler.cut();
    } else if (ctrlOrMeta && e.key === "v") {
      e.preventDefault();
      e.stopPropagation();
      if (selected) {
        const tp = this.callbacks.isItemDirectory(selected)
          ? selected
          : this.callbacks.getParentPath(selected);
        this.clipboardHandler.paste(tp);
      } else {
        this.clipboardHandler.paste("");
      }
    } else if (e.key === "Delete" || e.key === "Backspace") {
      e.preventDefault();
      e.stopPropagation();
      const ptd =
        selectedPaths.length > 0
          ? selectedPaths
          : selected && selected !== ""
            ? [selected]
            : [];
      if (ptd.length > 0)
        this.callbacks.handleContextMenuAction("delete", ptd[0]);
    } else if (e.key === "F2") {
      e.preventDefault();
      e.stopPropagation();
      const ptr = selectedPaths.length > 0 ? selectedPaths[0] : selected;
      if (ptr && ptr !== "") {
        const el = this.container.querySelector(
          `[data-path="${ptr}"]`,
        ) as HTMLElement;
        if (el) this.fileActions.startRename(ptr, el);
      }
    } else if (ctrlOrMeta && e.key === "a") {
      e.preventDefault();
      this.selectionHandler.selectAll();
    } else if (e.key === "F5") {
      e.preventDefault();
      e.stopPropagation();
      this.callbacks.refresh();
    } else if (e.altKey && e.key === "ArrowUp") {
      e.preventDefault();
      e.stopPropagation();
      if (selected) {
        const pp = this.callbacks.getParentPath(selected);
        if (pp !== selected) this.selectionHandler.select(pp, false);
      }
    } else if (e.altKey && e.key === "ArrowRight") {
      e.preventDefault();
      e.stopPropagation();
      if (selected && this.callbacks.isItemDirectory(selected)) {
        if (!this.stateManager.isExpanded(selected))
          this.fileActions.toggleFolder(selected);
        const item = TreeUtils.findItem(selected, this.callbacks.getTreeData());
        if (item?.children && item.children.length > 0)
          this.selectionHandler.select(item.children[0].path, false);
      }
    }
  }
}
