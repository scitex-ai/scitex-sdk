/**
 * Git Status Handler
 * Ported from scitex-cloud (no API deps - pure data transformation)
 */

import type { TreeItem, GitFileStat } from "../types";

export interface GitSummary {
  staged: number;
  modified: number;
  untracked: number;
}

export function mapStatusToCode(status: string): string {
  const map: Record<string, string> = {
    modified: "M",
    added: "A",
    deleted: "D",
    untracked: "??",
    renamed: "R",
    copied: "C",
  };
  return map[status] || status;
}

export function mergeGitStatus(
  treeData: TreeItem[],
  gitFiles: GitFileStat[],
): void {
  const statusMap = new Map<string, { status: string; staged: boolean }>();

  for (const file of gitFiles) {
    const statusCode = mapStatusToCode(file.status);
    statusMap.set(file.path, { status: statusCode, staged: file.staged });

    const parts = file.path.split("/");
    for (let i = 1; i < parts.length; i++) {
      const parentPath = parts.slice(0, i).join("/");
      if (!statusMap.has(parentPath)) {
        statusMap.set(parentPath, { status: "M", staged: false });
      }
    }
  }

  const applyStatus = (items: TreeItem[]): void => {
    for (const item of items) {
      const status = statusMap.get(item.path);
      if (status && !item.git_status) {
        item.git_status = status;
      }
      if (item.children) applyStatus(item.children);
    }
  };

  applyStatus(treeData);
}

export function calculateGitSummary(gitFiles: GitFileStat[]): GitSummary {
  const summary: GitSummary = { staged: 0, modified: 0, untracked: 0 };
  for (const file of gitFiles) {
    if (file.staged) summary.staged++;
    else if (file.status === "untracked" || file.status === "??")
      summary.untracked++;
    else summary.modified++;
  }
  return summary;
}
