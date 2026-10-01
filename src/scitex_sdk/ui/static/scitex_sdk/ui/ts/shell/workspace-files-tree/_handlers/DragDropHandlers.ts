/**
 * Drag and Drop Handlers - Uses adapter via FileOperations/FileUpload
 * Ported from scitex-cloud
 */

import type { TreeConfig } from "../types";
import type { FileOperation } from "./UndoRedoHandler";
import { FileOperations } from "./FileOperations";
import { FileUpload } from "./FileUpload";
import { DragState } from "./DragState";

export class DragDropHandlers {
  private showMessage: (
    message: string,
    type: "success" | "error" | "info",
  ) => void;
  private getSelectedPaths: () => string[];
  private isItemSelected: (path: string) => boolean;
  private fileOps: FileOperations;
  private fileUpload: FileUpload;
  private dragState: DragState;

  constructor(
    private config: TreeConfig,
    private refresh: () => Promise<void>,
    showMessage?: (message: string, type: "success" | "error" | "info") => void,
    getSelectedPaths?: () => string[],
    isItemSelected?: (path: string) => boolean,
  ) {
    this.showMessage =
      showMessage || ((msg, type) => console.log(`[DragDrop] ${type}: ${msg}`));
    this.getSelectedPaths = getSelectedPaths || (() => []);
    this.isItemSelected = isItemSelected || (() => false);
    this.fileOps = new FileOperations(config, refresh, showMessage);
    this.fileUpload = new FileUpload(config, refresh, showMessage);
    this.dragState = new DragState();
  }

  setRecordOperation(callback: (op: FileOperation) => void): void {
    this.fileOps.setRecordOperation(callback);
  }

  attachDragDropListeners(container: HTMLElement): void {
    const treeEl = container.querySelector(".wft-tree");
    if (!treeEl) return;
    this.attachContainerDropZone(container);

    treeEl.addEventListener("dragstart", (e) => {
      const dragEvent = e as DragEvent;
      const target = dragEvent.target as HTMLElement;
      const item = target.closest("[data-path]");
      if (item && dragEvent.dataTransfer) {
        const path = item.getAttribute("data-path")!;
        if (path === "") {
          dragEvent.preventDefault();
          return;
        }
        this.dragState.dragModifiers = {
          alt: dragEvent.altKey,
          ctrl: dragEvent.ctrlKey || dragEvent.metaKey,
        };
        if (this.isItemSelected(path)) {
          this.dragState.draggedPaths = this.getSelectedPaths().filter(
            (p) => p !== "",
          );
        } else {
          this.dragState.draggedPaths = [path];
        }
        const operation = this.dragState.dragModifiers.alt
          ? "symlink"
          : this.dragState.dragModifiers.ctrl
            ? "copy"
            : "move";
        dragEvent.dataTransfer.setData(
          "text/plain",
          this.dragState.draggedPaths.join(";"),
        );
        dragEvent.dataTransfer.setData("application/x-wft-internal", "true");
        dragEvent.dataTransfer.setData(
          "application/x-wft-count",
          String(this.dragState.draggedPaths.length),
        );
        dragEvent.dataTransfer.setData(
          "application/x-wft-operation",
          operation,
        );
        dragEvent.dataTransfer.effectAllowed = "copy";
        const dragData = this.dragState.draggedPaths.map((p) => ({
          path: p,
          name: p.split("/").pop() || p,
          type: "file",
        }));
        dragEvent.dataTransfer.setData(
          "application/x-scitex-file",
          JSON.stringify(dragData),
        );
        this.dragState.markDraggedItems(container, this.dragState.draggedPaths);
        this.dragState.showDragCountBadge(this.dragState.draggedPaths.length);
      }
    });

    treeEl.addEventListener("dragover", (e) => {
      const dragEvent = e as DragEvent;
      dragEvent.preventDefault();
      const target = dragEvent.target as HTMLElement;
      const dropTarget = target.closest(
        ".wft-folder[data-path], .wft-root[data-path]",
      );
      treeEl.querySelectorAll(".wft-drop-target").forEach((el) => {
        if (el !== dropTarget) el.classList.remove("wft-drop-target");
      });
      if (dropTarget && dragEvent.dataTransfer) {
        const targetPath = dropTarget.getAttribute("data-path") || "";
        const isValidTarget = !this.dragState.draggedPaths.some(
          (p) => targetPath === p || targetPath.startsWith(p + "/"),
        );
        if (isValidTarget) {
          dragEvent.dataTransfer.dropEffect = "move";
          dropTarget.classList.add("wft-drop-target");
        } else {
          dragEvent.dataTransfer.dropEffect = "none";
          dropTarget.classList.remove("wft-drop-target");
        }
      }
    });

    treeEl.addEventListener("dragleave", (e) => {
      const dragEvent = e as DragEvent;
      const target = dragEvent.target as HTMLElement;
      const dropTarget = target.closest(
        ".wft-folder[data-path], .wft-root[data-path]",
      );
      if (dropTarget) {
        setTimeout(() => {
          if (!dropTarget.matches(":hover"))
            dropTarget.classList.remove("wft-drop-target");
        }, 50);
      }
    });

    treeEl.addEventListener("drop", async (e) => {
      const dragEvent = e as DragEvent;
      dragEvent.preventDefault();
      dragEvent.stopPropagation();
      const target = dragEvent.target as HTMLElement;
      const dropTarget = target.closest(
        ".wft-folder[data-path], .wft-root[data-path]",
      );
      if (dragEvent.dataTransfer) {
        const files = dragEvent.dataTransfer.files;
        const isInternal = dragEvent.dataTransfer.types.includes(
          "application/x-wft-internal",
        );
        if (files.length > 0 && !isInternal) {
          const targetPath = dropTarget?.getAttribute("data-path") || "";
          await this.fileUpload.uploadFiles(files, targetPath);
        } else if (dropTarget && isInternal) {
          const sourceData = dragEvent.dataTransfer.getData("text/plain");
          const targetPath = dropTarget.getAttribute("data-path") || "";
          const sourcePaths = sourceData
            .split(";")
            .filter((p) => p && p !== targetPath);
          const operation =
            dragEvent.dataTransfer.getData("application/x-wft-operation") ||
            "move";
          if (sourcePaths.length > 0) {
            if (operation === "symlink")
              await this.fileOps.createSymlinks(sourcePaths, targetPath);
            else if (operation === "copy")
              await this.fileOps.copyFiles(sourcePaths, targetPath);
            else await this.fileOps.moveFiles(sourcePaths, targetPath);
          }
        }
      }
      this.dragState.reset();
      this.dragState.cleanupDragState(container);
    });

    treeEl.addEventListener("dragend", () => {
      this.dragState.cleanupDragState(container);
    });
  }

