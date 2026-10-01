/**
 * Workspace Files Tree - Type Definitions
 * Shared across all workspace modules
 *
 * Ported from scitex-cloud with FileTreeAdapter abstraction for backend URLs.
 */

export type WorkspaceMode =
  | "code"
  | "vis"
  | "writer"
  | "scholar"
  | "clew"
  | "hub"
  | "files"
  | "tools"
  | "example"
  | "apps"
  | "explorer"
  | "all";

export interface TreeItem {
  name: string;
  path: string;
  type: "file" | "directory";
  children?: TreeItem[];
  is_symlink?: boolean;
  symlink_target?: string;
  mtime?: number;
  git_status?: {
    status: string; // M, A, D, ??
    staged: boolean;
  };
}

export type SortMode = "name" | "mtime";

export interface TreeConfig {
  /** Current workspace mode */
  mode: WorkspaceMode;
  /** Container element ID */
  containerId: string;
  /** Project owner username */
  ownerUsername: string;
  /** Project slug */
  projectSlug: string;
  /** File extensions to show (empty = all) */
  allowedExtensions?: string[];
  /** File extensions to gray out but still show */
  disabledExtensions?: string[];
  /** Hide these patterns completely */
  hiddenPatterns?: string[];
  /** Callback when file is selected */
  onFileSelect?: (path: string, item: TreeItem) => void;
  /** Callback when folder is toggled */
  onFolderToggle?: (path: string, expanded: boolean) => void;
  /** Show folder action buttons (new file/folder) */
  showFolderActions?: boolean;
  /** Show git status indicators */
  showGitStatus?: boolean;
  /** Show a breadcrumb path bar above the tree that re-roots on click
   *  (requires the adapter to honour fetchTree's rootPath argument). */
  showBreadcrumb?: boolean;
  /** Custom CSS class for the tree container */
  className?: string;
  /** Backend adapter - abstracts all API calls */
  adapter: FileTreeAdapter;
}

export interface TreeState {
  /** Expanded folder paths */
  expandedPaths: Set<string>;
  /** Currently selected file path (primary selection) */
  selectedPath: string | null;
  /** All selected paths for multi-selection (includes selectedPath) */
  selectedPaths: Set<string>;
  /** Target/active file paths (files currently loaded in editor) */
  targetPaths: Set<string>;
  /** Last scroll position */
  scrollTop: number;
  /** Last focused directory per mode (for restoration on next load) */
  focusPathPerMode: Record<WorkspaceMode, string | null>;
  /** Last clicked path for shift+click range selection */
  lastClickedPath: string | null;
}

export interface FilterConfig {
  mode: WorkspaceMode;
  allowedExtensions: string[];
  disabledExtensions: string[];
  hiddenPatterns: string[];
}

// ============================================================================
// FileTreeAdapter - Backend abstraction interface
// ============================================================================

export interface GitFileStat {
  path: string;
  status: string;
  staged: boolean;
}

/**
 * FileTreeAdapter abstracts all backend API calls.
 * Consumers (scitex-cloud, figrecipe, etc.) implement this interface
 * to connect the tree to their specific backend.
 */
export interface FileTreeAdapter {
  /** Fetch the file tree structure.
   *  @param rootPath optional absolute directory to root the tree at (for
   *    breadcrumb navigation); omit to use the adapter's default root.
   *  @returns the tree and, when known, the absolute ``rootPath`` it is rooted
   *    at (used to render the breadcrumb). */
  fetchTree(rootPath?: string): Promise<{
    success: boolean;
    tree: TreeItem[];
    error?: string;
    rootPath?: string;
  }>;

  /** Fetch git status (optional - return null to disable) */
  fetchGitStatus?(): Promise<{
    success: boolean;
    files: GitFileStat[];
  } | null>;

  /** Get CSRF token for POST requests */
  getCsrfToken(): string;

  // === File operations ===
  createFile?(
    path: string,
    type: "file" | "directory",
  ): Promise<{ success: boolean; error?: string }>;
  renameFile?(
    oldPath: string,
    newName: string,
  ): Promise<{ success: boolean; new_path?: string; error?: string }>;
  deleteFile?(path: string): Promise<{ success: boolean; error?: string }>;
  copyFile?(
    sourcePath: string,
    destPath: string,
  ): Promise<{ success: boolean; error?: string }>;
  moveFile?(
    sourcePath: string,
    destPath: string,
  ): Promise<{ success: boolean; error?: string }>;
  createSymlink?(
    source: string,
    target: string,
  ): Promise<{ success: boolean; error?: string }>;

