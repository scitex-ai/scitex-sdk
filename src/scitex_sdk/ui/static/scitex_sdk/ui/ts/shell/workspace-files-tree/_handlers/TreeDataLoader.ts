/**
 * TreeDataLoader - Handles loading tree data via adapter
 * Ported from scitex-cloud, uses FileTreeAdapter instead of hardcoded URLs
 */

import type { TreeItem, TreeConfig } from "../types";
import { DEFAULT_EXPAND_PATHS } from "../types";
import type { TreeStateManager } from "../_TreeState";
import {
  mergeGitStatus,
  calculateGitSummary,
  type GitSummary,
} from "./GitStatusHandler";
import { TreeUtils } from "./TreeUtils";

export interface TreeLoadResult {
  success: boolean;
  treeData: TreeItem[];
  gitSummary: GitSummary;
  /** Absolute directory the tree is rooted at (for the breadcrumb), when known. */
  rootPath?: string;
  error?: string;
}

export class TreeDataLoader {
  private cacheKey: string;

  constructor(
    private config: TreeConfig,
    private stateManager: TreeStateManager,
    private showError: (message: string) => void,
  ) {
    this.cacheKey = `scitex-tree-${config.ownerUsername}-${config.projectSlug}`;
  }

  getCached(): TreeLoadResult | null {
    try {
      const raw = sessionStorage.getItem(this.cacheKey);
      if (!raw) return null;
      const cached = JSON.parse(raw) as TreeLoadResult;
      if (cached.success && cached.treeData?.length > 0) return cached;
    } catch {
      /* ignore parse errors */
    }
    return null;
  }

  private saveCache(result: TreeLoadResult): void {
    if (!result.success) return;
    try {
      sessionStorage.setItem(this.cacheKey, JSON.stringify(result));
    } catch {
      /* quota exceeded - ignore */
    }
  }

  async load(rootPath?: string): Promise<TreeLoadResult> {
    const showGitStatus = this.config.showGitStatus !== false;
    const adapter = this.config.adapter;

    try {
      const [treeResponse, gitResponse] = await Promise.all([
        adapter.fetchTree(rootPath),
        showGitStatus && adapter.fetchGitStatus
          ? adapter.fetchGitStatus()
          : Promise.resolve(null),
      ]);

      if (treeResponse.success) {
        const tree: TreeItem[] = treeResponse.tree;
        let gitSummary: GitSummary = { staged: 0, modified: 0, untracked: 0 };

        if (gitResponse && showGitStatus) {
          try {
            if (gitResponse.success && gitResponse.files) {
              mergeGitStatus(tree, gitResponse.files);
              gitSummary = calculateGitSummary(gitResponse.files);
            }
          } catch (gitError) {
            console.warn(
              "[TreeDataLoader] Failed to process git status:",
              gitError,
            );
          }
        }

        const result: TreeLoadResult = {
          success: true,
          treeData: tree,
          gitSummary,
          rootPath: treeResponse.rootPath ?? rootPath,
        };
        // Only cache the default root; re-rooted (breadcrumb) loads always
        // fetch fresh so they never clobber the default-root cache.
        if (!rootPath) this.saveCache(result);
        return result;
      } else {
        const errorMsg = treeResponse.error || "Failed to load file tree";
        this.showError(errorMsg);
        return {
          success: false,
          treeData: [],
          gitSummary: { staged: 0, modified: 0, untracked: 0 },
          error: errorMsg,
        };
      }
    } catch (error) {
      console.error("[TreeDataLoader] Error loading tree:", error);
      this.showError("Network error loading file tree");
      return {
        success: false,
        treeData: [],
        gitSummary: { staged: 0, modified: 0, untracked: 0 },
        error: "Network error",
      };
    }
  }

  applyDefaultExpansion(treeData: TreeItem[]): boolean {
    if (this.stateManager.getExpanded().size === 0) {
      (DEFAULT_EXPAND_PATHS[this.config.mode] || []).forEach((path) => {
        if (TreeUtils.pathExistsInTree(path, treeData)) {
          this.stateManager.expand(path);
        }
      });
      return true;
    }
    return false;
  }
}
