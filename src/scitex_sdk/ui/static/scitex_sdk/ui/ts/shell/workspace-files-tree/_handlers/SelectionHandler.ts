/**
 * SelectionHandler - Handles file selection and target highlighting
 * Ported from scitex-cloud (no API deps)
 */

import type { TreeItem } from "../types";
import { TreeStateManager } from "../_TreeState";
import { TreeUtils } from "./TreeUtils";

export class SelectionHandler {
  private stateManager: TreeStateManager;
  private containerFn: () => HTMLElement | null;
  private getTreeDataFn: () => TreeItem[];
  private rerenderFn: () => void;
  private selectFileFn: (path: string) => void;
  private isRectSelecting = false;
  private rectStartX = 0;
  private rectStartY = 0;
  private rectElement: HTMLDivElement | null = null;
  private preRectSelection: Set<string> = new Set();

  constructor(
    stateManager: TreeStateManager,
    getContainer: () => HTMLElement | null,
    getTreeData: () => TreeItem[],
    rerender: () => void,
    selectFile: (path: string) => void,
  ) {
    this.stateManager = stateManager;
    this.containerFn = getContainer;
    this.getTreeDataFn = getTreeData;
    this.rerenderFn = rerender;
    this.selectFileFn = selectFile;
  }

  initRectangleSelection(): void {
    const container = this.containerFn();
    if (!container) return;
    container.addEventListener("mousedown", this.handleMouseDown);
    document.addEventListener("mousemove", this.handleMouseMove);
    document.addEventListener("mouseup", this.handleMouseUp);
  }

  destroy(): void {
    const container = this.containerFn();
    if (container)
      container.removeEventListener("mousedown", this.handleMouseDown);
    document.removeEventListener("mousemove", this.handleMouseMove);
    document.removeEventListener("mouseup", this.handleMouseUp);
  }

  private handleMouseDown = (e: MouseEvent): void => {
    const target = e.target as HTMLElement;
    if (target.closest(".wft-item") || target.closest(".wft-action-btn"))
      return;
    const container = this.containerFn();
    if (!container) return;
    e.preventDefault();
    this.isRectSelecting = true;
    const rect = container.getBoundingClientRect();
    this.rectStartX = e.clientX - rect.left + container.scrollLeft;
    this.rectStartY = e.clientY - rect.top + container.scrollTop;
    if (e.ctrlKey || e.metaKey) {
      this.preRectSelection = this.stateManager.getSelectedPaths();
    } else {
      this.preRectSelection = new Set();
      this.stateManager.clearSelection();
    }
    this.rectElement = document.createElement("div");
    this.rectElement.className = "wft-selection-rect";
    this.rectElement.style.position = "absolute";
    this.rectElement.style.left = `${this.rectStartX}px`;
    this.rectElement.style.top = `${this.rectStartY}px`;
    this.rectElement.style.width = "0";
    this.rectElement.style.height = "0";
    container.style.position = "relative";
    container.appendChild(this.rectElement);
  };

  private handleMouseMove = (e: MouseEvent): void => {
    if (!this.isRectSelecting || !this.rectElement) return;
    const container = this.containerFn();
    if (!container) return;
    const rect = container.getBoundingClientRect();
    const currentX = e.clientX - rect.left + container.scrollLeft;
    const currentY = e.clientY - rect.top + container.scrollTop;
    const left = Math.min(this.rectStartX, currentX);
    const top = Math.min(this.rectStartY, currentY);
    const width = Math.abs(currentX - this.rectStartX);
    const height = Math.abs(currentY - this.rectStartY);
    this.rectElement.style.left = `${left}px`;
    this.rectElement.style.top = `${top}px`;
    this.rectElement.style.width = `${width}px`;
    this.rectElement.style.height = `${height}px`;
    this.updateRectSelection(left, top, width, height);
  };

  private handleMouseUp = (): void => {
    if (!this.isRectSelecting) return;
    this.isRectSelecting = false;
    if (this.rectElement) {
      this.rectElement.remove();
      this.rectElement = null;
    }
  };

  private updateRectSelection(
    left: number,
    top: number,
    width: number,
    height: number,
  ): void {
    const container = this.containerFn();
    if (!container) return;
    const selectedPaths = new Set(this.preRectSelection);
    const items = container.querySelectorAll(".wft-item[data-path]");
    items.forEach((item) => {
      const itemRect = (item as HTMLElement).getBoundingClientRect();
      const containerRect = container.getBoundingClientRect();
      const itemLeft =
        itemRect.left - containerRect.left + container.scrollLeft;
      const itemTop = itemRect.top - containerRect.top + container.scrollTop;
      const itemRight = itemLeft + itemRect.width;
      const itemBottom = itemTop + itemRect.height;
      const rectRight = left + width;
      const rectBottom = top + height;
      if (
        itemLeft < rectRight &&
        itemRight > left &&
        itemTop < rectBottom &&
        itemBottom > top
      ) {
        const path = item.getAttribute("data-path");
        if (path) {
          selectedPaths.add(path);
          item.classList.add("selected");
        }
      } else {
        const path = item.getAttribute("data-path");
        if (path && !this.preRectSelection.has(path))
          item.classList.remove("selected");
      }
    });
    this.stateManager.setSelectedPaths(Array.from(selectedPaths));
  }

