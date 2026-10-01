/**
 * Context Menu Action Handler - Ported from scitex-cloud (no API deps)
 */

import type { TreeConfig } from "../types";
import type { SelectionHandler } from "./SelectionHandler";
import type { ClipboardHandler } from "./ClipboardHandler";
import type { UndoRedoHandler } from "./UndoRedoHandler";
import type { FileActions } from "./FileActions";
import type { GitActions } from "./GitActions";

export interface ContextMenuActionCallbacks {
  isItemDirectory: (path: string) => boolean;
  getContainer: () => HTMLElement | null;
  refresh: () => Promise<void>;
  getCsrfToken: () => string;
  showMessage: (message: string, type: "success" | "error" | "info") => void;
  downloadFile: (path: string) => void;
  extractBundle: (path: string) => Promise<void>;
  promptCreateSymlink: (path: string) => Promise<void>;
  showFilter: () => void;
}

export class ContextMenuActionHandler {
  constructor(
    private config: TreeConfig,
    private selectionHandler: SelectionHandler,
    private clipboardHandler: ClipboardHandler,
    private undoRedoHandler: UndoRedoHandler,
    private fileActions: FileActions,
    private gitActions: GitActions,
    private callbacks: ContextMenuActionCallbacks,
  ) {}

  private getParentPath(path: string): string {
    const parts = path.split("/");
    parts.pop();
    return parts.join("/");
  }
  private getPathsForOperation(path: string): string[] {
    const selectedPaths = this.selectionHandler.getSelectedPaths();
    if (selectedPaths.includes(path)) return selectedPaths;
    return [path];
  }

  async handle(action: string, path: string): Promise<void> {
    switch (action) {
      case "cut":
        this.clipboardHandler.cut(this.getPathsForOperation(path));
        break;
      case "copy":
        this.clipboardHandler.copy(this.getPathsForOperation(path));
        break;
      case "paste":
        await this.clipboardHandler.paste(path);
        break;
      case "delete":
        await this.handleDelete(path);
        break;
      case "rename":
        await this.handleRename(path);
        break;
      case "duplicate":
        await this.handleDuplicate(path);
        break;
      case "new-file": {
        const d = this.callbacks.isItemDirectory(path)
          ? path
          : this.getParentPath(path);
        await this.fileActions.createNewFile(d);
        break;
      }
      case "new-folder": {
        const d = this.callbacks.isItemDirectory(path)
          ? path
          : this.getParentPath(path);
        await this.fileActions.createNewFolder(d);
        break;
      }
      case "create-symlink": {
        for (const p of this.getPathsForOperation(path))
          await this.callbacks.promptCreateSymlink(p);
        break;
      }
      case "download": {
        for (const p of this.getPathsForOperation(path))
          this.callbacks.downloadFile(p);
        break;
      }
      case "extract-bundle":
        await this.callbacks.extractBundle(path);
        break;
      case "git-stage":
        await this.gitActions.stage(this.getPathsForOperation(path));
        break;
      case "git-unstage":
        await this.gitActions.unstage(this.getPathsForOperation(path));
        break;
      case "git-discard":
        await this.gitActions.discard(this.getPathsForOperation(path));
        break;
      case "git-history":
        await this.gitActions.showHistory(path);
        break;
      case "git-diff":
        await this.gitActions.showDiff(path);
        break;
      case "git-stage-all":
        await this.gitActions.stageAll();
        break;
      case "git-unstage-all":
        await this.gitActions.unstageAll();
        break;
      case "git-commit":
        await this.handleGitCommit(false);
        break;
      case "git-commit-push":
        await this.handleGitCommit(true);
        break;
      case "git-push":
        await this.gitActions.push();
        break;
      case "git-pull":
        await this.gitActions.pull();
        break;
      case "run-file":
        document.dispatchEvent(
          new CustomEvent("run-file", { detail: { path } }),
        );
        break;
      case "clew":
        document.dispatchEvent(
          new CustomEvent("fileSelected", { detail: { path } }),
        );
        break;
      case "filter":
        this.callbacks.showFilter();
        break;
      case "refresh":
        await this.callbacks.refresh();
        break;
      case "undo":
        await this.undoRedoHandler.undo();
        break;
      case "redo":
        await this.undoRedoHandler.redo();
        break;
      default:
        console.warn("[ContextMenuAction] Unknown action:", action);
    }
  }

  private async handleGitCommit(push: boolean): Promise<void> {
    const label = push ? "Commit & Push" : "Commit";
    const message = window.prompt(`${label} -- Enter commit message:`);
    if (!message || !message.trim()) return;
    await this.gitActions.commit(message.trim(), push);
  }

  private async handleDelete(path: string): Promise<void> {
    const pathsToDelete = this.getPathsForOperation(path);
    for (const p of pathsToDelete) {
      this.undoRedoHandler.recordOperation({
        type: "delete",
        timestamp: Date.now(),
        originalPath: p,
        isDirectory: this.callbacks.isItemDirectory(p),
      });
      await this.fileActions.deleteFile(p);
    }
  }

  private async handleRename(path: string): Promise<void> {
    const container = this.callbacks.getContainer();
    const el = container?.querySelector(`[data-path="${path}"]`) as HTMLElement;
    if (el) {
      const result = await this.fileActions.startRename(path, el);
      if (result && result.newPath) {
        this.undoRedoHandler.recordOperation({
          type: "rename",
          timestamp: Date.now(),
          originalPath: path,
          newPath: result.newPath,
          isDirectory: this.callbacks.isItemDirectory(path),
        });
      }
    }
  }

  private async handleDuplicate(path: string): Promise<void> {
    const copyResult = await this.fileActions.copyFile(path);
    if (copyResult) {
      this.undoRedoHandler.recordOperation({
        type: "copy",
        timestamp: Date.now(),
        originalPath: copyResult.sourcePath,
        newPath: copyResult.destPath,
        isDirectory: this.callbacks.isItemDirectory(path),
      });
    }
  }
}
