/**
 * Workspace Files Tree - Orchestrator component
 * Ported from scitex-cloud, uses FileTreeAdapter for backend abstraction
 */

import type { TreeItem, TreeConfig, WorkspaceMode, SortMode } from "./types";
import { TreeStateManager } from "./_TreeState";
import { TreeFilter } from "./_TreeFilter";
import { TreeRenderer } from "./_TreeRenderer";
import { EventHandlers } from "./_handlers/EventHandlers";
import { DragDropHandlers } from "./_handlers/DragDropHandlers";
import { KeyboardHandlers } from "./_handlers/KeyboardHandlers";
import { FileActions } from "./_handlers/FileActions";
import { DirectoryFilterHandler } from "./_handlers/DirectoryFilterHandler";
import { PathNavigator } from "./_handlers/PathNavigator";
import { TreeUtils } from "./_handlers/TreeUtils";
import { SelectionHandler } from "./_handlers/SelectionHandler";
import { GitActions } from "./_handlers/GitActions";
import { ClipboardHandler } from "./_handlers/ClipboardHandler";
import { ContextMenuHandler } from "./_handlers/ContextMenuHandler";
import { UndoRedoHandler } from "./_handlers/UndoRedoHandler";
import { SearchHandler } from "./_handlers/SearchHandler";
import type { WorkspaceKeyboardHandler } from "./_handlers/WorkspaceKeyboardHandler";
import type { ContextMenuActionHandler } from "./_handlers/ContextMenuActionHandler";
import { TreeFileOperations } from "./_handlers/TreeFileOperations";
import { TreeDataLoader } from "./_handlers/TreeDataLoader";
import { BreadcrumbHandler } from "./_handlers/BreadcrumbHandler";
import { showTreeMessage } from "./_handlers/TreeMessageHandler";
import { type GitSummary } from "./_handlers/GitStatusHandler";
import type { SearchUIHandler } from "./_handlers/SearchUIHandler";
import { initializeTreeHandlers } from "./_handlers/TreeInitHandler";

export class WorkspaceFilesTree {
  private config: TreeConfig;
  private container: HTMLElement | null = null;
  private breadcrumb: BreadcrumbHandler | null = null;
  private currentRoot: string | null = null;
  private stateManager: TreeStateManager;
  private filter: TreeFilter;
  private renderer: TreeRenderer;
  private eventHandlers: EventHandlers;
  private dragDropHandlers: DragDropHandlers;
  private keyboardHandlers: KeyboardHandlers | null = null;
  private fileActions: FileActions;
  private directoryFilterHandler: DirectoryFilterHandler;
  private pathNavigator: PathNavigator;
  private selectionHandler: SelectionHandler;
  private gitActions: GitActions;
  private clipboardHandler: ClipboardHandler;
  private contextMenuHandler: ContextMenuHandler;
  private undoRedoHandler: UndoRedoHandler;
  private searchHandler: SearchHandler;
  private workspaceKeyboardHandler: WorkspaceKeyboardHandler | null = null;
  private contextMenuActionHandler: ContextMenuActionHandler | null = null;
  private searchUIHandler: SearchUIHandler | null = null;
  private fileOperations: TreeFileOperations;
  private dataLoader: TreeDataLoader;
  private treeData: TreeItem[] = [];
  private gitSummary: GitSummary = { staged: 0, modified: 0, untracked: 0 };
  private sortMode: SortMode = "name";
  private isLoading = false;
  private lastTreeHash = "";

