/**
 * Type definitions for the FileBrowser component.
 */

import type { BaseComponentConfig } from "../../_base/types";
import type { GitStatus } from "./_git-status";

export interface FileNode {
  name: string;
  path: string;
  type: "file" | "directory";
  children?: FileNode[];
  /** Whether a companion image exists (e.g. PNG for a YAML recipe) */
  has_image?: boolean;
  /** Whether this file is currently selected/active in the editor */
  is_current?: boolean;
  /** Whether this entry is a symlink */
  is_symlink?: boolean;
  /** Symlink target path (shown as " → target") */
  symlink_target?: string;
  /** Git status for this file/directory */
  git_status?: GitStatus;
  /** App-specific metadata (passed through, not rendered by default) */
  meta?: Record<string, unknown>;
}

export interface FileBrowserConfig extends BaseComponentConfig {
  /** API endpoint to fetch file tree (optional — use setData instead) */
  apiUrl?: string;
  /** Called when user clicks a file */
  onFileSelect?: (node: FileNode) => void;
  /** Called when user toggles a directory */
  onDirectoryToggle?: (node: FileNode, expanded: boolean) => void;
  /** File extensions to show (e.g. [".py", ".ts"]) — null shows all */
  extensions?: string[] | null;
  /** Show hidden files (default: false) */
  showHidden?: boolean;
  /** Show image badge indicator for files with has_image=true (default: true) */
  showImageBadge?: boolean;
  /** Show file count in header (default: false) */
  showFileCount?: boolean;
}
