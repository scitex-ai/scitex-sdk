/**
 * CsvViewer - Renders CSV/TSV files as a table.
 *
 * Ported from scitex-cloud's workspace-viewer/viewers/CsvViewer.ts.
 * Simplified: uses a basic HTML table (no DataTableManager dependency).
 * Uses ViewerAdapter for file content fetching.
 */

import type { Viewer, ViewerAdapter } from "./types";

export class CsvViewer implements Viewer {
  private abortController: AbortController | null = null;

  async render(
    container: HTMLElement,
    filePath: string,
    adapter: ViewerAdapter,
  ): Promise<void> {
    const fileName = filePath.split("/").pop() || filePath;

    container.innerHTML = "";
    this.abortController = new AbortController();

    const content = document.createElement("div");
    content.style.cssText = "height:100%; overflow:auto; padding:0;";
    content.innerHTML =
      '<div style="color:#888; padding:10px;">Loading...</div>';
    container.appendChild(content);

    let rawText = "";

    try {
      const result = await adapter.readFile(filePath);
      rawText = result.content;
    } catch (err: any) {
      if (err.name === "AbortError") return;
      content.innerHTML = `<div style="color:#e55; padding:10px;">Failed to load: ${fileName}</div>`;
      return;
    }

    content.innerHTML = "";
    content.style.padding = "0";
    this.renderTable(content, rawText, filePath);
  }

  private renderTable(
    container: HTMLElement,
    rawText: string,
    filePath: string,
  ): void {
    const rows = rawText.split(/\r?\n/).filter((l) => l.trim());
    if (rows.length === 0) {
      container.innerHTML =
        '<div style="color:#888; padding:10px;">Empty file</div>';
      return;
    }

    const isTsv = filePath.endsWith(".tsv");
    const separator = isTsv ? "\t" : ",";

    const table = document.createElement("table");
    table.className = "csv-table";
    table.style.cssText =
      "border-collapse:collapse; font-size:0.85em; white-space:nowrap; width:100%;";

    for (let i = 0; i < rows.length; i++) {
      const tr = document.createElement("tr");
      const cells = this.parseRow(rows[i], separator);
      for (const cell of cells) {
        const el = document.createElement(i === 0 ? "th" : "td");
        el.textContent = cell;
        el.style.cssText =
          "padding:4px 8px; border:1px solid var(--workspace-border-muted, #333);" +
          (i === 0
            ? "background:var(--workspace-bg-secondary, #2a2a2a); font-weight:600;"
            : "");
        tr.appendChild(el);
      }
      table.appendChild(tr);
    }
    container.appendChild(table);
  }

  private parseRow(row: string, separator: string): string[] {
    if (separator === "\t") return row.split("\t");
    // Basic CSV parsing (handles quoted fields)
    const cells: string[] = [];
    let current = "";
    let inQuotes = false;
    for (let i = 0; i < row.length; i++) {
      const ch = row[i];
      if (inQuotes) {
        if (ch === '"' && row[i + 1] === '"') {
          current += '"';
          i++;
        } else if (ch === '"') {
          inQuotes = false;
        } else {
          current += ch;
        }
      } else {
        if (ch === '"') {
          inQuotes = true;
        } else if (ch === separator) {
          cells.push(current);
          current = "";
        } else {
          current += ch;
        }
      }
    }
    cells.push(current);
    return cells;
  }

  destroy(): void {
    this.abortController?.abort();
    this.abortController = null;
  }
}
