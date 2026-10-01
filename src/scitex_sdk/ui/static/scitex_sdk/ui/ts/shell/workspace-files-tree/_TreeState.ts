/**
 * Workspace Files Tree - State Management
 * Persists tree state (expanded folders, selection) to localStorage
 * Syncs state across browser tabs
 *
 * Ported from scitex-cloud (identical logic, no API deps)
 */

import type { TreeState, WorkspaceMode } from "./types";

const STORAGE_KEY_PREFIX = "scitex_workspace_tree_";

const EMPTY_FOCUS_MAP = (): Record<string, string | null> => ({
  vis: null,
  writer: null,
  scholar: null,
  clew: null,
  hub: null,
  files: null,
  tools: null,
  explorer: null,
  all: null,
  code: null,
  example: null,
  apps: null,
});

export class TreeStateManager {
  private projectKey: string;
  private sharedKey: string;
  private mode: WorkspaceMode;
  private state: TreeState;
  private listeners: Set<(state: TreeState) => void> = new Set();

  constructor(username: string, slug: string, mode: WorkspaceMode = "all") {
    this.mode = mode;
    this.projectKey = `${STORAGE_KEY_PREFIX}${username}_${slug}_${mode}`;
    this.sharedKey = `${STORAGE_KEY_PREFIX}${username}_${slug}_shared`;
    this.state = this.loadState();
    this.setupStorageListener();
  }

  private loadState(): TreeState {
    let expandedPaths = new Set<string>();
    let selectedPath: string | null = null;
    let selectedPaths = new Set<string>();
    let targetPaths = new Set<string>();
    let scrollTop = 0;
    let focusPathPerMode = EMPTY_FOCUS_MAP() as any;

    try {
      const sharedStored = localStorage.getItem(this.sharedKey);
      if (sharedStored) {
        const sharedParsed = JSON.parse(sharedStored);
        expandedPaths = new Set(sharedParsed.expandedPaths || []);
      }
    } catch (err) {
      console.warn("[TreeState] Failed to load shared state:", err);
    }

    try {
      const stored = localStorage.getItem(this.projectKey);
      if (stored) {
        const parsed = JSON.parse(stored);
        selectedPath = parsed.selectedPath || null;
        selectedPaths = new Set(parsed.selectedPaths || []);
        targetPaths = new Set(parsed.targetPaths || []);
        scrollTop = parsed.scrollTop || 0;
        focusPathPerMode = parsed.focusPathPerMode || focusPathPerMode;
      }
    } catch (err) {
      console.warn("[TreeState] Failed to load mode-specific state:", err);
    }

    return {
      expandedPaths,
      selectedPath,
      selectedPaths,
      targetPaths,
      scrollTop,
      focusPathPerMode,
      lastClickedPath: null,
    };
  }

  private saveState(): void {
    try {
      localStorage.setItem(
        this.sharedKey,
        JSON.stringify({
          expandedPaths: Array.from(this.state.expandedPaths),
        }),
      );
      localStorage.setItem(
        this.projectKey,
        JSON.stringify({
          selectedPath: this.state.selectedPath,
          selectedPaths: Array.from(this.state.selectedPaths),
          targetPaths: Array.from(this.state.targetPaths),
          scrollTop: this.state.scrollTop,
          focusPathPerMode: this.state.focusPathPerMode,
        }),
      );
    } catch (err) {
      console.warn("[TreeState] Failed to save state:", err);
    }
  }

  private setupStorageListener(): void {
    window.addEventListener("storage", (e) => {
      try {
        if (e.key === this.sharedKey && e.newValue) {
          const p = JSON.parse(e.newValue);
          this.state.expandedPaths = new Set(p.expandedPaths || []);
          this.notifyListeners();
        } else if (e.key === this.projectKey && e.newValue) {
          const p = JSON.parse(e.newValue);
          this.state.selectedPath = p.selectedPath;
          this.state.selectedPaths = new Set(p.selectedPaths || []);
          this.state.targetPaths = new Set(p.targetPaths || []);
          this.state.scrollTop = p.scrollTop || 0;
          this.state.focusPathPerMode = p.focusPathPerMode || EMPTY_FOCUS_MAP();
          this.notifyListeners();
        }
      } catch (err) {
        console.warn("[TreeState] Failed to parse storage event:", err);
      }
    });
  }

  private notifyListeners(): void {
    this.listeners.forEach((l) => l(this.state));
  }

