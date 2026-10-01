/**
 * Excel-like fill handle — drag to fill cells down or right.
 * Ported from scitex-cloud TableFillHandle.ts.
 */

import { useState, useCallback, useRef } from "react";
import type { SelectionRange } from "../utils/selectionHelpers";
import { normalizeRange } from "../utils/selectionHelpers";
import type { DataAction } from "./useDataReducer";

// ----------------------------------------------------------------
// Types
// ----------------------------------------------------------------

export interface FillHandleState {
  active: boolean;
  source: SelectionRange;
  targetRow: number;
  targetCol: number;
}

export interface UseFillHandleReturn {
  fillHandle: FillHandleState | null;
  handleFillHandleMouseDown: (e: React.MouseEvent) => void;
  /** True when cell is inside fill preview area */
  isFillPreview: (row: number, col: number) => boolean;
}

// ----------------------------------------------------------------
// Hook
// ----------------------------------------------------------------

export function useFillHandle(
  selection: SelectionRange | null,
  dispatchData: (action: DataAction) => void,
  onStatusUpdate?: (msg: string) => void,
): UseFillHandleReturn {
  const [fillHandle, setFillHandle] = useState<FillHandleState | null>(null);
  const fillHandleRef = useRef<FillHandleState | null>(null);
  fillHandleRef.current = fillHandle;

  const handleFillHandleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (!selection) return;
      e.preventDefault();
      e.stopPropagation();

      const { minRow, maxRow, minCol, maxCol } = normalizeRange(selection);
      const state: FillHandleState = {
        active: true,
        source: {
          start: { row: minRow, col: minCol },
          end: { row: maxRow, col: maxCol },
        },
        targetRow: maxRow,
        targetCol: maxCol,
      };
      setFillHandle(state);

      const onMove = (ev: MouseEvent) => {
        const el = document.elementFromPoint(
          ev.clientX,
          ev.clientY,
        ) as HTMLElement | null;
        if (!el) return;
        const row = parseInt(el.getAttribute("data-row") ?? "-1");
        const col = parseInt(el.getAttribute("data-col") ?? "-1");
        if (row >= 0 && col >= 0) {
          setFillHandle((prev) =>
            prev ? { ...prev, targetRow: row, targetCol: col } : null,
          );
        }
      };

      const onUp = () => {
        const fh = fillHandleRef.current;
        if (fh) {
          const { start, end } = fh.source;
          dispatchData({
            type: "FILL",
            startRow: start.row,
            endRow: end.row,
            startCol: start.col,
            endCol: end.col,
            fillRow: fh.targetRow,
            fillCol: fh.targetCol,
          });
          onStatusUpdate?.("Fill completed");
        }
        setFillHandle(null);
        document.removeEventListener("mousemove", onMove);
        document.removeEventListener("mouseup", onUp);
      };

      document.addEventListener("mousemove", onMove);
      document.addEventListener("mouseup", onUp);
    },
    [selection, dispatchData, onStatusUpdate],
  );

  const isFillPreview = useCallback(
    (row: number, col: number): boolean => {
      if (!fillHandle?.active) return false;
      const { start, end } = fillHandle.source;
      const { targetRow: fr, targetCol: fc } = fillHandle;
      // Fill down preview
      if (fr > end.row) {
        return row > end.row && row <= fr && col >= start.col && col <= end.col;
      }
      // Fill right preview
      if (fc > end.col) {
        return col > end.col && col <= fc && row >= start.row && row <= end.row;
      }
      return false;
    },
    [fillHandle],
  );

  return { fillHandle, handleFillHandleMouseDown, isFillPreview };
}
