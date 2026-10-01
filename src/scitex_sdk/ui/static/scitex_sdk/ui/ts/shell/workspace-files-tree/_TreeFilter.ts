/**
 * Workspace Files Tree - Filtering
 * Mode-specific filtering for different workspace modules
 * Ported from scitex-cloud (identical logic)
 */

import type { TreeItem, FilterConfig, WorkspaceMode } from "./types";
import { MODE_FILTERS } from "./types";
import {
  ALLOW_EXTENSIONS,
  DENY_DIRECTORIES,
  ALLOW_DIRECTORIES,
  ALWAYS_VISIBLE_FILENAMES,
} from "./_FilteringCriteria";

export class TreeFilter {
  private config: FilterConfig;
  private showHidden = false;
  private moduleFilterEnabled = false;

  constructor(mode: WorkspaceMode, customConfig?: Partial<FilterConfig>) {
    const centralExtensions = ALLOW_EXTENSIONS[mode];
    const defaultAllowedExtensions =
      centralExtensions === "all" ? [] : centralExtensions;
    const defaultHiddenPatterns = DENY_DIRECTORIES[mode] || [];
    const legacyDefaults = MODE_FILTERS[mode] || MODE_FILTERS.all;

    this.config = {
      mode,
      allowedExtensions:
        customConfig?.allowedExtensions ?? defaultAllowedExtensions,
      disabledExtensions:
        customConfig?.disabledExtensions ??
        legacyDefaults.disabledExtensions ??
        [],
      hiddenPatterns: customConfig?.hiddenPatterns ?? defaultHiddenPatterns,
    };
  }

  isHidden(item: TreeItem): boolean {
    const { name, type } = item;
    if (!this.showHidden && name.startsWith(".")) return true;
    if (type === "file" && ALWAYS_VISIBLE_FILENAMES.includes(name))
      return false;
    const systemNoiseFiles = [".DS_Store", "Thumbs.db"];
    if (type === "file" && systemNoiseFiles.includes(name)) return true;
    if (
      type === "directory" &&
      (name.endsWith(".figz.d") || name.endsWith(".pltz.d"))
    )
      return true;
    return false;
  }

  isInactive(item: TreeItem): boolean {
    if (!this.moduleFilterEnabled) return false;
    const { name, path, type } = item;
    for (const pattern of this.config.hiddenPatterns) {
      if (pattern.startsWith(".") && name.endsWith(pattern)) return true;
      if (
        name === pattern ||
        path.includes(`/${pattern}/`) ||
        path.includes(`/${pattern}`)
      )
        return true;
    }
    if (!this.isWithinAllowedDirectories(path)) return true;
    if (type === "file" && !this.isAllowed(item)) return true;
    return false;
  }

  private isWithinAllowedDirectories(path: string): boolean {
    const allowedDirs = ALLOW_DIRECTORIES[this.config.mode];
    if (allowedDirs.length === 0) return true;
    const np = path.replace(/^\.\//, "");
    const inAllowed = allowedDirs.some((d) => {
      const nd = d.replace(/^\.\//, "");
      return np.startsWith(nd) || np === nd;
    });
    if (inAllowed) return true;
    return allowedDirs.some((d) => {
      const nd = d.replace(/^\.\//, "");
      return nd.startsWith(np + "/");
    });
  }

  isAllowed(item: TreeItem): boolean {
    if (item.type === "directory") return true;
    if (ALWAYS_VISIBLE_FILENAMES.includes(item.name)) return true;
    if (this.config.allowedExtensions.length === 0) return true;
    const ext = this.getExtension(item.name);
    return this.config.allowedExtensions.includes(ext);
  }

  isDisabled(item: TreeItem): boolean {
    if (!this.moduleFilterEnabled) return false;
    if (item.type === "directory") return false;
    if (ALWAYS_VISIBLE_FILENAMES.includes(item.name)) return false;
    const ext = this.getExtension(item.name);
    if (this.config.disabledExtensions.includes(ext)) return true;
    if (
      this.config.allowedExtensions.length > 0 &&
      !this.config.allowedExtensions.includes(ext)
    )
      return true;
    return false;
  }

  private getExtension(fileName: string): string {
    const lastDot = fileName.lastIndexOf(".");
    if (lastDot === -1) return "";
    return fileName.substring(lastDot).toLowerCase();
  }

  filterTree(items: TreeItem[]): TreeItem[] {
    return items
      .filter((item) => !this.isHidden(item))
      .map((item) => {
        if (item.type === "directory" && item.children) {
          return { ...item, children: this.filterTree(item.children) };
        }
        return item;
      });
  }

  getMode(): WorkspaceMode {
    return this.config.mode;
  }
  getConfig(): FilterConfig {
    return this.config;
  }
  setAllowedExtensions(ext: string[]): void {
    this.config.allowedExtensions = ext;
  }
  setDisabledExtensions(ext: string[]): void {
    this.config.disabledExtensions = ext;
  }
  setHiddenPatterns(p: string[]): void {
    this.config.hiddenPatterns = p;
  }
  setShowHidden(show: boolean): void {
    this.showHidden = show;
  }
  getShowHidden(): boolean {
    return this.showHidden;
  }
  setModuleFilterEnabled(enabled: boolean): void {
    this.moduleFilterEnabled = enabled;
  }
  getModuleFilterEnabled(): boolean {
    return this.moduleFilterEnabled;
  }

  setMode(mode: WorkspaceMode): void {
    const centralExtensions = ALLOW_EXTENSIONS[mode];
    const defaultAllowedExtensions =
      centralExtensions === "all" ? [] : centralExtensions;
    const defaultHiddenPatterns = DENY_DIRECTORIES[mode] || [];
    const legacyDefaults = MODE_FILTERS[mode] || MODE_FILTERS.all;
    this.config = {
      mode,
      allowedExtensions: defaultAllowedExtensions,
      disabledExtensions: legacyDefaults.disabledExtensions ?? [],
      hiddenPatterns: defaultHiddenPatterns,
    };
  }
}
