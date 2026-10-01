/**
 * DataTable — full-featured spreadsheet component.
 *
 * Orchestrates all sub-hooks; rendering only lives here.
 * Ported feature-for-feature from scitex-cloud DataTableManager.
 *
 * Features:
 * - Multi-cell range selection (click + drag)
 * - Cell editing (double-click, F2, Enter/Escape)
 * - Clipboard copy/paste (Ctrl+C / Ctrl+V, Excel TSV format)
 * - Column resize (drag header border)
 * - Right-click context menu
 * - Row/column header highlighting on selection
 * - Fill handle (drag bottom-right corner)
 * - Keyboard navigation (Arrow, Tab, Enter, Delete)
 * - Virtual scrolling (>100 rows)
 * - Empty Excel-like grid when no data
 */

import React, { useMemo, useEffect, useRef } from "react";
import type { DataTableProps, Dataset } from "./types";
import { parseCSV, exportToCSV, makeEmptyGrid } from "./utils/parseCSV";
import {
  isCellInRange,
  isColHighlighted,
  isRowHighlighted,
  isSelectionCorner,
} from "./utils/selectionHelpers";
import { useDataReducer } from "./hooks/useDataReducer";
import { useSelection } from "./hooks/useSelection";
import { useEditing } from "./hooks/useEditing";
import { useClipboard } from "./hooks/useClipboard";
import { useVirtualScroll } from "./hooks/useVirtualScroll";
import { useFillHandle } from "./hooks/useFillHandle";
import { useColumnResize } from "./hooks/useColumnResize";

const CLS = "stx-app-data-table";

// ----------------------------------------------------------------
// Sort helpers
// ----------------------------------------------------------------

function sortDataset(
  data: Dataset,
  colIdx: number,
  direction: "asc" | "desc",
): Dataset {
  const col = data.columns[colIdx];
  if (!col) return data;
  const sorted = [...data.rows].sort((a, b) => {
    const va = a[col];
    const vb = b[col];
    if (typeof va === "number" && typeof vb === "number") {
      return direction === "asc" ? va - vb : vb - va;
    }
    return direction === "asc"
      ? String(va ?? "").localeCompare(String(vb ?? ""))
      : String(vb ?? "").localeCompare(String(va ?? ""));
  });
  return { ...data, rows: sorted };
}

// ----------------------------------------------------------------
// Component
// ----------------------------------------------------------------

