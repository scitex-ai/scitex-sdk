/**
 * Repository Monitor — Orchestrator (adapter-based)
 *
 * Ported from scitex-cloud.  The WebSocket transport is replaced by
 * RepoMonitorAdapter so standalone apps can poll REST endpoints.
 *
 * Usage:
 * ```typescript
 * import { initRepoMonitor, initMonitorToggle } from "scitex-ui/ts/shell/repo-monitor";
 * import { apiUrl } from "scitex-ui/ts/_base";
 *
 * initMonitorToggle();
 * initRepoMonitor({
 *   adapter: { fetchRecentFiles: () => fetch(apiUrl("/api/files")).then(r => r.json()) },
 *   pollIntervalMs: 10000,
 * });
 * ```
 *
 * THE `apiUrl()` IN THAT EXAMPLE IS LOAD-BEARING. This example previously
 * passed a bare relative path straight to fetch, and that is the failure it
 * now demonstrates the fix for.
 *
 * THE OFFENDING FORMS ARE DESCRIBED HERE, NEVER WRITTEN. A checker that scans
 * source text for unsafe request URLs has no reason to understand comments —
 * scitex-ui shipped a collectstatic outage on 2026-09-05 for exactly that
 * reason, where a path quoted inside a CSS comment was read as a live
 * reference. Writing a specimen of the defect next to its own warning is how
 * the warning becomes the defect.
 *
 * A path with no leading slash resolves against the DOCUMENT's URL, so it
 * works at `/app/` and 404s at `/app`: it survives a smoke test and breaks on
 * a redirect or a differently-written link. A path with a leading slash is
 * wrong in the other direction — it ignores the mount entirely and 404s
 * everywhere the app is not at the root. `apiUrl()` joins onto the mount
 * prefix and returns a well-formed path in both cases (root mount yields "").
 *
 * An example is copied verbatim; that is what it is for. So an unsafe one does
 * not merely fail to help — it manufactures the defect in every app that
 * follows it, and as of scitex-app 0.14.0 those apps fail scitex-hub's
 * publication gate rather than failing quietly at runtime.
 */

import { RepoMonitorClient } from "./_RepoMonitorClient";
import { RepoMonitorFeed } from "./_RepoMonitorFeed";
import { RepoMonitorFilter } from "./_RepoMonitorFilter";
import type { RepoMonitorConfig } from "./types";

const STORAGE_KEY = "repo-monitor-collapsed";
let toggleInitialized = false;

/**
 * Initialize the monitor header toggle (collapse/expand + localStorage).
 * Always safe to call — works even without a project context.
 * Idempotent: multiple calls are harmless.
 */
export function initMonitorToggle(): void {
  if (toggleInitialized) return;

  const monitorArea = document.getElementById("ws-repo-monitor");
  const headerEl = document.getElementById("repo-monitor-header");
  if (!monitorArea || !headerEl) return;

  toggleInitialized = true;

  // Restore persisted state
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved === "false") {
    monitorArea.classList.remove("collapsed");
  }

  // Header click toggles collapse (toolbar buttons handled independently)
  headerEl.addEventListener("click", (e) => {
    if ((e.target as HTMLElement).closest(".repo-monitor-toolbar")) return;
    monitorArea.classList.toggle("collapsed");
    const isCollapsed = monitorArea.classList.contains("collapsed");
    localStorage.setItem(STORAGE_KEY, String(isCollapsed));

    // Notify resizer and client if they exist
    window.dispatchEvent(
      new CustomEvent("repo-monitor:toggle", {
        detail: { collapsed: isCollapsed },
      }),
    );
  });
}

/**
 * Initialize the full repo monitor (polling client, feed, filter).
 * Requires DOM elements from standalone_shell.html.
 * Call initMonitorToggle() first.
 */
export function initRepoMonitor(
  config: RepoMonitorConfig,
): RepoMonitorClient | null {
  const feedContainer = document.getElementById("repo-monitor-feed");
  const monitorArea = document.getElementById("ws-repo-monitor");

  if (!feedContainer || !monitorArea) {
    console.warn("[RepoMonitor] Missing required DOM elements — init skipped");
    return null;
  }

  const client = new RepoMonitorClient(config.adapter, config.pollIntervalMs);
  const feed = new RepoMonitorFeed(feedContainer);
  const filter = new RepoMonitorFilter(feed);

  // Wire events
  client.onEvent((event) => feed.addEvent(event));
  filter.onFilterChange((filters) => client.reconfigure(filters));

  // Listen for toggle events from initMonitorToggle
  window.addEventListener("repo-monitor:toggle", ((e: CustomEvent) => {
    if (e.detail.collapsed) {
      client.pause();
    } else {
      client.resume();
    }
  }) as EventListener);

  // Connect and initialize
  client.connect();
  filter.init();

  return client;
}

// Named re-exports
export { RepoMonitorClient } from "./_RepoMonitorClient";
export { RepoMonitorFeed } from "./_RepoMonitorFeed";
export { RepoMonitorFilter } from "./_RepoMonitorFilter";
export type {
  FsEvent,
  FilterConfig,
  RepoMonitorConfig,
  RepoMonitorAdapter,
  RecentFileEntry,
} from "./types";
