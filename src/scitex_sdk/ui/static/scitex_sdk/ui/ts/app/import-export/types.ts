/**
 * Type definitions for the ImportExport component.
 *
 * The ImportExport is the standard import/export pattern (compass L623):
 * a trigger opens a panel of FORMAT OPTIONS (BibTeX, RIS, CSL JSON, Zotero,
 * Markdown, PDF, ...); picking one shows a confirm bar; confirming emits
 * the event that the app answers with the actual transfer.
 *
 * The component owns the pattern — the markup, the BEM vocabulary, the
 * confirm/cancel flow, and the event contract. It does NOT own the data
 * (which formats exist is the app's) or the transfer (reading a file,
 * writing a citation file) — both come from the consuming app.
 */

import type { BaseComponentConfig } from "../../_base/types";

export interface FormatOption {
  /** Stable format identifier (passed back via the confirm event),
   *  e.g. "bibtex", "ris", "csl-json", "zotero", "markdown", "pdf". */
  id: string;
  /** Display label (what the user sees in the list), e.g. "BibTeX". */
  label: string;
  /** Optional secondary line (extension hint, "for EndNote", ...). */
  detail?: string;
}

/** Detail of the `stx-import-export:confirm` event. */
export interface ImportExportDetail {
  direction: "import" | "export";
  formatId: string;
  formatLabel: string;
}

export interface ImportExportConfig extends BaseComponentConfig {
  /** Which way the flow goes — sets the trigger label and the event
   *  detail. The pattern is identical either way. */
  direction: "import" | "export";
  /** The formats this flow offers, in display order. */
  formats: FormatOption[];
  /** Trigger label. Defaults to "Export" / "Import" per direction. */
  title?: string;
  /** Confirm-bar text. Defaults to "Export as <label>?" /
   *  "Import <label>?" — i.e. the question the user is confirming. */
  confirmText?: (label: string) => string;
}
