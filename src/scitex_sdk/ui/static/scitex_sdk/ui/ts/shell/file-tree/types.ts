/**
 * Shell file tree types — adapter interface for backend abstraction.
 *
 * Consumers (figrecipe, scitex-cloud) provide concrete adapter implementations.
 * The shell file tree never hardcodes API endpoints.
 */

import type { FileNode, FileBrowserConfig } from "../../app/file-browser/types";

export type { FileNode };

/**
 * Backend adapter for file tree data.
 * Consumers implement this to connect to their specific backend.
 */
export interface FileTreeAdapter {
  /** Fetch the file tree data from the backend. */
  fetchTree(): Promise<FileNode[]>;

  /** Create a new file in the given parent directory (optional). */
  createFile?(parentPath: string, name: string): Promise<void>;

  /** Create a new folder in the given parent directory (optional). */
  createFolder?(parentPath: string, name: string): Promise<void>;

  /** Delete a file or folder (optional). */
  deleteItem?(path: string): Promise<void>;

  /** Rename a file or folder (optional). */
  renameItem?(oldPath: string, newName: string): Promise<void>;
}

export interface ShellFileTreeConfig {
  /** Container element or CSS selector (default: "#ws-worktree-tree") */
  container?: string | HTMLElement;

  /** Backend adapter for fetching tree data. */
  adapter: FileTreeAdapter;

  /** Called when user clicks a file. */
  onFileSelect?: (node: FileNode) => void;

  /** Called when user toggles a directory. */
  onDirectoryToggle?: (node: FileNode, expanded: boolean) => void;

  /** Show hidden files on initial load (default: reads from localStorage). */
  showHidden?: boolean;

  /** File extensions to show (null = all). */
  extensions?: string[] | null;

  /** Show git status badges (default: true). */
  showGitStatus?: boolean;

  /** Show folder action buttons (new file/folder) on hover (default: false). */
  showFolderActions?: boolean;
}