  constructor(config: TreeConfig) {
    this.config = { showFolderActions: true, showGitStatus: true, ...config };
    this.stateManager = new TreeStateManager(
      config.ownerUsername,
      config.projectSlug,
      config.mode,
    );
    this.filter = new TreeFilter(config.mode, {
      allowedExtensions: config.allowedExtensions,
      disabledExtensions: config.disabledExtensions,
      hiddenPatterns: config.hiddenPatterns,
    });
    this.renderer = new TreeRenderer(
      this.config,
      this.stateManager,
      this.filter,
    );
    this.fileActions = new FileActions(
      this.config,
      this.stateManager,
      () => this.treeData,
      () => this.rerender(),
      (type, detail) => this.emitEvent(type, detail),
      () => this.refresh(),
    );
    this.gitActions = new GitActions(
      this.config,
      () => this.refresh(),
      (msg, type) => this.showMessage(msg, type),
    );
    this.eventHandlers = new EventHandlers(
      this.config,
      this.stateManager,
      (p) => this.fileActions.toggleFolder(p),
      (p, e) => this.handleFileClick(p, e),
      (p) => this.fileActions.openFile(p),
      (p) => this.fileActions.runFile(p),
      (p, el) => this.fileActions.startRename(p, el),
      (p) => this.fileActions.deleteFile(p),
      (fp) => this.fileActions.createNewFile(fp),
      (fp) => this.fileActions.createNewFolder(fp),
      (p) => this.fileActions.copyFile(p),
    );
    this.directoryFilterHandler = new DirectoryFilterHandler(() =>
      this.rerender(),
    );
    this.selectionHandler = new SelectionHandler(
      this.stateManager,
      () => this.container,
      () => this.treeData,
      () => this.rerender(),
      (p) => this.fileActions.selectFile(p),
    );
    this.pathNavigator = new PathNavigator(
      this.stateManager,
      () => this.container,
      () => this.rerender(),
      () => this.treeData,
      (p) => this.selectionHandler.updateClasses(p),
    );
    this.undoRedoHandler = new UndoRedoHandler(
      this.config,
      () => this.refresh(),
      (msg, type) => this.showMessage(msg, type),
    );
    this.dragDropHandlers = new DragDropHandlers(
      this.config,
      () => this.refresh(),
      (msg, type) => this.showMessage(msg, type),
      () => this.selectionHandler.getSelectedPaths(),
      (p) => this.stateManager.isSelected(p),
    );
    this.dragDropHandlers.setRecordOperation((op) =>
      this.undoRedoHandler.recordOperation(op),
    );
    this.clipboardHandler = new ClipboardHandler(
      this.config,
      () => this.refresh(),
      (msg, type) => this.showMessage(msg, type),
      () => this.selectionHandler.getSelectedPaths(),
      (p) => this.isItemDirectory(p),
    );
    this.clipboardHandler.setRecordOperation((op) =>
      this.undoRedoHandler.recordOperation(op),
    );
    this.contextMenuHandler = new ContextMenuHandler(
      (a, p) => this.contextMenuActionHandler?.handle(a, p),
      () => this.clipboardHandler.hasClipboard(),
      (p) => this.isItemDirectory(p),
      () => this.undoRedoHandler.canUndo(),
      () => this.undoRedoHandler.canRedo(),
      () => this.selectionHandler.getSelectedPaths().length,
      (p) => this.selectionHandler.getSelectedPaths().includes(p),
      () => ({
        staged: this.gitSummary.staged,
        unstaged: this.gitSummary.modified + this.gitSummary.untracked,
      }),
    );
    this.searchHandler = new SearchHandler(
      () => this.rerender(),
      () => this.treeData,
    );
    this.fileOperations = new TreeFileOperations(
      this.config,
      () => this.refresh(),
      (msg, type) => this.showMessage(msg, type),
      (p) => this.stateManager.expand(p),
    );
    this.dataLoader = new TreeDataLoader(
      this.config,
      this.stateManager,
      (msg) => this.showError(msg),
    );
    if (this.config.showBreadcrumb) {
      this.breadcrumb = new BreadcrumbHandler((path) => this.setRoot(path));
    }
    this.stateManager.subscribe(() => this.rerender());
  }

  /** Re-root the tree at `absPath` and reload (breadcrumb navigation). */
  async setRoot(absPath: string): Promise<void> {
    this.lastTreeHash = ""; // force re-render even if the new tree hashes equal
    await this.loadTree(absPath);
  }

  private isItemDirectory(path: string): boolean {
    if (path === "") return true;
    return TreeUtils.findItem(path, this.treeData)?.type === "directory";
  }
  private getParentPath(path: string): string {
    const parts = path.split("/");
    parts.pop();
    return parts.join("/");
  }

  async initialize(): Promise<void> {
    this.container = document.getElementById(this.config.containerId);
    if (!this.container)
      return console.error(`Container #${this.config.containerId} not found`);
    const result = initializeTreeHandlers(
      this.container,
      this.config,
      this.renderer,
      this.stateManager,
      this.selectionHandler,
      this.clipboardHandler,
      this.undoRedoHandler,
      this.contextMenuHandler,
      this.fileActions,
      this.gitActions,
      this.searchHandler,
      this.fileOperations,
      {
        isItemDirectory: (p) => this.isItemDirectory(p),
        getContainer: () => this.container,
        refresh: () => this.refresh(),
        getCsrfToken: () => this.config.adapter.getCsrfToken(),
        showMessage: (msg, type) => this.showMessage(msg, type),
        getParentPath: (p) => this.getParentPath(p),
        handleContextMenuAction: (a, p) =>
          this.contextMenuActionHandler?.handle(a, p) as Promise<void>,
        getTreeData: () => this.treeData,
        setSearchQuery: (q) => this.setSearchQuery(q),
        clearSearch: () => this.clearSearch(),
        selectFile: (p) => this.selectFile(p),
        loadTree: () => this.loadTree(),
      },
    );
    this.contextMenuActionHandler = result.contextMenuActionHandler;
    this.searchUIHandler = result.searchUIHandler;
    this.workspaceKeyboardHandler = result.workspaceKeyboardHandler;
    const cached = this.dataLoader.getCached();
    if (cached) {
      this.treeData = cached.treeData;
      this.gitSummary = cached.gitSummary;
      this.dataLoader.applyDefaultExpansion(this.treeData);
      this.render();
      this.attachEventListeners();
      this.selectionHandler.updateAllSelectionClasses();
      this.loadTree();
    } else {
      await this.loadTree();
    }
  }

