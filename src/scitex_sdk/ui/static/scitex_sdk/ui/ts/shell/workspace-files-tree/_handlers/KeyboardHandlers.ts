/**
 * Keyboard Navigation Handlers for WorkspaceFilesTree
 * Ported from scitex-cloud (no API deps)
 */

import type { TreeConfig } from "../types";
import type { TreeStateManager } from "../_TreeState";

export class KeyboardHandlers {
  private anchorPath: string | null = null;

  constructor(
    private config: TreeConfig,
    private stateManager: TreeStateManager,
    private container: HTMLElement,
    private onToggleFolder: (path: string) => void,
    private onOpenFile: (path: string) => void,
  ) {}

  handleKeyboard(e: KeyboardEvent): void {
    if (e.repeat) return;
    const allItems = this.getVisibleItems();
    if (allItems.length === 0) return;
    const selected = this.stateManager.getSelected();

    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        e.stopPropagation();
        this.navigateTree(1, e.shiftKey, allItems);
        break;
      case "ArrowUp":
        e.preventDefault();
        e.stopPropagation();
        this.navigateTree(-1, e.shiftKey, allItems);
        break;
      case "ArrowRight": {
        if (!selected) {
          this.selectItem(allItems[0], false);
          return;
        }
        e.preventDefault();
        e.stopPropagation();
        const isFolder = this.container.querySelector(
          `.wft-folder[data-path="${selected}"]`,
        );
        if (isFolder) {
          const expanded = this.stateManager.isExpanded(selected);
          if (!expanded) this.onToggleFolder(selected);
          else this.navigateTree(1, false, allItems);
        }
        break;
      }
      case "ArrowLeft": {
        if (!selected) return;
        e.preventDefault();
        e.stopPropagation();
        const isFolder = this.container.querySelector(
          `.wft-folder[data-path="${selected}"]`,
        );
        if (isFolder) {
          const expanded = this.stateManager.isExpanded(selected);
          if (expanded) this.onToggleFolder(selected);
          else this.collapseParent(selected);
        } else {
          this.collapseParent(selected);
        }
        break;
      }
      case "Home":
        e.preventDefault();
        e.stopPropagation();
        if (allItems.length > 0) {
          if (e.shiftKey && selected)
            this.selectRange(
              selected,
              allItems[0].getAttribute("data-path")!,
              allItems,
            );
          else this.selectItem(allItems[0], false);
        }
        break;
      case "End":
        e.preventDefault();
        e.stopPropagation();
        if (allItems.length > 0) {
          const lastItem = allItems[allItems.length - 1];
          if (e.shiftKey && selected)
            this.selectRange(
              selected,
              lastItem.getAttribute("data-path")!,
              allItems,
            );
          else this.selectItem(lastItem, false);
        }
        break;
      case "Enter":
        if (!selected) return;
        e.preventDefault();
        e.stopPropagation();
        const itemEl = this.container.querySelector(
          `[data-path="${selected}"]`,
        );
        if (itemEl?.classList.contains("wft-file")) this.onOpenFile(selected);
        else if (itemEl?.classList.contains("wft-folder"))
          this.onToggleFolder(selected);
        break;
    }
  }

  private getVisibleItems(): Element[] {
    return Array.from(this.container.querySelectorAll(".wft-item[data-path]"));
  }

  private navigateTree(
    direction: number,
    extendSelection: boolean,
    allItems: Element[],
  ): void {
    const selectedPath = this.stateManager.getSelected();
    let currentIndex: number;
    if (!selectedPath) currentIndex = direction > 0 ? -1 : allItems.length;
    else {
      currentIndex = allItems.findIndex(
        (item) => item.getAttribute("data-path") === selectedPath,
      );
      if (currentIndex === -1)
        currentIndex = direction > 0 ? -1 : allItems.length;
    }
    const nextIndex = currentIndex + direction;
    if (nextIndex >= 0 && nextIndex < allItems.length) {
      const nextItem = allItems[nextIndex];
      if (extendSelection) this.extendSelection(nextItem, allItems);
      else {
        this.selectItem(nextItem, false);
        this.anchorPath = nextItem.getAttribute("data-path");
      }
    }
  }

  private selectItem(item: Element, addToSelection: boolean): void {
    const path = item.getAttribute("data-path");
    if (!path) return;
    if (addToSelection) this.stateManager.addToSelection(path);
    else this.stateManager.selectSingleSilent(path);
    this.updateSelectionClasses();
    item.scrollIntoView({ behavior: "instant", block: "nearest" });
  }

  private extendSelection(toItem: Element, allItems: Element[]): void {
    const toPath = toItem.getAttribute("data-path");
    if (!toPath) return;
    if (!this.anchorPath) {
      const selected = this.stateManager.getSelected();
      this.anchorPath = selected || toPath;
    }
    this.selectRange(this.anchorPath, toPath, allItems);
  }

  private selectRange(
    fromPath: string,
    toPath: string,
    allItems: Element[],
  ): void {
    const fromIndex = allItems.findIndex(
      (item) => item.getAttribute("data-path") === fromPath,
    );
    const toIndex = allItems.findIndex(
      (item) => item.getAttribute("data-path") === toPath,
    );
    if (fromIndex === -1 || toIndex === -1) return;
    const start = Math.min(fromIndex, toIndex);
    const end = Math.max(fromIndex, toIndex);
    const rangePaths: string[] = [];
    for (let i = start; i <= end; i++) {
      const path = allItems[i].getAttribute("data-path");
      if (path) rangePaths.push(path);
    }
    this.stateManager.setSelectedPathsSilent(rangePaths);
    this.stateManager.setSelectedSilent(toPath);
    this.updateSelectionClasses();
    const targetItem = allItems[toIndex];
    targetItem.scrollIntoView({ behavior: "instant", block: "nearest" });
  }

  private updateSelectionClasses(): void {
    const selectedPaths = this.stateManager.getSelectedPaths();
    this.container.querySelectorAll(".wft-item").forEach((el) => {
      const path = el.getAttribute("data-path");
      if (path && selectedPaths.has(path)) el.classList.add("selected");
      else el.classList.remove("selected");
    });
  }

  private collapseParent(path: string): void {
    const parts = path.split("/");
    if (parts.length > 1) {
      const parentPath = parts.slice(0, -1).join("/");
      this.stateManager.selectSingleSilent(parentPath);
      this.anchorPath = parentPath;
      this.updateSelectionClasses();
      const parentEl = this.container.querySelector(
        `[data-path="${parentPath}"]`,
      );
      if (parentEl)
        parentEl.scrollIntoView({ behavior: "instant", block: "nearest" });
    }
  }

  resetAnchor(): void {
    this.anchorPath = null;
  }
}
