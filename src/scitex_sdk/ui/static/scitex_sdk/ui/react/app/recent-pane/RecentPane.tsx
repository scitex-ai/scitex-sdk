/**
 * RecentPane -- Real-time file change feed.
 * Port of scitex-cloud's repo-monitor as a pluggable React component.
 *
 * The component is backend-agnostic: the parent supplies `entries` and
 * wires pause/resume/clear callbacks.  This keeps the component reusable
 * across WebSocket, polling, or any other transport.
 */

import React, { useRef, useEffect, useCallback } from "react";
import type { BaseProps } from "../../_base/types";

const CLS = "stx-app-recent-pane";

/* ------------------------------------------------------------------
   Public types
   ------------------------------------------------------------------ */

export interface RecentEntry {
  path: string;
  event: "create" | "modify" | "delete" | "move";
  timestamp: number;
}

export interface RecentPaneProps extends BaseProps {
  /** Ordered list of recent file events (newest first). */
  entries: RecentEntry[];
  /** Maximum entries to display (default: 500). */
  count?: number;
  /** Whether the feed is paused. */
  paused?: boolean;
  /** Request the parent to pause the feed. */
  onPause?: () => void;
  /** Request the parent to resume the feed. */
  onResume?: () => void;
  /** Request the parent to clear all entries. */
  onClear?: () => void;
  /** Called when a user clicks on an entry. */
  onEntryClick?: (path: string) => void;
  /** Whether the pane is collapsed (shows header only). */
  collapsed?: boolean;
  /** Toggle collapsed state. */
  onToggleCollapse?: () => void;
}

/* ------------------------------------------------------------------
   Constants
   ------------------------------------------------------------------ */

const EVENT_LABELS: Record<RecentEntry["event"], string> = {
  create: "+",
  modify: "~",
  delete: "\u2212", // minus sign
  move: "\u2192", // right arrow
};

/* ------------------------------------------------------------------
   Helpers
   ------------------------------------------------------------------ */

function formatTime(ts: number): string {
  try {
    const d = new Date(ts);
    if (isNaN(d.getTime())) return "";
    return d.toLocaleTimeString(undefined, { hour12: false });
  } catch {
    return "";
  }
}

function basename(path: string): string {
  const parts = path.split("/");
  return parts[parts.length - 1] || path;
}

/* ------------------------------------------------------------------
   Component
   ------------------------------------------------------------------ */

export const RecentPane: React.FC<RecentPaneProps> = ({
  entries,
  count = 500,
  paused = false,
  onPause,
  onResume,
  onClear,
  onEntryClick,
  collapsed = false,
  onToggleCollapse,
  className,
  style,
}) => {
  const feedRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to top when new entries arrive and user is already at top
  const prevLengthRef = useRef(entries.length);
  useEffect(() => {
    const el = feedRef.current;
    if (!el) return;
    if (entries.length > prevLengthRef.current && el.scrollTop === 0) {
      el.scrollTop = 0;
    }
    prevLengthRef.current = entries.length;
  }, [entries.length]);

  const handleHeaderClick = useCallback(
    (e: React.MouseEvent) => {
      // Ignore clicks on toolbar buttons
      if ((e.target as HTMLElement).closest(`.${CLS}__toolbar`)) return;
      onToggleCollapse?.();
    },
    [onToggleCollapse],
  );

  const handlePauseResume = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      if (paused) {
        onResume?.();
      } else {
        onPause?.();
      }
    },
    [paused, onPause, onResume],
  );

  const handleClear = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onClear?.();
    },
    [onClear],
  );

  const visible = entries.slice(0, count);

  return (
    <div
      className={`${CLS}${collapsed ? " collapsed" : ""} ${className ?? ""}`}
      style={style}
    >
      {/* Header */}
      <div className={`${CLS}__header`} onClick={handleHeaderClick}>
        <span className={`${CLS}__icon`}>{"\u23F1"}</span>
        <span className={`${CLS}__title`}>Recent</span>
        <span className={`${CLS}__badge`}>{entries.length}</span>

        <div className={`${CLS}__toolbar`}>
          {/* Settings (disabled placeholder) */}
          <button
            className={`${CLS}__btn`}
            disabled
            title="Settings (coming soon)"
            onClick={(e) => e.stopPropagation()}
          >
            {"\u2699"}
          </button>

          {/* Pause / Resume */}
          <button
            className={`${CLS}__btn${paused ? ` ${CLS}__btn--active` : ""}`}
            title={paused ? "Resume" : "Pause"}
            onClick={handlePauseResume}
          >
            {paused ? "\u25B6" : "\u23F8"}
          </button>

          {/* Clear */}
          <button className={`${CLS}__btn`} title="Clear" onClick={handleClear}>
            {"\u2715"}
          </button>
        </div>
      </div>

      {/* Feed (hidden when collapsed) */}
      {!collapsed && (
        <div className={`${CLS}__feed`} ref={feedRef}>
          {visible.length === 0 ? (
            <div className={`${CLS}__empty`}>No recent changes</div>
          ) : (
            visible.map((entry, idx) => (
              <div
                key={`${entry.path}-${entry.timestamp}-${idx}`}
                className={`${CLS}__entry ${CLS}__entry--${entry.event}`}
                title={entry.path}
                onClick={() => onEntryClick?.(entry.path)}
              >
                <span className={`${CLS}__event-icon`}>
                  {EVENT_LABELS[entry.event]}
                </span>
                <span className={`${CLS}__path`}>{basename(entry.path)}</span>
                <span className={`${CLS}__time`}>
                  {formatTime(entry.timestamp)}
                </span>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};
