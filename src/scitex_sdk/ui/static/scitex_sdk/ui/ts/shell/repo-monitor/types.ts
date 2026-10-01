/**
 * Repository Monitor — Shared types
 *
 * Ported from scitex-cloud with adapter pattern:
 * the WebSocket-specific transport is replaced by RepoMonitorAdapter,
 * allowing standalone apps to poll REST endpoints instead.
 */

/* ---- Domain types (unchanged from scitex-cloud) ---- */

export interface FsEvent {
  type: "fs_event";
  event: "create" | "modify" | "delete" | "move";
  path: string;
  timestamp: string;
}

export interface FilterConfig {
  respectGitignore: boolean;
  blacklistPatterns: string[];
  whitelistPatterns: string[];
}

export type EventCallback = (event: FsEvent) => void;
export type FilterChangeCallback = (filters: FilterConfig) => void;

export const DEFAULT_FILTER_CONFIG: FilterConfig = {
  respectGitignore: true,
  blacklistPatterns: [".*"],
  whitelistPatterns: [],
};

/* ---- Adapter interfaces ---- */

/** A single recently-changed file returned by the adapter. */
export interface RecentFileEntry {
  path: string;
  name: string;
  modified_at: string;
  action?: "create" | "modify" | "delete" | "move";
}

/**
 * Backend adapter — abstracts how recent file changes are fetched.
 *
 * For scitex-cloud: wraps WebSocket messages.
 * For standalone apps: polls an HTTP endpoint (e.g. api/files).
 */
export interface RepoMonitorAdapter {
  /** Fetch the current list of recently modified files. */
  fetchRecentFiles(): Promise<RecentFileEntry[]>;
  /** Optional: resolve a clickable URL for a file path. */
  getFileUrl?(path: string): string;
}

/* ---- Orchestrator config ---- */

export interface RepoMonitorConfig {
  adapter: RepoMonitorAdapter;
  /** Polling interval in ms (only used for polling adapters). Default: 10000 */
  pollIntervalMs?: number;
}
