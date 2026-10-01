/**
 * Virtual scrolling for large datasets.
 * Ported from scitex-cloud TableRendering.ts virtual scroll logic.
 *
 * Only renders visible rows + buffer to keep the DOM small.
 * Uses requestAnimationFrame for smooth scroll handling.
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { TABLE_CONSTANTS } from "../types";

const ROW_HEIGHT = TABLE_CONSTANTS.ROW_HEIGHT; // px
const BUFFER_ROWS = 10;

// ----------------------------------------------------------------
// Types
// ----------------------------------------------------------------

export interface VirtualScrollState {
  renderStart: number;
  renderEnd: number;
  topSpacerHeight: number;
  bottomSpacerHeight: number;
  /** Ref to attach to the scroll container */
  scrollContainerRef: React.RefObject<HTMLDivElement>;
}

// ----------------------------------------------------------------
// Hook
// ----------------------------------------------------------------

export function useVirtualScroll(
  totalRows: number,
  enabled: boolean,
): VirtualScrollState {
  const [visibleRange, setVisibleRange] = useState({ start: 0, end: 50 });
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const rafIdRef = useRef<number | null>(null);
  const lastScrollTopRef = useRef(0);

  // Recalculate initial visible range when total rows or container changes
  useEffect(() => {
    const el = scrollContainerRef.current;
    const containerHeight = el?.clientHeight ?? 400;
    const visibleCount = Math.ceil(containerHeight / ROW_HEIGHT);
    setVisibleRange({
      start: 0,
      end: Math.min(visibleCount + BUFFER_ROWS, totalRows),
    });
  }, [totalRows]);

  const updateVisibleRange = useCallback(() => {
    const el = scrollContainerRef.current;
    if (!el || !enabled) return;

    const scrollTop = el.scrollTop;
    if (Math.abs(scrollTop - lastScrollTopRef.current) < ROW_HEIGHT / 2) return;
    lastScrollTopRef.current = scrollTop;

    const containerHeight = el.clientHeight;
    const firstVisible = Math.floor(scrollTop / ROW_HEIGHT);
    const visibleCount = Math.ceil(containerHeight / ROW_HEIGHT);

    const newStart = Math.max(0, firstVisible - BUFFER_ROWS);
    const newEnd = Math.min(
      totalRows,
      firstVisible + visibleCount + BUFFER_ROWS,
    );

    setVisibleRange((prev) => {
      if (
        Math.abs(newStart - prev.start) > BUFFER_ROWS / 2 ||
        Math.abs(newEnd - prev.end) > BUFFER_ROWS / 2
      ) {
        return { start: newStart, end: newEnd };
      }
      return prev;
    });
  }, [totalRows, enabled]);

  // Attach scroll listener
  useEffect(() => {
    const el = scrollContainerRef.current;
    if (!el || !enabled) return;

    const onScroll = () => {
      if (rafIdRef.current) cancelAnimationFrame(rafIdRef.current);
      rafIdRef.current = requestAnimationFrame(() => updateVisibleRange());
    };

    el.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      el.removeEventListener("scroll", onScroll);
      if (rafIdRef.current) cancelAnimationFrame(rafIdRef.current);
    };
  }, [enabled, updateVisibleRange]);

  const renderStart = enabled ? visibleRange.start : 0;
  const renderEnd = enabled ? visibleRange.end : totalRows;

  return {
    renderStart,
    renderEnd,
    topSpacerHeight: enabled ? renderStart * ROW_HEIGHT : 0,
    bottomSpacerHeight: enabled
      ? Math.max(0, (totalRows - renderEnd) * ROW_HEIGHT)
      : 0,
    scrollContainerRef,
  };
}
