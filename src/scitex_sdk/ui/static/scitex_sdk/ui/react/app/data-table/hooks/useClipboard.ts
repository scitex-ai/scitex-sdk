/**
 * Clipboard copy/paste (Ctrl+C / Ctrl+V).
 * Ported from scitex-cloud TableClipboard.ts.
 */

import { useCallback } from "react";
import type { Dataset } from "../types";
import type { SelectionRange } from "../utils/selectionHelpers";
import { normalizeRange } from "../utils/selectionHelpers";
import type { DataAction } from "./useDataReducer";
import type { CellPosition } from "../types";

// ----------------------------------------------------------------
// Types
// ----------------------------------------------------------------

export interface UseClipboardReturn {
  handleClipboardKeyDown: (e: React.KeyboardEvent) => void;
}

// ----------------------------------------------------------------
// Hook
// ----------------------------------------------------------------

export function useClipboard(
  data: Dataset,
  dispatchData: (action: DataAction) => void,
  selection: SelectionRange | null,
  currentCell: CellPosition | null,
  readOnly: boolean,
  onStatusUpdate?: (msg: string) => void,
): UseClipboardReturn {
  const handleClipboardKeyDown = useCallback(
    async (e: React.KeyboardEvent) => {
      if (!(e.ctrlKey || e.metaKey)) return;

      // ---- Copy ----
      if (e.key === "c" || e.key === "C") {
        e.preventDefault();
        if (!selection) return;

        const { minRow, maxRow, minCol, maxCol } = normalizeRange(selection);
        const lines: string[] = [];

        for (let r = minRow; r <= maxRow; r++) {
          const vals: string[] = [];
          for (let c = minCol; c <= maxCol; c++) {
            const colName = data.columns[c];
            const v = data.rows[r]?.[colName];
            vals.push(v !== undefined && v !== null ? String(v) : "");
          }
          lines.push(vals.join("\t"));
        }

        try {
          await navigator.clipboard.writeText(lines.join("\n"));
          const rowCount = maxRow - minRow + 1;
          const colCount = maxCol - minCol + 1;
          onStatusUpdate?.(
            `Copied ${rowCount} row${rowCount !== 1 ? "s" : ""} × ${colCount} col${colCount !== 1 ? "s" : ""}`,
          );
        } catch {
          onStatusUpdate?.("Copy failed — clipboard access denied");
        }
        return;
      }

      // ---- Paste ----
      if (e.key === "v" || e.key === "V") {
        e.preventDefault();
        if (!currentCell || readOnly) return;

        try {
          const text = await navigator.clipboard.readText();
          if (!text) return;

          const lines = text.trim().split("\n");
          const rows = lines.map((line) =>
            line.includes("\t") ? line.split("\t") : line.split(","),
          );

          dispatchData({
            type: "PASTE",
            startRow: currentCell.row,
            startCol: currentCell.col,
            values: rows,
          });

          onStatusUpdate?.(
            `Pasted ${rows.length} rows × ${rows[0]?.length ?? 0} cols`,
          );
        } catch {
          onStatusUpdate?.("Paste failed — clipboard access denied");
        }
        return;
      }
    },
    [data, dispatchData, selection, currentCell, readOnly, onStatusUpdate],
  );

  return { handleClipboardKeyDown };
}
