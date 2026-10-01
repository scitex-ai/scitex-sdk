/**
 * Cell editing state and keyboard navigation.
 * Ported from scitex-cloud TableEditing.ts.
 */

import { useState, useCallback } from "react";
import type { Dataset } from "../types";
import type { DataAction } from "./useDataReducer";
import type {
  NormalizedBounds,
  SelectionRange,
} from "../utils/selectionHelpers";
import { normalizeRange } from "../utils/selectionHelpers";

// ----------------------------------------------------------------
// Types
// ----------------------------------------------------------------

/**
 * Bounds that Tab / Enter wrap-around navigation stays inside: the selected
 * range when a real multi-cell range is selected, otherwise the whole grid.
 *
 * Read the corners through `normalizeRange` — `SelectionRange` stores its
 * corners as `start`/`end` `CellPosition`s, so flat `startRow`/`endCol`-style
 * reads yield `undefined` and every derived bound becomes `NaN`.
 */
function navigationBounds(
  selection: SelectionRange | null,
  maxRow: number,
  maxCol: number,
): NormalizedBounds {
  const isMultiCell =
    selection !== null &&
    (selection.start.row !== selection.end.row ||
      selection.start.col !== selection.end.col);
  if (!isMultiCell) return { minRow: 0, maxRow, minCol: 0, maxCol };
  return normalizeRange(selection);
}

export interface EditingState {
  row: number;
  col: number;
  value: string;
  /** true when editing a column header (col rename) */
  isHeader: boolean;
}

export interface UseEditingReturn {
  editing: EditingState | null;
  startEditing: (
    row: number,
    col: number,
    initialValue: string,
    isHeader?: boolean,
  ) => void;
  commitEdit: () => void;
  cancelEdit: () => void;
  setEditValue: (value: string) => void;
  handleCellKeyDown: (
    e: React.KeyboardEvent,
    row: number,
    col: number,
    data: Dataset,
    selection: SelectionRange | null,
    moveCurrentCell: (row: number, col: number) => void,
    dispatchData: (action: DataAction) => void,
    readOnly: boolean,
  ) => void;
}

// ----------------------------------------------------------------
// Hook
// ----------------------------------------------------------------

