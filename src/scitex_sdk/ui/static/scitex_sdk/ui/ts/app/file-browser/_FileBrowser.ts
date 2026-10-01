/**
 * FileBrowser — tree view for navigating file hierarchies.
 *
 * Usage:
 *   import { FileBrowser } from 'scitex_sdk/ui/ts/app/file-browser';
 *   const browser = new FileBrowser({
 *     container: '#file-tree',
 *     onFileSelect: (node) => console.log(node.path),
 *   });
 *   browser.setData(treeData);
 */

import { BaseComponent } from "../../_base/BaseComponent";
import type { FileNode, FileBrowserConfig } from "./types";
import {
  renderError,
  renderLoading,
  renderTree,
  setActive,
} from "./_FileTreeRenderer";

export class FileBrowser extends BaseComponent<FileBrowserConfig> {
  private data: FileNode[] = [];
  private expandedDirs: Set<string> = new Set();

  constructor(config: FileBrowserConfig) {
    super(config);
    if (config.apiUrl) {
      this.fetchData(config.apiUrl);
    }
  }

  setData(nodes: FileNode[]): void {
    this.data = nodes;
    this.render();
  }

  async refresh(): Promise<void> {
    if (this.config.apiUrl) {
      await this.fetchData(this.config.apiUrl);
    } else {
      this.render();
    }
  }

  select(path: string): void {
    setActive(this.container, path);
  }

  /** Get paths of currently expanded directories. */
  getExpanded(): string[] {
    return [...this.expandedDirs];
  }

  /** Get total file count (excludes directories). */
  getFileCount(): number {
    return this.countFiles(this.data);
  }

  expandDir(path: string): void {
    this.expandedDirs.add(path);
    this.render();
  }

  collapseDir(path: string): void {
    this.expandedDirs.delete(path);
    this.render();
  }

  override destroy(): void {
    this.data = [];
    this.expandedDirs.clear();
    super.destroy();
  }

  private async fetchData(url: string): Promise<void> {
    renderLoading(this.container);
    try {
      const resp = await fetch(url);
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
      }
      const data = await resp.json();
      this.data = Array.isArray(data)
        ? data
        : (data.tree ?? data.children ?? []);
      this.render();
    } catch (err) {
      renderError(
        this.container,
        err instanceof Error ? err.message : "Failed to load files",
      );
    }
  }

  private render(): void {
    renderTree(
      this.container,
      this.data,
      this.config,
      this.expandedDirs,
      (path) => {
        if (this.expandedDirs.has(path)) {
          this.expandedDirs.delete(path);
        } else {
          this.expandedDirs.add(path);
        }
        this.render();
        const node = this.findNode(path);
        if (node) {
          this.config.onDirectoryToggle?.(node, this.expandedDirs.has(path));
        }
      },
    );
  }

  private countFiles(nodes: FileNode[]): number {
    let count = 0;
    for (const node of nodes) {
      if (node.type === "file") count++;
      if (node.children) count += this.countFiles(node.children);
    }
    return count;
  }

  private findNode(path: string, nodes?: FileNode[]): FileNode | null {
    for (const node of nodes ?? this.data) {
      if (node.path === path) return node;
      if (node.children) {
        const found = this.findNode(path, node.children);
        if (found) return found;
      }
    }
    return null;
  }
}
