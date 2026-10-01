/**
 * Git status badge rendering for file tree items.
 *
 * Ported from scitex-cloud's _file-tree-builder.ts.
 */

export interface GitStatus {
  /** Git status code: M, A, D, ??, R, C */
  status: string;
  /** Whether the change is staged */
  staged: boolean;
}

const STATUS_COLORS: Record<string, string> = {
  M: "#e2c08d", // Modified — orange/yellow
  A: "#73c991", // Added — green
  D: "#f14c4c", // Deleted — red
  "??": "#73c991", // Untracked — green (like added)
  R: "#73c991", // Renamed — green
  C: "#89d185", // Copied — green
};

const STATUS_LABELS: Record<string, string> = {
  M: "M",
  A: "A",
  D: "D",
  "??": "U", // U for untracked
  R: "R",
  C: "C",
};

/**
 * Create a git status badge element.
 * Returns null if no git status is provided.
 */
export function createGitStatusBadge(
  gitStatus: GitStatus | undefined,
): HTMLSpanElement | null {
  if (!gitStatus) return null;

  const color = STATUS_COLORS[gitStatus.status] || "#858585";
  const label = STATUS_LABELS[gitStatus.status] || gitStatus.status;

  const badge = document.createElement("span");
  badge.className = "stx-app-file-browser__git-badge";
  badge.style.color = color;
  badge.style.fontWeight = "600";
  badge.style.fontSize = "11px";
  badge.style.marginLeft = "6px";
  badge.title = gitStatus.staged ? "Staged" : "Modified";
  badge.textContent = label;

  return badge;
}
