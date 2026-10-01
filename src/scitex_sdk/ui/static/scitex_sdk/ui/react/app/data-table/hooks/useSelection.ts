/**
 * Multi-cell selection state and mouse event handlers.
 * Ported from scitex-cloud TableSelection.ts.
 */

import { useState, useCallback, useRef, useEffect } from "react";
import type { CellPosition } from "../types";
import type { SelectionRange } from "../utils/selectionHelpers";
import { normalizeRange } from "../utils/selectionHelpers";

// ----------------------------------------------------------------
// Types
// ----------------------------------------------------------------

export interface UseSelectionReturn {
  selection: SelectionRange | null;
  currentCell: CellPosition | null;
  selectedColumns: Set<number>;
  selectedRows: Set<number>;
  /** Cell mousedown: starts drag selection */
  handleCellMouseDown: (e: React.MouseEvent, row: number, col: number) => void;
  /** Cell mouseover: extends drag selection */
  handleCellMouseOver: (e: React.MouseEvent, row: number, col: number) => void;
  /** Column header mousedown: starts column selection */
  handleColumnHeaderMouseDown: (e: React.MouseEvent, col: number) => void;
  /** Column header mouseover: extends column selection */
  handleColumnHeaderMouseOver: (e: React.MouseEvent, col: number) => void;
  /** Row number mousedown: starts row selection */
  handleRowNumberMouseDown: (e: React.MouseEvent, row: number) => void;
  /** Row number mouseover: extends row selection */
  handleRowNumberMouseOver: (e: React.MouseEvent, row: number) => void;
  /** Programmatically select a single cell */
  selectCell: (row: number, col: number) => void;
  /** Move current cell (keeps selection range) */
  moveCurrentCell: (row: number, col: number) => void;
  /** Clear all selection state */
  clearSelection: () => void;
  setCurrentCell: (pos: CellPosition | null) => void;
  setSelection: (sel: SelectionRange | null) => void;
}

// ----------------------------------------------------------------
// Hook
// ----------------------------------------------------------------

export function useSelection(
  onCellSelect?: (pos: CellPosition) => void,
  onStatusUpdate?: (msg: string) => void,
  columns?: string[],
): UseSelectionReturn {
  const [selection, setSelection] = useState<SelectionRange | null>(null);
  const [currentCell, setCurrentCell] = useState<CellPosition | null>(null);
  const [selectedColumns, setSelectedColumns] = useState<Set<number>>(
    new Set(),
  );
  const [selectedRows, setSelectedRows] = useState<Set<number>>(new Set());

  const isDragging = useRef(false);
  const isSelectingCols = useRef(false);
  const isSelectingRows = useRef(false);
  const colSelectStart = useRef(-1);
  const rowSelectStart = useRef(-1);

  // Global mouseup: stop all dragging
  useEffect(() => {
    const onMouseUp = () => {
      if (isDragging.current && selection) {
        const { minRow, minCol } = normalizeRange(selection);
        setCurrentCell({ row: minRow, col: minCol });
      }
      isDragging.current = false;
      isSelectingCols.current = false;
      isSelectingRows.current = false;
    };
    document.addEventListener("mouseup", onMouseUp);
    return () => document.removeEventListener("mouseup", onMouseUp);
  }, [selection]);

  // ---- Cell events ----

  const handleCellMouseDown = useCallback(
    (e: React.MouseEvent, row: number, col: number) => {
      if (e.button !== 0) return;
      e.preventDefault();
      setSelectedColumns(new Set());
      setSelectedRows(new Set());
      setSelection({ start: { row, col }, end: { row, col } });
      setCurrentCell({ row, col });
      isDragging.current = true;
      onCellSelect?.({ row, col });
      onStatusUpdate?.(`Cell (${row + 1}, ${columns?.[col] ?? col + 1})`);
    },
    [onCellSelect, onStatusUpdate, columns],
  );

  const handleCellMouseOver = useCallback(
    (_e: React.MouseEvent, row: number, col: number) => {
      if (!isDragging.current) return;
      setSelection((prev) =>
        prev ? { start: prev.start, end: { row, col } } : null,
      );
    },
    [],
  );

  // ---- Column header events ----

  const handleColumnHeaderMouseDown = useCallback(
    (e: React.MouseEvent, col: number) => {
      if (
        (e.target as HTMLElement).classList.contains(
          "stx-app-data-table__resize-handle",
        )
      )
        return;
      e.preventDefault();
      setSelectedColumns(new Set([col]));
      setSelectedRows(new Set());
      setSelection(null);
      setCurrentCell(null);
      isSelectingCols.current = true;
      colSelectStart.current = col;
    },
    [],
  );

  const handleColumnHeaderMouseOver = useCallback(
    (_e: React.MouseEvent, col: number) => {
      if (!isSelectingCols.current) return;
      const start = Math.min(colSelectStart.current, col);
      const end = Math.max(colSelectStart.current, col);
      setSelectedColumns(
        new Set(Array.from({ length: end - start + 1 }, (_, i) => start + i)),
      );
    },
    [],
  );

  // ---- Row number events ----

  const handleRowNumberMouseDown = useCallback(
    (e: React.MouseEvent, row: number) => {
      e.preventDefault();
      setSelectedRows(new Set([row]));
      setSelectedColumns(new Set());
      setSelection(null);
      setCurrentCell(null);
      isSelectingRows.current = true;
      rowSelectStart.current = row;
    },
    [],
  );

  const handleRowNumberMouseOver = useCallback(
    (_e: React.MouseEvent, row: number) => {
      if (!isSelectingRows.current) return;
      const start = Math.min(rowSelectStart.current, row);
      const end = Math.max(rowSelectStart.current, row);
      setSelectedRows(
        new Set(Array.from({ length: end - start + 1 }, (_, i) => start + i)),
      );
    },
    [],
  );

  // ---- Programmatic selection ----

  const selectCell = useCallback((row: number, col: number) => {
    setSelection({ start: { row, col }, end: { row, col } });
    setCurrentCell({ row, col });
    setSelectedColumns(new Set());
    setSelectedRows(new Set());
  }, []);

  const moveCurrentCell = useCallback((row: number, col: number) => {
    setCurrentCell({ row, col });
    setSelection({ start: { row, col }, end: { row, col } });
    setSelectedColumns(new Set());
    setSelectedRows(new Set());
  }, []);

  const clearSelection = useCallback(() => {
    setSelection(null);
    setCurrentCell(null);
    setSelectedColumns(new Set());
    setSelectedRows(new Set());
  }, []);

  return {
    selection,
    currentCell,
    selectedColumns,
    selectedRows,
    handleCellMouseDown,
    handleCellMouseOver,
    handleColumnHeaderMouseDown,
    handleColumnHeaderMouseOver,
    handleRowNumberMouseDown,
    handleRowNumberMouseOver,
    selectCell,
    moveCurrentCell,
    clearSelection,
    setCurrentCell,
    setSelection,
  };
}