  private handleFileClick(path: string, event?: MouseEvent): void {
    this.container?.focus();
    this.selectionHandler.handleClick(path, event || new MouseEvent("click"));
  }

  async loadTree(rootPath?: string): Promise<void> {
    if (this.isLoading) return;
    this.isLoading = true;
    const treeEl = this.container?.querySelector(".wft-tree");
    const scrollTop = treeEl?.scrollTop || 0;
    try {
      const result = await this.dataLoader.load(rootPath);
      if (result.success) {
        if (result.rootPath) this.currentRoot = result.rootPath;
        const hash = JSON.stringify(result.treeData);
        if (hash === this.lastTreeHash) return;
        this.lastTreeHash = hash;
        this.treeData = result.treeData;
        this.gitSummary = result.gitSummary;
        const isFirstLoad = this.dataLoader.applyDefaultExpansion(
          this.treeData,
        );
        this.render();
        const newTreeEl = this.container?.querySelector(".wft-tree");
        if (newTreeEl && scrollTop > 0) newTreeEl.scrollTop = scrollTop;
        await this.pathNavigator.autoExpandFocusPath(
          this.config.mode,
          isFirstLoad,
        );
        this.attachEventListeners();
        this.selectionHandler.updateAllSelectionClasses();
        this.clipboardHandler.reapplyClasses();
      }
    } finally {
      this.isLoading = false;
    }
  }

  private contentEl(): HTMLElement {
    let el = this.container!.querySelector(
      ":scope > .wft-content",
    ) as HTMLElement;
    if (!el) {
      el = document.createElement("div");
      el.className = "wft-content";
      const sb = this.container!.querySelector(":scope > .wft-search-box");
      Array.from(this.container!.children).forEach((c) => {
        if (c !== sb && !c.classList.contains("wft-breadcrumb")) c.remove();
      });
      if (sb) this.container!.insertBefore(el, sb);
      else this.container!.appendChild(el);
    }
    return el;
  }

  private render(): void {
    if (!this.container) return;
    const data = this.directoryFilterHandler.isActive()
      ? this.directoryFilterHandler.getFilteredData()
      : this.treeData;
    const info = this.searchHandler.isActive()
      ? this.searchHandler.getMatchInfo(data)
      : { matches: new Set<string>(), ancestors: new Set<string>() };
    this.renderer.setSearchInfo(info.matches, info.ancestors);
    this.contentEl().innerHTML = this.renderer.render(data, this.gitSummary);
    this.breadcrumb?.render(this.container, this.currentRoot);
  }

  private rerender(): void {
    const treeEl = this.container?.querySelector(".wft-tree");
    const scrollTop = treeEl?.scrollTop || 0;
    this.render();
    this.attachEventListeners();
    const newTreeEl = this.container?.querySelector(".wft-tree");
    if (newTreeEl) newTreeEl.scrollTop = scrollTop;
    this.selectionHandler.updateAllSelectionClasses();
    this.clipboardHandler.reapplyClasses();
  }

  private showError(message: string): void {
    if (!this.container) return;
    this.contentEl().innerHTML = `<div class="wft-error"><i class="fas fa-exclamation-triangle"></i><p>${message}</p></div>`;
  }
  private boundKeyboardHandler: ((e: KeyboardEvent) => void) | null = null;

  private attachEventListeners(): void {
    if (!this.container) return;
    this.eventHandlers.attachEventListeners(this.container);
    this.dragDropHandlers.attachDragDropListeners(this.container);
    if (!this.keyboardHandlers) {
      this.keyboardHandlers = new KeyboardHandlers(
        this.config,
        this.stateManager,
        this.container,
        (p) => this.fileActions.toggleFolder(p),
        (p) => this.fileActions.openFile(p),
      );
      this.boundKeyboardHandler = (e: KeyboardEvent) =>
        this.keyboardHandlers?.handleKeyboard(e);
      this.container.addEventListener("keydown", this.boundKeyboardHandler);
    }
  }

