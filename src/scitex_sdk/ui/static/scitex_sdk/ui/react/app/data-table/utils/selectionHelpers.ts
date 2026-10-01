/**
 * Selection helper utilities.
 * Ported from scitex-cloud TableSelection.ts logic.
 */

import type { CellPosition } from "../types";

// ----------------------------------------------------------------
// Types
// ----------------------------------------------------------------

export interface SelectionRange {
  start: CellPosition;
  end: CellPosition;
}

export interface NormalizedBounds {
  minRow: number;
  maxRow: number;
  minCol: number;
  maxCol: number;
}

// ----------------------------------------------------------------
// Helpers
// ----------------------------------------------------------------

export function normalizeRange(r: SelectionRange): NormalizedBounds {
  return {
    minRow: Math.min(r.start.row, r.end.row),
    maxRow: Math.max(r.start.row, r.end.row),
    minCol: Math.min(r.start.col, r.end.col),
    maxCol: Math.max(r.start.col, r.end.col),
  };
}

export function isCellInRange(
  row: number,
  col: number,
  range: SelectionRange | null,
): boolean {
  if (!range) return false;
  const { minRow, maxRow, minCol, maxCol } = normalizeRange(range);
  return row >= minRow && row <= maxRow && col >= minCol && col <= maxCol;
}

export function isColHighlighted(
  col: number,
  selection: SelectionRange | null,
  selectedColumns: Set<number>,
): boolean {
  if (selectedColumns.has(col)) return true;
  if (!selection) return false;
  const { minCol, maxCol } = normalizeRange(selection);
  return col >= minCol && col <= maxCol;
}

export function isRowHighlighted(
  row: number,
  selection: SelectionRange | null,
  selectedRows: Set<number>,
): boolean {
  if (selectedRows.has(row)) return true;
  if (!selection) return false;
  const { minRow, maxRow } = normalizeRange(selection);
  return row >= minRow && row <= maxRow;
}

/** Returns true when the cell is the bottom-right corner of the selection */
export function isSelectionCorner(
  row: number,
  col: number,
  selection: SelectionRange | null,
): boolean {
  if (!selection) return false;
  const { maxRow, maxCol } = normalizeRange(selection);
  return row === maxRow && col === maxCol;
}
