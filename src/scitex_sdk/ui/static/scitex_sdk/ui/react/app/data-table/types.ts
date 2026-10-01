/**
 * Type definitions for shared DataTable component.
 * Ported from scitex-cloud static/shared/ts/components/data-table/types.ts
 */

import type { BaseProps } from "../../_base/types";

export interface Dataset {
  columns: string[];
  rows: DataRow[];
}

export interface DataRow {
  [key: string]: string | number;
}

export interface CellPosition {
  row: number;
  col: number;
}

export interface SelectionState {
  start: CellPosition | null;
  end: CellPosition | null;
  isSelecting: boolean;
  selectedColumns: Set<number>;
  selectedRows: Set<number>;
}

export const TABLE_CONSTANTS = {
  ROW_HEIGHT: 33,
  COL_WIDTH: 80,
  MAX_ROWS: 32767,
  MAX_COLS: 32767,
  DEFAULT_ROWS: 1000,
  DEFAULT_COLS: 32,
} as const;

export interface DataTableProps extends BaseProps {
  /** Data to display */
  data?: Dataset;
  /** CSV string to parse and display */
  csvContent?: string;
  /** Whether the table is read-only */
  readOnly?: boolean;
  /** Called when data changes */
  onDataChange?: (data: Dataset) => void;
  /** Called when cell is selected */
  onCellSelect?: (position: CellPosition) => void;
  /** Called on status update */
  onStatusUpdate?: (message: string) => void;
  /** Show row numbers */
  showRowNumbers?: boolean;
  /** Enable column sorting */
  sortable?: boolean;
  /** Enable column resizing */
  resizable?: boolean;
}
