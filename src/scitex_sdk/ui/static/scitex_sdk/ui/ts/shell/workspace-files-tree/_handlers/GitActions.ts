/**
 * Git Actions Handler - Uses adapter instead of hardcoded URLs
 * Ported from scitex-cloud
 */

import type { TreeConfig } from "../types";

export class GitActions {
  constructor(
    private config: TreeConfig,
    private refresh: () => Promise<void>,
    private showMessage: (
      message: string,
      type: "success" | "error" | "info",
    ) => void,
  ) {}

  async stage(paths: string | string[]): Promise<boolean> {
    const a = this.config.adapter;
    if (!a.gitStage) return false;
    const pathsArray = Array.isArray(paths) ? paths : [paths];
    try {
      const data = await a.gitStage(pathsArray);
      if (data.success) {
        this.showMessage(
          data.message || `Staged ${pathsArray.length} file(s)`,
          "success",
        );
        await this.refresh();
        return true;
      } else {
        this.showMessage(data.error || "Failed to stage files", "error");
        return false;
      }
    } catch {
      this.showMessage("Network error staging files", "error");
      return false;
    }
  }

  async unstage(paths: string | string[]): Promise<boolean> {
    const a = this.config.adapter;
    if (!a.gitUnstage) return false;
    const pathsArray = Array.isArray(paths) ? paths : [paths];
    try {
      const data = await a.gitUnstage(pathsArray);
      if (data.success) {
        this.showMessage(
          data.message || `Unstaged ${pathsArray.length} file(s)`,
          "success",
        );
        await this.refresh();
        return true;
      } else {
        this.showMessage(data.error || "Failed to unstage files", "error");
        return false;
      }
    } catch {
      this.showMessage("Network error unstaging files", "error");
      return false;
    }
  }

  async discard(paths: string | string[]): Promise<boolean> {
    const a = this.config.adapter;
    if (!a.gitDiscard) return false;
    const pathsArray = Array.isArray(paths) ? paths : [paths];
    try {
      const data = await a.gitDiscard(pathsArray);
      if (data.success) {
        this.showMessage(
          data.message || `Discarded changes to ${pathsArray.length} file(s)`,
          "success",
        );
        await this.refresh();
        return true;
      } else {
        this.showMessage(data.error || "Failed to discard changes", "error");
        return false;
      }
    } catch {
      this.showMessage("Network error discarding changes", "error");
      return false;
    }
  }

  async stageAll(): Promise<boolean> {
    const a = this.config.adapter;
    if (!a.gitStageAll) return false;
    try {
      const data = await a.gitStageAll();
      if (data.success) {
        this.showMessage(data.message || "All changes staged", "success");
        await this.refresh();
        return true;
      } else {
        this.showMessage(data.error || "Failed to stage all", "error");
        return false;
      }
    } catch {
      this.showMessage("Network error staging all files", "error");
      return false;
    }
  }

  async unstageAll(): Promise<boolean> {
    const a = this.config.adapter;
    if (!a.gitUnstageAll) return false;
    try {
      const data = await a.gitUnstageAll();
      if (data.success) {
        this.showMessage(data.message || "All changes unstaged", "success");
        await this.refresh();
        return true;
      } else {
        this.showMessage(data.error || "Failed to unstage all", "error");
        return false;
      }
    } catch {
      this.showMessage("Network error unstaging all files", "error");
      return false;
    }
  }

  async commit(message: string, push: boolean = false): Promise<boolean> {
    const a = this.config.adapter;
    if (!a.gitCommit) return false;
    if (!message.trim()) {
      this.showMessage("Commit message is required", "error");
      return false;
    }
    try {
      const data = await a.gitCommit(message.trim(), push);
      if (data.success) {
        this.showMessage(data.message || "Changes committed", "success");
        await this.refresh();
        return true;
      } else {
        this.showMessage(data.error || "Failed to commit", "error");
        return false;
      }
    } catch {
      this.showMessage("Network error committing changes", "error");
      return false;
    }
  }

  async push(): Promise<boolean> {
    const a = this.config.adapter;
    if (!a.gitPush) return false;
    try {
      const data = await a.gitPush();
      if (data.success) {
        this.showMessage(data.message || "Pushed to remote", "success");
        await this.refresh();
        return true;
      } else {
        this.showMessage(data.error || "Failed to push", "error");
        return false;
      }
    } catch {
      this.showMessage("Network error pushing to remote", "error");
      return false;
    }
  }

  async pull(): Promise<boolean> {
    const a = this.config.adapter;
    if (!a.gitPull) return false;
    try {
      const data = await a.gitPull();
      if (data.success) {
        this.showMessage(data.message || "Pulled from remote", "success");
        await this.refresh();
        return true;
      } else {
        this.showMessage(data.error || "Failed to pull", "error");
        return false;
      }
    } catch {
      this.showMessage("Network error pulling from remote", "error");
      return false;
    }
  }

  async getHistory(path: string = "", limit: number = 20): Promise<any[]> {
    const a = this.config.adapter;
    if (!a.gitHistory) return [];
    try {
      const data = await a.gitHistory(path, limit);
      return data.success ? data.commits || [] : [];
    } catch {
      return [];
    }
  }

  async getDiff(
    path: string = "",
    staged: boolean = false,
  ): Promise<{ diff: string; stat: string } | null> {
    const a = this.config.adapter;
    if (!a.gitDiff) return null;
    try {
      const data = await a.gitDiff(path, staged);
      return data.success
        ? { diff: data.diff || "", stat: data.stat || "" }
        : null;
    } catch {
      return null;
    }
  }

  async showHistory(path: string): Promise<void> {
    const commits = await this.getHistory(path);
    if (commits.length === 0) {
      this.showMessage("No history found", "info");
      return;
    }
    window.dispatchEvent(
      new CustomEvent("git-history-show", { detail: { path, commits } }),
    );
  }

  async showDiff(path: string, staged: boolean = false): Promise<void> {
    const result = await this.getDiff(path, staged);
    if (!result || !result.diff) {
      this.showMessage("No changes to show", "info");
      return;
    }
    window.dispatchEvent(
      new CustomEvent("git-diff-show", {
        detail: { path, diff: result.diff, stat: result.stat },
      }),
    );
  }
}
