/**
 * ShellFileTree — shell-level file tree component.
 *
 * Wraps the app-layer FileBrowser with:
 *  - Backend adapter abstraction (no hardcoded API endpoints)
 *  - Hidden files toggle with localStorage persistence
 *  - System noise filtering (.DS_Store, Thumbs.db, __pycache__, etc.)
 *  - Auto-initialization into #ws-worktree-tree container
 *
 * Ported from scitex-cloud's file-tree.ts and _file-tree-builder.ts.
 */

import { FileBrowser } from "../../app/file-browser/_FileBrowser";
import type { FileNode } from "../../app/file-browser/types";
import type { ShellFileTreeConfig, FileTreeAdapter } from "./types";

const HIDDEN_FILES_KEY = "stx-shell-show-hidden-files";
const DEFAULT_CONTAINER = "#ws-worktree-tree";

/** System noise files — always hidden regardless of toggle */
const SYSTEM_NOISE = new Set([
  ".DS_Store",
  "Thumbs.db",
  "__pycache__",
  "node_modules",
  ".venv",
  "venv",
]);

export class ShellFileTree {
  private browser: FileBrowser;
  private adapter: FileTreeAdapter;
  private config: ShellFileTreeConfig;
  private rawData: FileNode[] = [];

  constructor(config: ShellFileTreeConfig) {
    this.config = config;
    this.adapter = config.adapter;

    const container =
      typeof config.container === "string"
        ? config.container
        : config.container
          ? config.container
          : DEFAULT_CONTAINER;

    this.browser = new FileBrowser({
      container,
      onFileSelect: config.onFileSelect,
      onDirectoryToggle: config.onDirectoryToggle,
      showHidden: this.getShowHidden(),
      extensions: config.extensions ?? null,
    });
  }

  /** Load file tree from the backend adapter and render. */
  async load(): Promise<void> {
    try {
      this.rawData = await this.adapter.fetchTree();
      const filtered = this.filterTree(this.rawData);
      this.browser.setData(filtered);
    } catch (err) {
      console.error("[ShellFileTree] Failed to load:", err);
      throw err;
    }
  }

  /** Reload tree data from backend. */
  async refresh(): Promise<void> {
    await this.load();
  }

  /** Select a file by path. */
  select(path: string): void {
    this.browser.select(path);
  }

  /** Get currently expanded directory paths. */
  getExpanded(): string[] {
    return this.browser.getExpanded();
  }

  /** Toggle hidden files visibility and re-render. */
  toggleHidden(): void {
    const current = this.getShowHidden();
    const next = !current;
    localStorage.setItem(HIDDEN_FILES_KEY, String(next));

    // Re-filter and re-render with current raw data
    const filtered = this.filterTree(this.rawData);
    this.browser.setData(filtered);

    // Update toggle button if it exists
    this.updateToggleButton(next);

    // Dispatch event for external listeners
    document.dispatchEvent(
      new CustomEvent("stx-shell:hidden-files-changed", {
        detail: { showHidden: next },
      }),
    );
  }

  /** Destroy the component and clean up. */
  destroy(): void {
    this.browser.destroy();
    this.rawData = [];
  }

  /* ── Private ──────────────────────────────────────────────── */

  private getShowHidden(): boolean {
    if (this.config.showHidden !== undefined) return this.config.showHidden;
    return localStorage.getItem(HIDDEN_FILES_KEY) === "true";
  }

  private filterTree(nodes: FileNode[]): FileNode[] {
    const showHidden = this.getShowHidden();

    return nodes
      .filter((node) => {
        // Always hide system noise
        if (SYSTEM_NOISE.has(node.name)) return false;
        // Hide dotfiles unless toggle is on
        if (!showHidden && node.name.startsWith(".")) return false;
        return true;
      })
      .map((node) => {
        if (node.type === "directory" && node.children) {
          const filteredChildren = this.filterTree(node.children);
          return { ...node, children: filteredChildren };
        }
        return node;
      })
      .filter((node) => {
        // Remove empty directories after filtering
        if (
          node.type === "directory" &&
          node.children &&
          node.children.length === 0
        ) {
          return false;
        }
        return true;
      });
  }

  private updateToggleButton(showHidden: boolean): void {
    const btn = document.getElementById("hidden-files-toggle");
    if (!btn) return;
    const icon = btn.querySelector("i");
    if (!icon) return;

    if (showHidden) {
      icon.className = "fas fa-eye";
      btn.title = "Hide hidden files";
      btn.classList.add("active");
    } else {
      icon.className = "fas fa-eye-slash";
      btn.title = "Show hidden files";
      btn.classList.remove("active");
    }
  }
}