  private emitEvent(type: string, detail: any): void {
    if (!this.container) return;
    this.container.dispatchEvent(
      new CustomEvent(type, { detail, bubbles: true }),
    );
    if (type === "file-open" && this.config.onFileSelect) {
      const item = TreeUtils.findItem(detail.path, this.treeData);
      if (item) this.config.onFileSelect(detail.path, item);
    } else if (type === "folder-toggle" && this.config.onFolderToggle) {
      this.config.onFolderToggle(detail.path, detail.expanded);
    }
  }

  private showMessage(
    message: string,
    type: "success" | "error" | "info",
  ): void {
    showTreeMessage(message, type);
  }

  // === Public API ===
  setDirectoryFilter(path: string | null): void {
    this.directoryFilterHandler.setFilter(path, this.treeData);
  }
  getDirectoryFilter(): string | null {
    return this.directoryFilterHandler.getFilter();
  }
  selectFile(path: string, skipCallback = false): void {
    this.selectionHandler.select(path, skipCallback);
  }
  setTargetFile(path: string): void {
    this.selectionHandler.setTarget(path);
  }
  async refresh(): Promise<void> {
    await this.loadTree();
  }
  getTreeData(): TreeItem[] {
    return this.treeData;
  }
  async refreshAndExpandPath(path: string): Promise<void> {
    await this.pathNavigator.refreshAndExpandPath(path, () => this.loadTree());
  }
  async expandPath(path: string): Promise<void> {
    await this.pathNavigator.expandPath(path);
  }
  async focusDirectory(
    targetPath: string,
    collapseOthersAtLevel = true,
  ): Promise<void> {
    await this.pathNavigator.focusDirectory(targetPath, collapseOthersAtLevel);
  }
  setSearchQuery(query: string): void {
    this.searchHandler.setQuery(query);
  }
  clearSearch(): void {
    this.searchHandler.clear();
  }
  getSearchQuery(): string {
    return this.searchHandler.getQuery();
  }
  isSearchActive(): boolean {
    return this.searchHandler.isActive();
  }
  getGitActions(): GitActions {
    return this.gitActions;
  }
  getUndoRedoHandler(): UndoRedoHandler {
    return this.undoRedoHandler;
  }
  getSelectedPaths(): string[] {
    return this.selectionHandler.getSelectedPaths();
  }
  clearSelection(): void {
    this.selectionHandler.clearSelection();
  }
  selectAll(): void {
    this.selectionHandler.selectAll();
  }
  async undo(): Promise<boolean> {
    return this.undoRedoHandler.undo();
  }
  async redo(): Promise<boolean> {
    return this.undoRedoHandler.redo();
  }
  toggleHiddenFiles(): boolean {
    const s = !this.filter.getShowHidden();
    this.filter.setShowHidden(s);
    this.rerender();
    return s;
  }
  setShowHidden(show: boolean): void {
    this.filter.setShowHidden(show);
    this.rerender();
  }
  getShowHidden(): boolean {
    return this.filter.getShowHidden();
  }
  toggleModuleFilter(): boolean {
    const s = !this.filter.getModuleFilterEnabled();
    this.filter.setModuleFilterEnabled(s);
    this.rerender();
    return s;
  }
  setModuleFilterEnabled(enabled: boolean): void {
    this.filter.setModuleFilterEnabled(enabled);
    this.rerender();
  }
  getModuleFilterEnabled(): boolean {
    return this.filter.getModuleFilterEnabled();
  }
  setFilterMode(mode: WorkspaceMode | "all"): void {
    if (mode !== "all") this.filter.setMode(mode);
    this.filter.setModuleFilterEnabled(mode !== "all");
    this.rerender();
  }
  toggleGitStatus(): boolean {
    const s = this.config.showGitStatus === false;
    this.config.showGitStatus = s;
    this.container?.classList.toggle("wft-no-git", !s);
    return s;
  }
  setShowGitStatus(show: boolean): void {
    this.config.showGitStatus = show;
    this.container?.classList.toggle("wft-no-git", !show);
  }
  setSortMode(mode: SortMode): void {
    this.sortMode = mode;
    this.renderer.setSortMode(mode);
    this.rerender();
  }
  toggleSortMode(): SortMode {
    const next: SortMode = this.sortMode === "name" ? "mtime" : "name";
    this.setSortMode(next);
    return next;
  }
  getSortMode(): SortMode {
    return this.sortMode;
  }
  setOnFileSelect(handler: (path: string, item: TreeItem) => void): void {
    this.config.onFileSelect = handler;
  }
  destroy(): void {
    /* reserved for future cleanup */
  }
}
