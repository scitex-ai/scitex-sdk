/**
 * PathNavigator - Ported from scitex-cloud (no API deps)
 */
import type { TreeItem, WorkspaceMode } from "../types";
import { TreeStateManager } from "../_TreeState";

export class PathNavigator {
  constructor(
    private stateManager: TreeStateManager,
    private containerFn: () => HTMLElement | null,
    private rerenderFn: () => void,
    private getTreeDataFn: () => TreeItem[],
    private updateSelectionClassesFn: (path: string) => void,
  ) {}

  getParentPaths(path: string): string[] {
    const parts = path.split("/");
    const parents: string[] = [];
    for (let i = 1; i < parts.length; i++)
      parents.push(parts.slice(0, i).join("/"));
    return parents;
  }

  async expandPath(path: string): Promise<void> {
    this.getParentPaths(path).forEach((p) => this.stateManager.expand(p));
    this.rerenderFn();
    await new Promise((r) => setTimeout(r, 100));
    const element = this.containerFn()?.querySelector(`[data-path="${path}"]`);
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "center" });
      this.stateManager.setSelected(path);
      this.updateSelectionClassesFn(path);
    }
  }

  async focusDirectory(
    targetPath: string,
    collapseOthersAtLevel: boolean = true,
  ): Promise<void> {
    const parentPaths = this.getParentPaths(targetPath);
    parentPaths.forEach((p) => this.stateManager.expand(p));
    this.stateManager.expand(targetPath);
    if (collapseOthersAtLevel) {
      const parentPath = parentPaths[parentPaths.length - 1] || "";
      this.getSiblingDirectories(targetPath, parentPath).forEach((sp) => {
        if (sp !== targetPath) this.stateManager.collapse(sp);
      });
    }
    this.rerenderFn();
    await new Promise((r) => setTimeout(r, 100));
    const element = this.containerFn()?.querySelector(
      `[data-path="${targetPath}"]`,
    );
    if (element) element.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  async autoExpandFocusPath(
    mode: WorkspaceMode,
    isFirstLoad: boolean = false,
  ): Promise<void> {
    const focusPath = this.stateManager.getFocusPath(mode);
    if (!focusPath) return;
    this.getParentPaths(focusPath).forEach((p) => this.stateManager.expand(p));
    this.stateManager.expand(focusPath);
    this.stateManager.setSelected(focusPath);
    this.rerenderFn();
    await new Promise((r) => setTimeout(r, 100));
    const focusEl = this.containerFn()?.querySelector(
      `[data-path="${focusPath}"]`,
    );
    if (focusEl)
      focusEl.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  async refreshAndExpandPath(
    path: string,
    loadTreeFn: () => Promise<void>,
  ): Promise<void> {
    await loadTreeFn();
    this.getParentPaths(path).forEach((p) => this.stateManager.expand(p));
    this.stateManager.expand(path);
    this.rerenderFn();
    await new Promise((r) => setTimeout(r, 100));
    const element = this.containerFn()?.querySelector(`[data-path="${path}"]`);
    if (element)
      element.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  private getSiblingDirectories(
    targetPath: string,
    parentPath: string,
  ): string[] {
    const siblings: string[] = [];
    const searchInItems = (items: TreeItem[]): void => {
      for (const item of items) {
        if (item.type === "directory") {
          const ip = this.getParentPaths(item.path).pop() || "";
          if (ip === parentPath) siblings.push(item.path);
          if (item.children) searchInItems(item.children);
        }
      }
    };
    searchInItems(this.getTreeDataFn());
    return siblings;
  }
}
