/**
 * BridgeContract — TypeScript interfaces for the SciTeX app bridge system.
 *
 * Every app that docks into scitex-cloud implements this contract.
 * The bridge connects the app's React frontend to the workspace shell.
 */

/** Configuration for an app bridge (app-specific, declared in manifest.json). */
export interface BridgeConfig {
  /** App slug used for API routing and event namespacing. */
  slug: string;
  /** DOM element ID for the mount point. */
  mountId: string;
  /** API path prefixes that the fetch override should rewrite. */
  apiPaths: string[];
  /** File extensions this app handles (for file tree interception). */
  fileExtensions: string[];
}

/** Options passed to the app's mount function. */
export interface BridgeMountOptions {
  /** DOM container to render into. */
  container: HTMLElement;
  /** Project working directory (filesystem path, injected server-side). */
  workingDir?: string;
  /** Initial file to open. */
  initialFile?: string;
  /** Dark mode preference. */
  darkMode?: boolean;
}

/** Function signature for mounting an app. */
export type AppMounter = (options: BridgeMountOptions) => void;

/** Function signature for unmounting an app. */
export type AppUnmounter = () => void;