  subscribe(listener: (state: TreeState) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  getState(): TreeState {
    return this.state;
  }
  isExpanded(path: string): boolean {
    return this.state.expandedPaths.has(path);
  }
  expand(path: string): void {
    this.state.expandedPaths.add(path);
    this.saveState();
    this.notifyListeners();
  }
  collapse(path: string): void {
    this.state.expandedPaths.delete(path);
    this.saveState();
    this.notifyListeners();
  }
  toggle(path: string): boolean {
    const e = this.isExpanded(path);
    if (e) this.collapse(path);
    else this.expand(path);
    return !e;
  }
  getExpanded(): Set<string> {
    return new Set(this.state.expandedPaths);
  }
  setSelected(path: string | null): void {
    this.state.selectedPath = path;
    this.saveState();
    this.notifyListeners();
  }
  getSelected(): string | null {
    return this.state.selectedPath;
  }

  // Multi-selection
  isSelected(path: string): boolean {
    return this.state.selectedPaths.has(path);
  }
  addToSelection(path: string): void {
    this.state.selectedPaths.add(path);
    this.state.lastClickedPath = path;
    this.saveState();
    this.notifyListeners();
  }
  removeFromSelection(path: string): void {
    this.state.selectedPaths.delete(path);
    this.saveState();
    this.notifyListeners();
  }
  toggleSelection(path: string): void {
    if (this.state.selectedPaths.has(path))
      this.state.selectedPaths.delete(path);
    else this.state.selectedPaths.add(path);
    this.state.lastClickedPath = path;
    this.saveState();
    this.notifyListeners();
  }
  getSelectedPaths(): Set<string> {
    return new Set(this.state.selectedPaths);
  }
  setSelectedPaths(paths: string[]): void {
    this.state.selectedPaths = new Set(paths);
    this.saveState();
    this.notifyListeners();
  }
  clearSelection(): void {
    this.state.selectedPaths.clear();
    this.state.selectedPath = null;
    this.state.lastClickedPath = null;
    this.saveState();
    this.notifyListeners();
  }
  getLastClickedPath(): string | null {
    return this.state.lastClickedPath;
  }
  setLastClickedPath(path: string | null): void {
    this.state.lastClickedPath = path;
  }
  selectSingle(path: string): void {
    this.state.selectedPaths.clear();
    this.state.selectedPaths.add(path);
    this.state.selectedPath = path;
    this.state.lastClickedPath = path;
    this.saveState();
    this.notifyListeners();
  }
  selectSingleSilent(path: string): void {
    this.state.selectedPaths.clear();
    this.state.selectedPaths.add(path);
    this.state.selectedPath = path;
    this.state.lastClickedPath = path;
    this.saveState();
  }
  setSelectedPathsSilent(paths: string[]): void {
    this.state.selectedPaths = new Set(paths);
    this.saveState();
  }
  setSelectedSilent(path: string | null): void {
    this.state.selectedPath = path;
    this.saveState();
  }

  // Scroll
  setScrollTop(scrollTop: number): void {
    this.state.scrollTop = scrollTop;
    this.saveState();
  }
  getScrollTop(): number {
    return this.state.scrollTop;
  }

  // Path expansion
  expandToPath(filePath: string): void {
    const parts = filePath.split("/");
    let cur = "";
    for (let i = 0; i < parts.length - 1; i++) {
      cur = cur ? `${cur}/${parts[i]}` : parts[i];
      this.state.expandedPaths.add(cur);
    }
    this.saveState();
    this.notifyListeners();
  }

  // Targets
  isTarget(path: string): boolean {
    return this.state.targetPaths.has(path);
  }
  addTarget(path: string): void {
    this.state.targetPaths.add(path);
    this.saveState();
    this.notifyListeners();
  }
  removeTarget(path: string): void {
    this.state.targetPaths.delete(path);
    this.saveState();
    this.notifyListeners();
  }
  setTargets(paths: string[]): void {
    this.state.targetPaths = new Set(paths);
    this.saveState();
    this.notifyListeners();
  }
  clearTargets(): void {
    this.state.targetPaths.clear();
    this.saveState();
    this.notifyListeners();
  }
  getTargets(): Set<string> {
    return new Set(this.state.targetPaths);
  }

  // Focus paths
  setFocusPath(mode: WorkspaceMode, path: string | null): void {
    this.state.focusPathPerMode[mode] = path;
    this.saveState();
    this.notifyListeners();
  }
  getFocusPath(mode: WorkspaceMode): string | null {
    return this.state.focusPathPerMode[mode];
  }

  clear(): void {
    this.state = {
      expandedPaths: new Set(),
      selectedPath: null,
      selectedPaths: new Set(),
      targetPaths: new Set(),
      scrollTop: 0,
      focusPathPerMode: EMPTY_FOCUS_MAP() as any,
      lastClickedPath: null,
    };
    localStorage.removeItem(this.projectKey);
    localStorage.removeItem(this.sharedKey);
    this.notifyListeners();
  }
}
