/**
 * UndoRedoHandler - Uses adapter instead of hardcoded URLs
 * Ported from scitex-cloud
 */

import type { TreeConfig } from "../types";

export type OperationType = "create" | "delete" | "rename" | "move" | "copy";

export interface FileOperation {
  type: OperationType;
  timestamp: number;
  originalPath?: string;
  originalContent?: string;
  newPath?: string;
  isDirectory?: boolean;
}

export class UndoRedoHandler {
  private undoStack: FileOperation[] = [];
  private redoStack: FileOperation[] = [];
  private maxStackSize = 50;

  constructor(
    private config: TreeConfig,
    private refresh: () => Promise<void>,
    private showMessage: (
      message: string,
      type: "success" | "error" | "info",
    ) => void,
  ) {}

  recordOperation(operation: FileOperation): void {
    this.undoStack.push(operation);
    this.redoStack = [];
    if (this.undoStack.length > this.maxStackSize) this.undoStack.shift();
  }

  canUndo(): boolean {
    return this.undoStack.length > 0;
  }
  canRedo(): boolean {
    return this.redoStack.length > 0;
  }

  async undo(): Promise<boolean> {
    if (!this.canUndo()) {
      this.showMessage("Nothing to undo", "info");
      return false;
    }
    const operation = this.undoStack.pop()!;
    const adapter = this.config.adapter;
    try {
      let success = false;
      switch (operation.type) {
        case "delete":
          if (operation.originalPath && adapter.gitDiscard) {
            const r = await adapter.gitDiscard([operation.originalPath]);
            success = r.success && (r.discarded?.length ?? 0) > 0;
          }
          break;
        case "create":
          if (operation.newPath && adapter.deleteFile) {
            const r = await adapter.deleteFile(operation.newPath);
            success = r.success;
          }
          break;
        case "rename":
        case "move":
          if (operation.originalPath && operation.newPath && adapter.moveFile) {
            const r = await adapter.moveFile(
              operation.newPath,
              operation.originalPath,
            );
            success = r.success;
          }
          break;
        case "copy":
          if (operation.newPath && adapter.deleteFile) {
            const r = await adapter.deleteFile(operation.newPath);
            success = r.success;
          }
          break;
      }
      if (success) {
        this.redoStack.push(operation);
        await this.refresh();
        this.showMessage("Undo successful", "success");
        return true;
      } else {
        this.undoStack.push(operation);
        this.showMessage("Undo failed", "error");
        return false;
      }
    } catch (error) {
      this.undoStack.push(operation);
      this.showMessage("Undo failed", "error");
      return false;
    }
  }

  async redo(): Promise<boolean> {
    if (!this.canRedo()) {
      this.showMessage("Nothing to redo", "info");
      return false;
    }
    const operation = this.redoStack.pop()!;
    const adapter = this.config.adapter;
    try {
      let success = false;
      switch (operation.type) {
        case "delete":
          if (operation.originalPath && adapter.deleteFile) {
            const r = await adapter.deleteFile(operation.originalPath);
            success = r.success;
          }
          break;
        case "create":
          if (operation.newPath && adapter.createFile) {
            const r = await adapter.createFile(
              operation.newPath,
              operation.isDirectory ? "directory" : "file",
            );
            success = r.success;
          }
          break;
        case "rename":
        case "move":
          if (operation.originalPath && operation.newPath && adapter.moveFile) {
            const r = await adapter.moveFile(
              operation.originalPath,
              operation.newPath,
            );
            success = r.success;
          }
          break;
        case "copy":
          if (operation.originalPath && operation.newPath && adapter.copyFile) {
            const r = await adapter.copyFile(
              operation.originalPath,
              operation.newPath,
            );
            success = r.success;
          }
          break;
      }
      if (success) {
        this.undoStack.push(operation);
        await this.refresh();
        this.showMessage("Redo successful", "success");
        return true;
      } else {
        this.redoStack.push(operation);
        this.showMessage("Redo failed", "error");
        return false;
      }
    } catch (error) {
      this.redoStack.push(operation);
      this.showMessage("Redo failed", "error");
      return false;
    }
  }

  clear(): void {
    this.undoStack = [];
    this.redoStack = [];
  }
  getUndoStackSize(): number {
    return this.undoStack.length;
  }
  getRedoStackSize(): number {
    return this.redoStack.length;
  }
}