  private attachContainerDropZone(container: HTMLElement): void {
    let dragCounter = 0;
    container.addEventListener("dragenter", (e) => {
      e.preventDefault();
      dragCounter++;
      const dragEvent = e as DragEvent;
      if (dragEvent.dataTransfer?.types.includes("Files"))
        container.classList.add("wft-drop-zone-active");
    });
    container.addEventListener("dragover", (e) => {
      e.preventDefault();
      const dragEvent = e as DragEvent;
      if (dragEvent.dataTransfer) dragEvent.dataTransfer.dropEffect = "copy";
    });
    container.addEventListener("dragleave", (e) => {
      e.preventDefault();
      dragCounter--;
      if (dragCounter === 0) container.classList.remove("wft-drop-zone-active");
    });
    container.addEventListener("drop", async (e) => {
      e.preventDefault();
      dragCounter = 0;
      container.classList.remove("wft-drop-zone-active");
      const dragEvent = e as DragEvent;
      if (dragEvent.dataTransfer) {
        const files = dragEvent.dataTransfer.files;
        const isInternal = dragEvent.dataTransfer.types.includes(
          "application/x-wft-internal",
        );
        const target = dragEvent.target as HTMLElement;
        const dropTarget = target.closest(
          ".wft-folder[data-path], .wft-root[data-path]",
        );
        const targetPath = dropTarget?.getAttribute("data-path") || "";
        if (files.length > 0 && !isInternal) {
          if (!dropTarget) await this.fileUpload.uploadFiles(files, "");
          return;
        }
        const droppedUrl =
          dragEvent.dataTransfer.getData("text/uri-list") ||
          dragEvent.dataTransfer.getData("text/plain");
        if (
          droppedUrl &&
          !isInternal &&
          this.fileUpload.isDownloadableUrl(droppedUrl)
        ) {
          await this.fileUpload.downloadAndUploadFromUrl(
            droppedUrl,
            targetPath,
          );
        }
      }
    });
  }
}
