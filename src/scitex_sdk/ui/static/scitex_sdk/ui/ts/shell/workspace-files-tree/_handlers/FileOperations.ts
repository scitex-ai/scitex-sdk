/**
 * File Operations Handler - Uses adapter instead of hardcoded URLs
 * Ported from scitex-cloud
 */

import type { TreeConfig } from "../types";
import type { FileOperation } from "./UndoRedoHandler";

export class FileOperations {
  private config: TreeConfig;
  private refresh: () => Promise<void>;
  private showMessage: (
    message: string,
    type: "success" | "error" | "info",
  ) => void;
  private recordOperation: ((op: FileOperation) => void) | null = null;

  constructor(
    config: TreeConfig,
    refresh: () => Promise<void>,
    showMessage?: (message: string, type: "success" | "error" | "info") => void,
  ) {
    this.config = config;
    this.refresh = refresh;
    this.showMessage =
      showMessage || ((msg, type) => console.log(`[FileOps] ${type}: ${msg}`));
  }

  setRecordOperation(callback: (op: FileOperation) => void): void {
    this.recordOperation = callback;
  }

  async moveFiles(
    sourcePaths: string[],
    targetFolderPath: string,
  ): Promise<void> {
    if (sourcePaths.length === 0) return;
    const adapter = this.config.adapter;
    if (!adapter.moveFile) {
      this.showMessage("Move not supported", "error");
      return;
    }

    const validPaths = sourcePaths.filter((src) => {
      if (targetFolderPath.startsWith(src + "/") || targetFolderPath === src)
        return false;
      return true;
    });
    if (validPaths.length === 0) {
      this.showMessage("Cannot move folder into itself", "error");
      return;
    }

    this.showMessage(
      `Moving ${validPaths.length} item${validPaths.length > 1 ? "s" : ""}...`,
      "info",
    );
    let successCount = 0;
    let errorCount = 0;

    for (const sourcePath of validPaths) {
      try {
        const fileName = sourcePath.split("/").pop() || sourcePath;
        const destPath = targetFolderPath
          ? `${targetFolderPath}/${fileName}`
          : fileName;
        const data = await adapter.moveFile(sourcePath, destPath);
        if (data.success) {
          successCount++;
          if (this.recordOperation) {
            this.recordOperation({
              type: "move",
              timestamp: Date.now(),
              originalPath: sourcePath,
              newPath: destPath,
              isDirectory:
                sourcePath.endsWith("/") || !sourcePath.includes("."),
            });
          }
        } else {
          errorCount++;
        }
      } catch {
        errorCount++;
      }
    }
    if (successCount > 0) {
      await this.refresh();
      this.showMessage(
        `Moved ${successCount} item${successCount > 1 ? "s" : ""} (Ctrl+Z to undo)`,
        errorCount > 0 ? "info" : "success",
      );
    } else {
      this.showMessage("Failed to move items", "error");
    }
  }

  async copyFiles(
    sourcePaths: string[],
    targetFolderPath: string,
  ): Promise<void> {
    if (sourcePaths.length === 0) return;
    const adapter = this.config.adapter;
    if (!adapter.copyFile) {
      this.showMessage("Copy not supported", "error");
      return;
    }

    this.showMessage(
      `Copying ${sourcePaths.length} item${sourcePaths.length > 1 ? "s" : ""}...`,
      "info",
    );
    let successCount = 0;

    for (const sourcePath of sourcePaths) {
      try {
        const fileName = sourcePath.split("/").pop() || sourcePath;
        const destPath = targetFolderPath
          ? `${targetFolderPath}/${fileName}`
          : fileName;
        const data = await adapter.copyFile(sourcePath, destPath);
        if (data.success) {
          successCount++;
          if (this.recordOperation) {
            this.recordOperation({
              type: "copy",
              timestamp: Date.now(),
              originalPath: sourcePath,
              newPath: destPath,
              isDirectory:
                sourcePath.endsWith("/") || !sourcePath.includes("."),
            });
          }
        }
      } catch {
        /* continue */
      }
    }
    if (successCount > 0) {
      await this.refresh();
      this.showMessage(
        `Copied ${successCount} item${successCount > 1 ? "s" : ""} (Ctrl+Z to undo)`,
        "success",
      );
    } else {
      this.showMessage("Failed to copy items", "error");
    }
  }

  async createSymlinks(
    sourcePaths: string[],
    targetFolderPath: string,
  ): Promise<void> {
    if (sourcePaths.length === 0) return;
    const adapter = this.config.adapter;
    if (!adapter.createSymlink) {
      this.showMessage("Symlink not supported", "error");
      return;
    }

    let successCount = 0;
    for (const sourcePath of sourcePaths) {
      try {
        const fileName = sourcePath.split("/").pop() || sourcePath;
        const linkPath = targetFolderPath
          ? `${targetFolderPath}/${fileName}`
          : fileName;
        const data = await adapter.createSymlink(sourcePath, linkPath);
        if (data.success) successCount++;
      } catch {
        /* continue */
      }
    }
    if (successCount > 0) {
      await this.refresh();
      this.showMessage(
        `Created ${successCount} symlink${successCount > 1 ? "s" : ""}`,
        "success",
      );
    } else {
      this.showMessage("Failed to create symlinks", "error");
    }
  }
}