export function useEditing(
  data: Dataset,
  dispatchData: (action: DataAction) => void,
): UseEditingReturn {
  const [editing, setEditing] = useState<EditingState | null>(null);

  const startEditing = useCallback(
    (row: number, col: number, initialValue: string, isHeader = false) => {
      setEditing({ row, col, value: initialValue, isHeader });
    },
    [],
  );

  const commitEdit = useCallback(() => {
    setEditing((prev) => {
      if (!prev) return null;
      const { row, col, value, isHeader } = prev;
      if (isHeader) {
        const oldName = data.columns[col];
        const newName = value.trim() || `${col + 1}`;
        dispatchData({ type: "SET_HEADER", col, oldName, newName });
      } else {
        const trimmed = value.trim();
        const num = parseFloat(trimmed);
        const parsed = trimmed !== "" && !isNaN(num) ? num : trimmed;
        dispatchData({ type: "SET_CELL", row, col, value: parsed });
      }
      return null;
    });
  }, [data.columns, dispatchData]);

  const cancelEdit = useCallback(() => {
    setEditing(null);
  }, []);

  const setEditValue = useCallback((value: string) => {
    setEditing((prev) => (prev ? { ...prev, value } : null));
  }, []);

  /**
   * Handle keydown while a cell is focused (may or may not be editing).
   * Returns early if the key was fully handled.
   */
  const handleCellKeyDown = useCallback(
    (
      e: React.KeyboardEvent,
      row: number,
      col: number,
      _data: Dataset,
      selection: SelectionRange | null,
      moveCurrentCell: (r: number, c: number) => void,
      dispatch: (action: DataAction) => void,
      readOnly: boolean,
    ) => {
      const maxRow = data.rows.length - 1;
      const maxCol = data.columns.length - 1;

      if (editing) {
        switch (e.key) {
          case "Escape":
            e.preventDefault();
            cancelEdit();
            return;
          case "Enter": {
            e.preventDefault();
            commitEdit();
            if (!editing.isHeader) {
              // Selection-aware: wrap within bounds
              const {
                minRow: mnR,
                maxRow: mxR,
                minCol: mnC,
                maxCol: mxC,
              } = navigationBounds(selection, maxRow, maxCol);
              if (row < mxR) moveCurrentCell(row + 1, col);
              else moveCurrentCell(mnR, col < mxC ? col + 1 : mnC);
            }
            return;
          }
          case "Tab": {
            e.preventDefault();
            commitEdit();
            if (!editing.isHeader) {
              // Selection-aware: wrap within bounds
              const {
                minRow: mnR,
                maxRow: mxR,
                minCol: mnC,
                maxCol: mxC,
              } = navigationBounds(selection, maxRow, maxCol);
              if (!e.shiftKey) {
                if (col < mxC) moveCurrentCell(row, col + 1);
                else moveCurrentCell(row < mxR ? row + 1 : mnR, mnC);
              } else {
                if (col > mnC) moveCurrentCell(row, col - 1);
                else moveCurrentCell(row > mnR ? row - 1 : mxR, mxC);
              }
            }
            return;
          }
          case "F2":
            e.preventDefault();
            cancelEdit();
            return;
          default:
            return; // Let input handle other keys
        }
      }

      // Navigation mode
      switch (e.key) {
        case "ArrowUp":
          e.preventDefault();
          if (row > 0) moveCurrentCell(row - 1, col);
          break;
        case "ArrowDown":
          e.preventDefault();
          if (row < maxRow) moveCurrentCell(row + 1, col);
          break;
        case "ArrowLeft":
          e.preventDefault();
          if (col > 0) moveCurrentCell(row, col - 1);
          break;
        case "ArrowRight":
          e.preventDefault();
          if (col < maxCol) moveCurrentCell(row, col + 1);
          break;
        case "Tab": {
          e.preventDefault();
          // Selection-aware: stay within selection bounds if range selected
          const {
            minRow: minR,
            maxRow: maxR,
            minCol: minC,
            maxCol: maxC,
          } = navigationBounds(selection, maxRow, maxCol);
          if (!e.shiftKey) {
            if (col < maxC) moveCurrentCell(row, col + 1);
            else moveCurrentCell(row < maxR ? row + 1 : minR, minC);
          } else {
            if (col > minC) moveCurrentCell(row, col - 1);
            else moveCurrentCell(row > minR ? row - 1 : maxR, maxC);
          }
          break;
        }
        case "Enter": {
          e.preventDefault();
          if (!readOnly && !e.shiftKey) {
            const val = data.rows[row]?.[data.columns[col]];
            startEditing(row, col, String(val ?? ""));
          } else {
            // Shift+Enter: move up; Enter in readOnly: move down
            const {
              minRow: mnR,
              maxRow: mxR,
              minCol: mnC,
              maxCol: mxC,
            } = navigationBounds(selection, maxRow, maxCol);
            if (e.shiftKey) {
              if (row > mnR) moveCurrentCell(row - 1, col);
              else moveCurrentCell(mxR, col < mxC ? col + 1 : mnC);
            } else {
              if (row < mxR) moveCurrentCell(row + 1, col);
              else moveCurrentCell(mnR, col < mxC ? col + 1 : mnC);
            }
          }
          break;
        }
        case "F2":
          e.preventDefault();
          if (!readOnly) {
            const val = data.rows[row]?.[data.columns[col]];
            startEditing(row, col, String(val ?? ""));
          }
          break;
        case "Delete":
        case "Backspace":
          e.preventDefault();
          if (!readOnly && selection) {
            const {
              minRow,
              maxRow: mr,
              minCol,
              maxCol: mc,
            } = normalizeRange(selection);
            dispatch({
              type: "CLEAR_RANGE",
              minRow,
              maxRow: mr,
              minCol,
              maxCol: mc,
            });
          }
          break;
        default:
          // Printable character starts editing
          if (!readOnly && e.key.length === 1 && !e.ctrlKey && !e.metaKey) {
            startEditing(row, col, e.key);
          }
          break;
      }
    },
    [editing, data, commitEdit, cancelEdit, startEditing],
  );

  return {
    editing,
    startEditing,
    commitEdit,
    cancelEdit,
    setEditValue,
    handleCellKeyDown,
  };
}
