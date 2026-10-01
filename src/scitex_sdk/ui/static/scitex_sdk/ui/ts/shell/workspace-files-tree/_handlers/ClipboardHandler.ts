/**
 * ClipboardHandler - Uses adapter instead of hardcoded URLs
 * Ported from scitex-cloud
 */

import type { TreeConfig } from "../types";
import type { FileOperation } from "./UndoRedoHandler";

export type ClipboardOperation = "cut" | "copy";
export interface ClipboardState {
  operation: ClipboardOperation;
  paths: string[];
  timestamp: number;
}

export class ClipboardHandler {
  private recordOperation: ((op: FileOperation) => void) | null = null;
  private clipboard: ClipboardState | null = null;

  constructor(
    private config: TreeConfig,
    private refresh: () => Promise<void>,
    private showMessage: (
      message: string,
      type: "success" | "error" | "info",
    ) => void,
    private getSelectedPaths: () => string[],
    private isPathDirectory: (path: string) => boolean,
  ) {}

  setRecordOperation(callback: (op: FileOperation) => void): void {
    this.recordOperation = callback;
  }

  copy(paths?: string[]): void {
    const p = paths || this.getSelectedPaths();
    if (p.length === 0) {
      this.showMessage("No files selected", "info");
      return;
    }
    this.clipboard = { operation: "copy", paths: p, timestamp: Date.now() };
    this.copyToOsClipboard(p);
    this.showMessage(
      p.length === 1
        ? `Copied: ${this.getFileName(p[0])}`
        : `Copied ${p.length} items`,
      "success",
    );
    this.updateCutCopyClasses();
  }

  private async copyToOsClipboard(paths: string[]): Promise<void> {
    try {
      await navigator.clipboard.writeText(paths.join("\n"));
    } catch {
      /* ignore */
    }
  }

  cut(paths?: string[]): void {
    const p = paths || this.getSelectedPaths();
    if (p.length === 0) {
      this.showMessage("No files selected", "info");
      return;
    }
    this.clipboard = { operation: "cut", paths: p, timestamp: Date.now() };
    this.showMessage(
      p.length === 1
        ? `Cut: ${this.getFileName(p[0])}`
        : `Cut ${p.length} items`,
      "success",
    );
    this.updateCutCopyClasses();
  }

  async paste(targetPath: string): Promise<boolean> {
    if (!this.clipboard) {
      this.showMessage("Nothing to paste", "info");
      return false;
    }
    const { operation, paths } = this.clipboard;
    const adapter = this.config.adapter;
    try {
      const isDirectory =
        targetPath === "" ? true : this.isPathDirectory(targetPath);
      const destDir = isDirectory ? targetPath : this.getParentPath(targetPath);
      let successCount = 0;
      const errors: string[] = [];

      for (const sourcePath of paths) {
        const fileName = this.getFileName(sourcePath);
        let destPath = destDir ? `${destDir}/${fileName}` : fileName;
        if (sourcePath === destPath) {
          if (operation === "copy")
            destPath = this.getPathWithSuffix(destPath, 1);
          else {
            errors.push(`Cannot move '${fileName}' to same location`);
            continue;
          }
        }
        if (destPath.startsWith(sourcePath + "/")) {
          errors.push(`Cannot ${operation} '${fileName}' into itself`);
          continue;
        }

        try {
          const isDir = this.isPathDirectory(sourcePath);
          if (operation === "copy") {
            if (!adapter.copyFile) throw new Error("Copy not supported");
            let finalDest = destPath;
            let attempt = 0;
            while (attempt < 100) {
              const data = await adapter.copyFile(sourcePath, finalDest);
              if (data.success) {
                if (this.recordOperation)
                  this.recordOperation({
                    type: "copy",
                    timestamp: Date.now(),
                    originalPath: sourcePath,
                    newPath: finalDest,
                    isDirectory: isDir,
                  });
                successCount++;
                break;
              }
              if (data.error?.includes("already exists")) {
                attempt++;
                finalDest = this.getPathWithSuffix(destPath, attempt);
                continue;
              }
              throw new Error(data.error || "Copy failed");
            }
          } else {
            if (!adapter.moveFile) throw new Error("Move not supported");
            let finalDest = destPath;
            let attempt = 0;
            while (attempt < 100) {
              const data = await adapter.moveFile(sourcePath, finalDest);
              if (data.success) {
                if (this.recordOperation)
                  this.recordOperation({
                    type: "move",
                    timestamp: Date.now(),
                    originalPath: sourcePath,
                    newPath: finalDest,
                    isDirectory: isDir,
                  });
                successCount++;
                break;
              }
              if (data.error?.includes("already exists")) {
                attempt++;
                finalDest = this.getPathWithSuffix(destPath, attempt);
                continue;
              }
              throw new Error(data.error || "Move failed");
            }
          }
        } catch (error: any) {
          errors.push(`${fileName}: ${error.message || "Unknown error"}`);
        }
      }

      if (operation === "cut" && successCount > 0) {
        this.clipboard = null;
        this.updateCutCopyClasses();
      }
      await this.refresh();
      if (successCount > 0) {
        const verb = operation === "cut" ? "Moved" : "Copied";
        this.showMessage(
          `${verb} ${successCount} item${successCount > 1 ? "s" : ""} (Ctrl+Z to undo)`,
          "success",
        );
      }
      if (errors.length > 0)
        this.showMessage(`Errors: ${errors.join(", ")}`, "error");
      return successCount > 0;
    } catch (error) {
      console.error("[ClipboardHandler] Paste error:", error);
      this.showMessage("Failed to paste items", "error");
      return false;
    }
  }

  hasClipboard(): boolean {
    return this.clipboard !== null && this.clipboard.paths.length > 0;
  }
  getClipboardOperation(): ClipboardOperation | null {
    return this.clipboard?.operation ?? null;
  }
  getClipboardPaths(): string[] {
    return this.clipboard?.paths ?? [];
  }
  clearClipboard(): void {
    this.clipboard = null;
    this.updateCutCopyClasses();
  }

  private getPathWithSuffix(path: string, suffix: number): string {
    const parts = path.split("/");
    const fileName = parts.pop() || path;
    const parentPath = parts.join("/");
    const dotIndex = fileName.lastIndexOf(".");
    let newName: string;
    if (dotIndex > 0) {
      newName = `${fileName.substring(0, dotIndex)} (${suffix})${fileName.substring(dotIndex)}`;
    } else {
      newName = `${fileName} (${suffix})`;
    }
    return parentPath ? `${parentPath}/${newName}` : newName;
  }

  private getParentPath(path: string): string {
    const parts = path.split("/");
    parts.pop();
    return parts.join("/");
  }
  private getFileName(path: string): string {
    return path.split("/").pop() || path;
  }

  private updateCutCopyClasses(): void {
    document
      .querySelectorAll(".wft-item.wft-cut, .wft-item.wft-copied")
      .forEach((el) => {
        el.classList.remove("wft-cut", "wft-copied");
      });
    if (this.clipboard) {
      const className =
        this.clipboard.operation === "cut" ? "wft-cut" : "wft-copied";
      for (const path of this.clipboard.paths) {
        const el = document.querySelector(`.wft-item[data-path="${path}"]`);
        if (el) el.classList.add(className);
      }
    }
  }

  reapplyClasses(): void {
    this.updateCutCopyClasses();
  }
}
