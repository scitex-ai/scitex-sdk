/**
 * CSV parsing and export utilities.
 * Ported from scitex-cloud _TableData.ts parseCSVContent / parseCSV / exportToCSV.
 */

import type { Dataset, DataRow } from "../types";

// ----------------------------------------------------------------
// Internal: low-level CSV tokenizer (handles quoted fields)
// ----------------------------------------------------------------

export function parseCSVContent(
  content: string,
  delimiter: string,
): string[][] {
  const rows: string[][] = [];
  let currentRow: string[] = [];
  let currentCell = "";
  let inQuotes = false;

  for (let i = 0; i < content.length; i++) {
    const char = content[i];
    const nextChar = content[i + 1];

    if (inQuotes) {
      if (char === '"' && nextChar === '"') {
        currentCell += '"';
        i++;
      } else if (char === '"') {
        inQuotes = false;
      } else {
        currentCell += char;
      }
    } else {
      if (char === '"') {
        inQuotes = true;
      } else if (char === delimiter) {
        currentRow.push(currentCell);
        currentCell = "";
      } else if (char === "\n" || (char === "\r" && nextChar === "\n")) {
        currentRow.push(currentCell);
        if (currentRow.some((c) => c.trim())) rows.push(currentRow);
        currentRow = [];
        currentCell = "";
        if (char === "\r") i++;
      } else if (char !== "\r") {
        currentCell += char;
      }
    }
  }

  // Last row / cell
  if (currentCell || currentRow.length > 0) {
    currentRow.push(currentCell);
    if (currentRow.some((c) => c.trim())) rows.push(currentRow);
  }

  return rows;
}

// ----------------------------------------------------------------
// Public: parse CSV/TSV string into Dataset
// ----------------------------------------------------------------

export function parseCSV(content: string, fileName?: string): Dataset {
  const delimiter = fileName?.toLowerCase().endsWith(".tsv") ? "\t" : ",";
  const rawRows = parseCSVContent(content, delimiter);
  if (rawRows.length === 0) return { columns: [], rows: [] };

  const headers = rawRows[0].map((h, i) => h.trim() || `${i + 1}`);
  const dataRows: DataRow[] = [];

  for (let i = 1; i < rawRows.length; i++) {
    const row: DataRow = {};
    headers.forEach((h, j) => {
      const val = (rawRows[i][j] ?? "").trim();
      const num = parseFloat(val);
      row[h] = val !== "" && !isNaN(num) ? num : val;
    });
    dataRows.push(row);
  }

  return { columns: headers, rows: dataRows };
}

// ----------------------------------------------------------------
// Public: export Dataset to CSV string
// ----------------------------------------------------------------

export function exportToCSV(dataset: Dataset): string {
  const lines: string[] = [];
  lines.push(dataset.columns.join(","));
  dataset.rows.forEach((row) => {
    const vals = dataset.columns.map((col) => {
      const v = row[col];
      if (v === undefined || v === null) return "";
      const s = String(v);
      if (s.includes(",") || s.includes("\n") || s.includes('"')) {
        return `"${s.replace(/"/g, '""')}"`;
      }
      return s;
    });
    lines.push(vals.join(","));
  });
  return lines.join("\n");
}

// ----------------------------------------------------------------
// Public: make empty Excel-like grid
// ----------------------------------------------------------------

export function makeEmptyGrid(rows = 100, cols = 32): Dataset {
  const columns = Array.from({ length: cols }, (_, i) => `${i + 1}`);
  const dataRows: DataRow[] = Array.from({ length: rows }, () => {
    const row: DataRow = {};
    columns.forEach((c) => (row[c] = ""));
    return row;
  });
  return { columns, rows: dataRows };
}

// ----------------------------------------------------------------
// Helper: coerce string to Dataset value
// ----------------------------------------------------------------

export function parseValue(raw: string): string | number {
  const trimmed = raw.trim();
  const num = parseFloat(trimmed);
  return trimmed !== "" && !isNaN(num) ? num : trimmed;
}