export const DataTable: React.FC<DataTableProps> = ({
  data: propData,
  csvContent,
  readOnly = false,
  onDataChange,
  onCellSelect,
  onStatusUpdate,
  showRowNumbers = true,
  sortable = true,
  resizable = true,
  className,
  style,
}) => {
  // ---- Sort state ----
  const [sortCol, setSortCol] = React.useState<number | null>(null);
  const [sortDir, setSortDir] = React.useState<"asc" | "desc">("asc");
  const [contextMenuPos, setContextMenuPos] = React.useState<{
    x: number;
    y: number;
  } | null>(null);

  // ---- Base data ----
  const initialData = useMemo<Dataset>(() => {
    if (propData) return propData;
    if (csvContent) return parseCSV(csvContent);
    return makeEmptyGrid();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const [data, dispatchData] = useDataReducer(initialData);

  // Sync external prop changes
  useEffect(() => {
    if (propData) dispatchData({ type: "SET_DATA", payload: propData });
  }, [propData]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (csvContent) {
      dispatchData({ type: "SET_DATA", payload: parseCSV(csvContent) });
    }
  }, [csvContent]); // eslint-disable-line react-hooks/exhaustive-deps

  // Notify parent on changes
  useEffect(() => {
    onDataChange?.(data);
  }, [data]); // eslint-disable-line react-hooks/exhaustive-deps

  // ---- Sorted view ----
  const sortedData = useMemo<Dataset>(() => {
    if (sortCol === null) return data;
    return sortDataset(data, sortCol, sortDir);
  }, [data, sortCol, sortDir]);

  // ---- Sub-hooks ----
  const {
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
    moveCurrentCell,
  } = useSelection(onCellSelect, onStatusUpdate, sortedData.columns);

  const {
    editing,
    startEditing,
    commitEdit,
    cancelEdit,
    setEditValue,
    handleCellKeyDown,
  } = useEditing(sortedData, dispatchData);

  const { handleClipboardKeyDown } = useClipboard(
    sortedData,
    dispatchData,
    selection,
    currentCell,
    readOnly,
    onStatusUpdate,
  );

  const totalRows = sortedData.rows.length;
  const useVS = totalRows > 100;
  const {
    renderStart,
    renderEnd,
    topSpacerHeight,
    bottomSpacerHeight,
    scrollContainerRef,
  } = useVirtualScroll(totalRows, useVS);

  const { fillHandle, handleFillHandleMouseDown, isFillPreview } =
    useFillHandle(selection, dispatchData, onStatusUpdate);

  const { getColWidth, handleResizeStart } = useColumnResize();

  // Edit input ref
  const editInputRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (editing && editInputRef.current) {
      editInputRef.current.focus();
      editInputRef.current.select();
    }
  }, [editing]);

  // Hide context menu on outside click
  useEffect(() => {
    if (!contextMenuPos) return;
    const hide = () => setContextMenuPos(null);
    document.addEventListener("click", hide);
    return () => document.removeEventListener("click", hide);
  }, [contextMenuPos]);

  // ---- Key handler ----
  const handleTableKeyDown = (e: React.KeyboardEvent) => {
    handleClipboardKeyDown(e);
    if (currentCell) {
      handleCellKeyDown(
        e,
        currentCell.row,
        currentCell.col,
        sortedData,
        selection,
        moveCurrentCell,
        dispatchData,
        readOnly,
      );
    }
  };

  // ---- Cell CSS ----
  const getCellClass = (row: number, col: number): string => {
    const parts = [`${CLS}__cell`];
    if (isCellInRange(row, col, selection))
      parts.push(`${CLS}__cell--selected`);
    if (currentCell?.row === row && currentCell?.col === col)
      parts.push(`${CLS}__cell--current`);
    if (editing?.row === row && editing?.col === col && !editing.isHeader)
      parts.push(`${CLS}__cell--editing`);
    if (isFillPreview(row, col)) parts.push(`${CLS}__cell--fill-preview`);
    return parts.join(" ");
  };

  // ---- Render ----
  return (
    <div
      className={`${CLS} ${className ?? ""}`}
      style={style}
      tabIndex={0}
      onKeyDown={handleTableKeyDown}
      onContextMenu={(e) => {
        e.preventDefault();
        setContextMenuPos({ x: e.clientX, y: e.clientY });
      }}
    >
      <div ref={scrollContainerRef} className={`${CLS}__scroll`}>
        {useVS && topSpacerHeight > 0 && (
          <div style={{ height: topSpacerHeight }} />
        )}

        <table className={`${CLS}__table`}>
          <thead>
            <tr>
              {showRowNumbers && (
                <th className={`${CLS}__row-num ${CLS}__row-num--header`}>#</th>
              )}
              {sortedData.columns.map((col, ci) => {
                const highlighted = isColHighlighted(
                  ci,
                  selection,
                  selectedColumns,
                );
                const isEditingHeader = editing?.isHeader && editing.col === ci;
                return (
                  <th
                    key={ci}
                    data-col={ci}
                    className={[
                      `${CLS}__header-cell`,
                      sortCol === ci ? `${CLS}__header-cell--sorted` : "",
                      highlighted ? `${CLS}__header-cell--highlighted` : "",
                    ]
                      .join(" ")
                      .trim()}
                    style={{ width: getColWidth(ci), minWidth: 30 }}
                    onClick={() =>
                      !editing &&
                      sortable &&
                      (sortCol === ci
                        ? setSortDir((d) => (d === "asc" ? "desc" : "asc"))
                        : (setSortCol(ci), setSortDir("asc")))
                    }
                    onMouseDown={(e) => handleColumnHeaderMouseDown(e, ci)}
                    onMouseOver={(e) => handleColumnHeaderMouseOver(e, ci)}
                    onDoubleClick={() =>
                      !readOnly && startEditing(-1, ci, col, true)
                    }
                  >
                    {isEditingHeader ? (
                      <input
                        ref={editInputRef}
                        className={`${CLS}__edit-input`}
                        value={editing.value}
                        onChange={(e) => setEditValue(e.target.value)}
                        onBlur={commitEdit}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") {
                            e.preventDefault();
                            commitEdit();
                          } else if (e.key === "Escape") {
                            e.preventDefault();
                            cancelEdit();
                          }
                          e.stopPropagation();
                        }}
                        style={{ width: "100%" }}
                      />
                    ) : (
                      <>
                        <span>{col}</span>
                        {sortable && sortCol === ci && (
                          <i
                            className={`fas fa-caret-${sortDir === "asc" ? "up" : "down"}`}
                          />
                        )}
                      </>
                    )}
                    {resizable && (
                      <div
                        className={`${CLS}__resize-handle`}
                        onMouseDown={(e) => handleResizeStart(ci, e)}
                      />
                    )}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {sortedData.rows
              .slice(renderStart, renderEnd)
              .map((row, relIdx) => {
                const ri = renderStart + relIdx;
                return (
                  <tr
                    key={ri}
                    className={`${CLS}__row${ri % 2 === 0 ? ` ${CLS}__row--even` : ` ${CLS}__row--odd`}`}
                  >
                    {showRowNumbers && (
                      <td
                        className={`${CLS}__row-num${isRowHighlighted(ri, selection, selectedRows) ? ` ${CLS}__row-num--highlighted` : ""}`}
                        onMouseDown={(e) => handleRowNumberMouseDown(e, ri)}
                        onMouseOver={(e) => handleRowNumberMouseOver(e, ri)}
                      >
                        {ri + 1}
                      </td>
                    )}
                    {sortedData.columns.map((col, ci) => {
                      const cellEditing =
                        editing?.row === ri &&
                        editing?.col === ci &&
                        !editing.isHeader;
                      const cellValue = row[col] ?? "";
                      const isLast = isSelectionCorner(ri, ci, selection);
                      return (
                        <td
                          key={ci}
                          className={getCellClass(ri, ci)}
                          data-row={ri}
                          data-col={ci}
                          tabIndex={
                            currentCell?.row === ri && currentCell?.col === ci
                              ? 0
                              : -1
                          }
                          style={{ width: getColWidth(ci), minWidth: 30 }}
                          onMouseDown={(e) => {
                            if (
                              !editing ||
                              editing.row !== ri ||
                              editing.col !== ci
                            )
                              commitEdit();
                            handleCellMouseDown(e, ri, ci);
                          }}
                          onMouseOver={(e) => handleCellMouseOver(e, ri, ci)}
                          onDoubleClick={() =>
                            !readOnly && startEditing(ri, ci, String(cellValue))
                          }
                          title={String(cellValue)}
                        >
                          {cellEditing ? (
                            <input
                              ref={editInputRef}
                              className={`${CLS}__edit-input`}
                              value={editing.value}
                              onChange={(e) => setEditValue(e.target.value)}
                              onBlur={commitEdit}
                              onKeyDown={(e) => {
                                if (e.key === "Tab" || e.key === "Enter") {
                                  // Don't stop propagation — let container's
                                  // handleCellKeyDown handle commit + navigation
                                } else if (e.key === "Escape") {
                                  e.preventDefault();
                                  cancelEdit();
                                  e.stopPropagation();
                                } else {
                                  e.stopPropagation();
                                }
                              }}
                              style={{ width: "100%" }}
                            />
                          ) : (
                            <span className={`${CLS}__cell-text`}>
                              {cellValue}
                            </span>
                          )}
                          {!readOnly && isLast && !fillHandle && (
                            <div
                              className={`${CLS}__fill-handle`}
                              onMouseDown={handleFillHandleMouseDown}
                            />
                          )}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
          </tbody>
        </table>

        {useVS && bottomSpacerHeight > 0 && (
          <div style={{ height: bottomSpacerHeight }} />
        )}
      </div>

      {/* Context menu */}
      {contextMenuPos && (
        <div
          className={`${CLS}__context-menu`}
          style={{
            position: "fixed",
            left: contextMenuPos.x,
            top: contextMenuPos.y,
            zIndex: 10000,
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <div className={`${CLS}__context-menu-section`}>
            <div
              className={`${CLS}__context-menu-item`}
              onClick={() => {
                handleImportFile(dispatchData, onStatusUpdate);
                setContextMenuPos(null);
              }}
            >
              <i className="fas fa-file-import" />{" "}
              <span>Import CSV / TSV…</span>
            </div>
            {!readOnly && selection && (
              <div
                className={`${CLS}__context-menu-item`}
                onClick={() => {
                  const sel = selection;
                  if (sel) {
                    const b = {
                      minRow: Math.min(sel.start.row, sel.end.row),
                      maxRow: Math.max(sel.start.row, sel.end.row),
                      minCol: Math.min(sel.start.col, sel.end.col),
                      maxCol: Math.max(sel.start.col, sel.end.col),
                    };
                    dispatchData({ type: "CLEAR_RANGE", ...b });
                  }
                  setContextMenuPos(null);
                }}
              >
                <i className="fas fa-eraser" /> <span>Clear selection</span>
              </div>
            )}
            <div
              className={`${CLS}__context-menu-item`}
              onClick={() => {
                const csv = exportToCSV(data);
                const b = new Blob([csv], { type: "text/csv" });
                const url = URL.createObjectURL(b);
                const a = document.createElement("a");
                a.href = url;
                a.download = "data.csv";
                a.click();
                URL.revokeObjectURL(url);
                setContextMenuPos(null);
              }}
            >
              <i className="fas fa-file-export" /> <span>Export as CSV</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// ---- Standalone helper (not a hook) ----
function handleImportFile(
  dispatchData: (a: import("./hooks/useDataReducer").DataAction) => void,
  onStatusUpdate?: (msg: string) => void,
) {
  const input = document.createElement("input");
  input.type = "file";
  input.accept = ".csv,.tsv";
  input.onchange = (e) => {
    const file = (e.target as HTMLInputElement).files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      const content = ev.target?.result as string;
      if (content) {
        const parsed = parseCSV(content, file.name);
        dispatchData({ type: "SET_DATA", payload: parsed });
        onStatusUpdate?.(
          `Loaded ${file.name} — ${parsed.rows.length} rows × ${parsed.columns.length} cols`,
        );
      }
    };
    reader.readAsText(file);
  };
  input.click();
}
