/**
 * Dataset state management via useReducer.
 * Ported from scitex-cloud TableData / TableEditing / TableClipboard / TableFillHandle logic.
 */

import { useReducer } from "react";
import type { Dataset, DataRow } from "../types";
import { TABLE_CONSTANTS } from "../types";
import { parseValue } from "../utils/parseCSV";

const MAX_ROWS = TABLE_CONSTANTS.MAX_ROWS;
const MAX_COLS = TABLE_CONSTANTS.MAX_COLS;

// ----------------------------------------------------------------
// Action types
// ----------------------------------------------------------------

export type DataAction =
  | { type: "SET_DATA"; payload: Dataset }
  | { type: "SET_CELL"; row: number; col: number; value: string | number }
  | { type: "SET_HEADER"; col: number; oldName: string; newName: string }
  | { type: "PASTE"; startRow: number; startCol: number; values: string[][] }
  | {
      type: "CLEAR_RANGE";
      minRow: number;
      maxRow: number;
      minCol: number;
      maxCol: number;
    }
  | {
      type: "FILL";
      startRow: number;
      endRow: number;
      startCol: number;
      endCol: number;
      fillRow: number;
      fillCol: number;
    };

// ----------------------------------------------------------------
// Reducer
// ----------------------------------------------------------------

function dataReducer(state: Dataset, action: DataAction): Dataset {
  switch (action.type) {
    case "SET_DATA":
      return action.payload;

    case "SET_CELL": {
      const { row, col, value } = action;
      if (row >= state.rows.length || col >= state.columns.length) return state;
      const colName = state.columns[col];
      const newRows = state.rows.map((r, i) =>
        i === row ? { ...r, [colName]: value } : r,
      );
      return { ...state, rows: newRows };
    }

    case "SET_HEADER": {
      const { col, oldName, newName } = action;
      if (col >= state.columns.length) return state;
      const newColumns = [...state.columns];
      newColumns[col] = newName;
      const newRows = state.rows.map((r) => {
        const updated = { ...r };
        if (oldName in updated) {
          updated[newName] = updated[oldName];
          if (oldName !== newName) delete updated[oldName];
        }
        return updated;
      });
      return { columns: newColumns, rows: newRows };
    }

    case "PASTE": {
      const { startRow, startCol, values } = action;
      let cols = [...state.columns];
      let rows = state.rows.map((r): DataRow => ({ ...r }));

      const neededCols = startCol + (values[0]?.length ?? 0);
      const neededRows = startRow + values.length;

      // Expand columns if needed
      while (cols.length < neededCols && cols.length < MAX_COLS) {
        const label = `${cols.length + 1}`;
        cols.push(label);
        rows.forEach((r) => (r[label] = ""));
      }
      // Expand rows if needed
      while (rows.length < neededRows && rows.length < MAX_ROWS) {
        const newRow: DataRow = {};
        cols.forEach((c) => (newRow[c] = ""));
        rows.push(newRow);
      }
      // Paste cell by cell
      for (let r = 0; r < values.length; r++) {
        const targetRow = startRow + r;
        if (targetRow >= rows.length) break;
        for (let c = 0; c < values[r].length; c++) {
          const targetCol = startCol + c;
          if (targetCol >= cols.length) break;
          rows[targetRow][cols[targetCol]] = parseValue(values[r][c]);
        }
      }
      return { columns: cols, rows };
    }

    case "CLEAR_RANGE": {
      const { minRow, maxRow, minCol, maxCol } = action;
      const newRows = state.rows.map((r, ri) => {
        if (ri < minRow || ri > maxRow) return r;
        const updated = { ...r };
        for (let c = minCol; c <= maxCol; c++) {
          if (c < state.columns.length) updated[state.columns[c]] = "";
        }
        return updated;
      });
      return { ...state, rows: newRows };
    }

    case "FILL": {
      const { startRow, endRow, startCol, endCol, fillRow, fillCol } = action;
      const newRows = state.rows.map((r, ri) => {
        const updated = { ...r };
        // Fill down: copy from endRow into rows endRow+1..fillRow
        if (fillRow > endRow && ri > endRow && ri <= fillRow) {
          for (let c = startCol; c <= endCol; c++) {
            if (c < state.columns.length) {
              updated[state.columns[c]] =
                state.rows[endRow]?.[state.columns[c]] ?? "";
            }
          }
        }
        // Fill right: copy from endCol into cols endCol+1..fillCol
        if (fillCol > endCol && ri >= startRow && ri <= endRow) {
          for (let c = endCol + 1; c <= fillCol; c++) {
            if (c < state.columns.length) {
              updated[state.columns[c]] = r[state.columns[endCol]] ?? "";
            }
          }
        }
        return updated;
      });
      return { ...state, rows: newRows };
    }

    default:
      return state;
  }
}

// ----------------------------------------------------------------
// Hook
// ----------------------------------------------------------------

export function useDataReducer(initialData: Dataset) {
  return useReducer(dataReducer, initialData);
}