  // === File content ===
  getFileUrl?(path: string): string;
  uploadFile?(
    file: File,
    path: string,
  ): Promise<{ success: boolean; error?: string }>;
  uploadFromUrl?(
    url: string,
    path: string,
  ): Promise<{ success: boolean; path?: string; error?: string }>;
  extractBundle?(
    bundlePath: string,
    outputPath: string,
  ): Promise<{ success: boolean; error?: string }>;

  // === Git operations ===
  gitStage?(
    paths: string[],
  ): Promise<{ success: boolean; message?: string; error?: string }>;
  gitUnstage?(
    paths: string[],
  ): Promise<{ success: boolean; message?: string; error?: string }>;
  gitDiscard?(
    paths: string[],
  ): Promise<{
    success: boolean;
    discarded?: string[];
    message?: string;
    error?: string;
  }>;
  gitStageAll?(): Promise<{
    success: boolean;
    message?: string;
    error?: string;
  }>;
  gitUnstageAll?(): Promise<{
    success: boolean;
    message?: string;
    error?: string;
  }>;
  gitCommit?(
    message: string,
    push: boolean,
  ): Promise<{ success: boolean; message?: string; error?: string }>;
  gitPush?(): Promise<{ success: boolean; message?: string; error?: string }>;
  gitPull?(): Promise<{ success: boolean; message?: string; error?: string }>;
  gitHistory?(
    path: string,
    limit: number,
  ): Promise<{ success: boolean; commits?: any[]; error?: string }>;
  gitDiff?(
    path: string,
    staged: boolean,
  ): Promise<{
    success: boolean;
    diff?: string;
    stat?: string;
    error?: string;
  }>;
}

// ============================================================================
// Mode Filters (backward compatible)
// ============================================================================

export const MODE_FILTERS: Record<WorkspaceMode, Partial<FilterConfig>> = {
  code: {
    allowedExtensions: [],
    hiddenPatterns: ["__pycache__", ".pyc", "node_modules", ".git/objects"],
  },
  vis: {
    allowedExtensions: [
      ".png",
      ".jpg",
      ".jpeg",
      ".svg",
      ".pdf",
      ".csv",
      ".json",
      ".xlsx",
      ".tsv",
    ],
    hiddenPatterns: ["__pycache__", "node_modules", ".git", ".venv"],
  },
  writer: {
    allowedExtensions: [
      ".tex",
      ".bib",
      ".pdf",
      ".png",
      ".jpg",
      ".jpeg",
      ".svg",
      ".eps",
    ],
    hiddenPatterns: [
      "__pycache__",
      "node_modules",
      ".git",
      ".venv",
      "build",
      ".aux",
      ".log",
      ".out",
    ],
  },
  scholar: {
    allowedExtensions: [".bib"],
    hiddenPatterns: ["__pycache__", "node_modules", ".git", ".venv", "build"],
  },
  clew: {
    allowedExtensions: [],
    hiddenPatterns: ["__pycache__", "node_modules", ".git", ".venv"],
  },
  hub: {
    allowedExtensions: [],
    hiddenPatterns: ["__pycache__", "node_modules", ".git", ".venv"],
  },
  files: {
    allowedExtensions: [],
    hiddenPatterns: ["__pycache__", "node_modules", ".git"],
  },
  tools: {
    allowedExtensions: [],
    hiddenPatterns: ["__pycache__", "node_modules", ".git", ".venv"],
  },
  example: {
    allowedExtensions: [],
    hiddenPatterns: ["__pycache__", "node_modules", ".git", ".venv"],
  },
  apps: {
    allowedExtensions: [],
    hiddenPatterns: ["__pycache__", "node_modules", ".git", ".venv"],
  },
  explorer: {
    allowedExtensions: [],
    hiddenPatterns: ["__pycache__", "node_modules", ".git", ".venv"],
  },
  all: {
    allowedExtensions: [],
    disabledExtensions: [],
    hiddenPatterns: [],
  },
};

export const DEFAULT_EXPAND_PATHS: Record<WorkspaceMode, string[]> = {
  code: ["scripts"],
  vis: [],
  writer: [],
  scholar: [],
  clew: [],
  hub: [],
  files: [],
  tools: [],
  example: [],
  apps: [],
  explorer: [],
  all: [],
};
