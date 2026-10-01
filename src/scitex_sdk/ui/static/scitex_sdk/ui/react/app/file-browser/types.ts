/**
 * Type definitions for the FileBrowser React component.
 * Mirrors: ts/app/file-browser/types.ts
 * Extended to match scitex-cloud TreeItem for full API compatibility.
 */

import type { BaseProps } from "../../_base/types";

export interface FileNode {
  name: string;
  path: string;
  type: "file" | "directory";
  children?: FileNode[];
  has_image?: boolean;
  is_current?: boolean;
  /** Symlink support — mirrors scitex-cloud TreeItem */
  is_symlink?: boolean;
  symlink_target?: string;
  /** Git status — mirrors scitex-cloud TreeItem */
  git_status?: {
    status: string; // M, A, D, ??
    staged: boolean;
  };
  mtime?: number;
  meta?: Record<string, unknown>;
}

export interface FileBrowserProps extends BaseProps {
  /** File tree data */
  data?: FileNode[];
  /** API endpoint to fetch file tree */
  apiUrl?: string;
  /** Called when user clicks a file */
  onFileSelect?: (node: FileNode) => void;
  /** Called when user toggles a directory */
  onDirectoryToggle?: (node: FileNode, expanded: boolean) => void;
  /** File extensions to show (null = all) */
  extensions?: string[] | null;
  /** Show hidden files (default: false) */
  showHidden?: boolean;
  /** Show image badge for files with has_image (default: true) */
  showImageBadge?: boolean;
  /** Show file count header (default: false) */
  showFileCount?: boolean;
  /** Enable Ctrl+K file search (default: false) */
  searchable?: boolean;
  /** Context menu action handler (right-click on file/dir) */
  onContextAction?: (
    action: "new" | "rename" | "delete" | "duplicate" | "copy-path",
    node: FileNode,
  ) => void;
  /** Sort mode — 'name' (A-Z) or 'mtime' (newest first). Ported from scitex-cloud SortToggle */
  sortMode?: "name" | "mtime";
  /** Called when user double-clicks a file (open in editor/viewer) */
  onFileDoubleClick?: (node: FileNode) => void;
}
