/**
 * Column resize — drag header border to resize columns.
 * Ported from scitex-cloud TableColumnRow.ts setupColumnResizing.
 */

import { useState, useCallback } from "react";
import { TABLE_CONSTANTS } from "../types";

const COL_WIDTH = TABLE_CONSTANTS.COL_WIDTH;

// ----------------------------------------------------------------
// Types
// ----------------------------------------------------------------

export interface UseColumnResizeReturn {
  colWidths: Map<number, number>;
  getColWidth: (col: number) => number;
  handleResizeStart: (colIdx: number, e: React.MouseEvent) => void;
}

// ----------------------------------------------------------------
// Hook
// ----------------------------------------------------------------

export function useColumnResize(): UseColumnResizeReturn {
  const [colWidths, setColWidths] = useState<Map<number, number>>(new Map());

  const getColWidth = useCallback(
    (col: number): number => colWidths.get(col) ?? COL_WIDTH,
    [colWidths],
  );

  const handleResizeStart = useCallback(
    (colIdx: number, e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();

      const startX = e.clientX;
      const startW = colWidths.get(colIdx) ?? COL_WIDTH;

      const onMove = (ev: MouseEvent) => {
        const newW = Math.max(30, startW + (ev.clientX - startX));
        setColWidths((prev) => {
          const next = new Map(prev);
          next.set(colIdx, newW);
          return next;
        });
      };

      const onUp = () => {
        document.removeEventListener("mousemove", onMove);
        document.removeEventListener("mouseup", onUp);
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
      };

      document.addEventListener("mousemove", onMove);
      document.addEventListener("mouseup", onUp);
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
    },
    [colWidths],
  );

  return { colWidths, getColWidth, handleResizeStart };
}
