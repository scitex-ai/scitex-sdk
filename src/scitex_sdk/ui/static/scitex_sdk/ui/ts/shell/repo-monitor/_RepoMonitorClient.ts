/**
 * Repository Monitor Polling Client
 *
 * Replaces scitex-cloud's WebSocket client with a polling loop
 * driven by RepoMonitorAdapter.fetchRecentFiles().
 *
 * Keeps the same public API surface (onEvent, pause, resume, disconnect)
 * so the Feed and Filter components work unchanged.
 */

import type {
  RepoMonitorAdapter,
  RecentFileEntry,
  FsEvent,
  FilterConfig,
  EventCallback,
} from "./types";
import { DEFAULT_FILTER_CONFIG } from "./types";

const DEFAULT_POLL_MS = 10_000;
const STORAGE_KEY = "scitex-repo-monitor-filters";

export class RepoMonitorClient {
  private adapter: RepoMonitorAdapter;
  private pollMs: number;
  private callbacks: EventCallback[] = [];
  private timer: ReturnType<typeof setInterval> | null = null;
  private isPaused = false;
  /** Tracks paths we have already seen so we only emit new/changed entries. */
  private knownModTimes: Map<string, string> = new Map();

  constructor(adapter: RepoMonitorAdapter, pollMs?: number) {
    this.adapter = adapter;
    this.pollMs = pollMs ?? DEFAULT_POLL_MS;
  }

  /** Start the polling loop. */
  connect(): void {
    // Run once immediately, then on interval.
    this.poll();
    this.timer = setInterval(() => this.poll(), this.pollMs);
  }

  onEvent(callback: EventCallback): void {
    this.callbacks.push(callback);
  }

  reconfigure(_filters: FilterConfig): void {
    // Filters are applied client-side by RepoMonitorFilter;
    // the polling adapter returns all recent files and the filter decides
    // which entries to show.  This method exists for API compatibility.
  }

  pause(): void {
    this.isPaused = true;
  }

  resume(): void {
    this.isPaused = false;
    // Catch up immediately.
    this.poll();
  }

  disconnect(): void {
    if (this.timer !== null) {
      clearInterval(this.timer);
      this.timer = null;
    }
  }

  isConnected(): boolean {
    return this.timer !== null;
  }

  /* ---- internals ---- */

  private async poll(): Promise<void> {
    if (this.isPaused) return;

    let entries: RecentFileEntry[];
    try {
      entries = await this.adapter.fetchRecentFiles();
    } catch (err) {
      console.warn("[RepoMonitorClient] poll failed:", err);
      return;
    }

    for (const entry of entries) {
      const prevMod = this.knownModTimes.get(entry.path);
      if (prevMod === entry.modified_at) continue; // no change

      this.knownModTimes.set(entry.path, entry.modified_at);

      const action = entry.action ?? (prevMod ? "modify" : "create");

      const event: FsEvent = {
        type: "fs_event",
        event: action,
        path: entry.path,
        timestamp: entry.modified_at,
      };

      this.callbacks.forEach((cb) => cb(event));
    }
  }

  /** Load persisted filter config from localStorage. */
  loadFilters(): FilterConfig {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) return JSON.parse(raw) as FilterConfig;
    } catch {
      // ignore
    }
    return DEFAULT_FILTER_CONFIG;
  }
}
