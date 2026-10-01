/**
 * Workspace Files Tree - Main Export
 * Unified file tree component for all workspace modules
 *
 * Ported from scitex-cloud with FileTreeAdapter abstraction.
 *
 * Usage:
 * ```typescript
 * import { WorkspaceFilesTree } from './workspace-files-tree';
 *
 * const tree = new WorkspaceFilesTree({
 *   mode: 'code',
 *   containerId: 'file-tree',
 *   ownerUsername: 'test-user',
 *   projectSlug: 'my-project',
 *   adapter: myAdapter,
 *   onFileSelect: (path, item) => {
 *     console.log('Selected:', path);
 *   },
 * });
 *
 * await tree.initialize();
 * ```
 */

export { WorkspaceFilesTree } from "./WorkspaceFilesTree";
export { TreeStateManager } from "./_TreeState";
export { TreeFilter } from "./_TreeFilter";
export { TreeRenderer } from "./_TreeRenderer";
export type {
  TreeItem,
  TreeConfig,
  TreeState,
  FilterConfig,
  WorkspaceMode,
  FileTreeAdapter,
  GitFileStat,
} from "./types";
export { MODE_FILTERS } from "./types";