  handleClick(path: string, e: MouseEvent): void {
    if (path === "") {
      this.stateManager.clearSelection();
      this.stateManager.setLastClickedPath("");
      this.stateManager.setSelected("");
      this.updateAllSelectionClasses();
      return;
    }
    const item = TreeUtils.findItem(path, this.getTreeDataFn());
    if (!item) return;
    const parentPaths = TreeUtils.getParentPaths(path);
    const needsExpand = parentPaths.some(
      (p) => !this.stateManager.isExpanded(p),
    );
    parentPaths.forEach((p) => this.stateManager.expand(p));
    if (e.ctrlKey || e.metaKey) {
      this.stateManager.toggleSelection(path);
    } else if (e.shiftKey) {
      this.selectRange(path);
    } else {
      this.stateManager.selectSingle(path);
      const isBundleDir =
        item.type === "directory" &&
        (path.endsWith(".figz.d") || path.endsWith(".pltz.d"));
      if (item.type === "file" || isBundleDir) this.selectFileFn(path);
    }
    if (needsExpand) this.rerenderFn();
    else this.updateAllSelectionClasses();
  }

  private selectRange(toPath: string): void {
    const fromPath = this.stateManager.getLastClickedPath();
    if (!fromPath) {
      this.stateManager.selectSingle(toPath);
      return;
    }
    const visiblePaths = this.getVisiblePaths();
    const fromIndex = visiblePaths.indexOf(fromPath);
    const toIndex = visiblePaths.indexOf(toPath);
    if (fromIndex === -1 || toIndex === -1) {
      this.stateManager.selectSingle(toPath);
      return;
    }
    const start = Math.min(fromIndex, toIndex);
    const end = Math.max(fromIndex, toIndex);
    const rangePaths = visiblePaths.slice(start, end + 1);
    this.stateManager.setSelectedPaths(rangePaths);
    this.stateManager.setLastClickedPath(toPath);
  }

  private getVisiblePaths(): string[] {
    const container = this.containerFn();
    if (!container) return [];
    const paths: string[] = [];
    container.querySelectorAll(".wft-item[data-path]").forEach((el) => {
      const path = el.getAttribute("data-path");
      if (path) paths.push(path);
    });
    return paths;
  }

  select(path: string, skipCallback: boolean = false): void {
    const item = TreeUtils.findItem(path, this.getTreeDataFn());
    if (item) {
      const parentPaths = TreeUtils.getParentPaths(path);
      const needsExpand = parentPaths.some(
        (p) => !this.stateManager.isExpanded(p),
      );
      parentPaths.forEach((p) => this.stateManager.expand(p));
      this.stateManager.selectSingle(path);
      if (!skipCallback && item.type === "file") this.selectFileFn(path);
      if (needsExpand) this.rerenderFn();
      else this.updateAllSelectionClasses();
      setTimeout(() => {
        const container = this.containerFn();
        const element = container?.querySelector(`[data-path="${path}"]`);
        if (element)
          element.scrollIntoView({ behavior: "smooth", block: "center" });
      }, 100);
    }
  }

  updateAllSelectionClasses(): void {
    const container = this.containerFn();
    if (!container) return;
    const selectedPaths = this.stateManager.getSelectedPaths();
    const selectedPath = this.stateManager.getSelected();
    container.querySelectorAll(".wft-item").forEach((el) => {
      const path = el.getAttribute("data-path");
      if (path === "") {
        if (selectedPath === "") el.classList.add("selected");
        else el.classList.remove("selected");
      } else if (path && selectedPaths.has(path)) el.classList.add("selected");
      else el.classList.remove("selected");
    });
  }

  updateClasses(selectedPath: string): void {
    this.updateAllSelectionClasses();
  }
  getSelectedPaths(): string[] {
    return Array.from(this.stateManager.getSelectedPaths());
  }
  clearSelection(): void {
    this.stateManager.clearSelection();
    this.updateAllSelectionClasses();
  }
  selectAll(): void {
    const paths = this.getVisiblePaths();
    this.stateManager.setSelectedPaths(paths);
    this.updateAllSelectionClasses();
  }

  setTarget(path: string): void {
    this.stateManager.clearTargets();
    this.stateManager.addTarget(path);
    const container = this.containerFn();
    if (container) {
      container.querySelectorAll(".wft-file.target").forEach((el) => {
        el.classList.remove("target");
        el.querySelector(".wft-target-badge")?.remove();
      });
      const targetElement = container.querySelector(`[data-path="${path}"]`);
      if (targetElement) {
        targetElement.classList.add("target");
        targetElement.scrollIntoView({ behavior: "instant", block: "nearest" });
      }
    }
  }
}
