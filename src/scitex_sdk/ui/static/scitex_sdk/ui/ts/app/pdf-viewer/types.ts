/**
 * @scitex/ui/pdf-viewer — L1 hook-API types (ADR 0001).
 *
 * Framework-neutral. All geometry is in PDF-space (zoom-invariant) so marks
 * survive zoom/resize without recomputation. Consumers own the mark/comment
 * feed; L1 is a controlled overlay.
 */

export type PdfTool = "highlight" | "rect" | "freehand" | "circle" | "arrow";

/** A point in PDF-space (page-local, unscaled), optional stylus pressure. */
export interface PenPoint {
  x: number;
  y: number;
  pressure?: number;
}

/** Zoom-invariant coordinate resolved from a client (screen) point. */
export interface PdfCoords {
  page: number;
  pdfX: number;
  pdfY: number;
}

/** Axis-aligned region in PDF-space. */
export interface PdfRect {
  page: number;
  x: number;
  y: number;
  w: number;
  h: number;
}

/** A pen/overlay stroke emitted by L1 as the user draws. */
export interface PenInput {
  page: number;
  tool: PdfTool;
  path: PenPoint[];
}

/**
 * A controlled overlay mark. Geometry is `rect` (rect/highlight/circle/arrow
 * bounding) and/or `path` (freehand). `color` may be a literal or a
 * `var(--stx-verdict-*)` reference resolved from the palette.
 */
export interface Mark {
  id: string;
  page: number;
  tool: PdfTool;
  rect?: Omit<PdfRect, "page">;
  path?: PenPoint[];
  color?: string;
  label?: string;
  meta?: Record<string, unknown>;
}

/** Verdict palette → CSS custom properties (e.g. { "accept": "#2e7d32" }). */
export type PdfPalette = Record<string, string>;

/** Viewport reported to `onPageRender`. */
export interface PdfViewport {
  width: number;
  height: number;
  scale: number;
}

/**
 * L1 → consumer callbacks. All optional; L1 stays inert until wired.
 * The consumer owns the feed and echoes marks back via `setMarks`.
 */
export interface PdfViewerHooks {
  onPageRender?: (page: number, viewport: PdfViewport) => void;
  onRegionSelect?: (region: PdfRect) => void;
  onPenInput?: (input: PenInput) => void;
  onMarksChange?: (marks: Mark[]) => void;
}

export type PdfSource = string | URL | ArrayBuffer;

export interface PdfViewerOptions {
  container: HTMLElement;
  src?: PdfSource;
  tool?: PdfTool;
  palette?: PdfPalette;
  hooks?: PdfViewerHooks;
  /** Render scale (CSS px per PDF unit). Default 1.5. */
  scale?: number;
  /**
   * Override the PDF.js worker URL. Defaults to resolving
   * `pdfjs-dist/build/pdf.worker.min.mjs` relative to this module — which
   * modern bundlers (Vite) handle. Set explicitly for other setups.
   */
  workerSrc?: string;
}

/**
 * The stable L1 interface consumers wire against. The React adapter
 * (`@scitex/ui/pdf-viewer/react`) is a thin wrapper over this.
 */
export interface PdfViewerApi {
  /** Load (or replace) the PDF source and render pages. */
  load(src: PdfSource): Promise<void>;
  /** Map a client (screen) point to zoom-invariant PDF-space; null if off-page. */
  getCoords(clientX: number, clientY: number): PdfCoords | null;
  /** Set the active pen/overlay tool. */
  setTool(tool: PdfTool): void;
  /**
   * Toggle pen editing. `false` (Read/Review mode) disables pen input and
   * lets scroll / text-selection through to the page; marks keep rendering.
   * `true` (Markup mode) re-enables the pen overlay. Default is enabled.
   */
  setInteractive(enabled: boolean): void;
  /** Re-render all pages at `scale` (CSS px per PDF unit); preserves scroll + marks. */
  setScale(scale: number): Promise<void>;
  /** Current render scale. */
  getScale(): number;
  /** Set the scale so the page width fills the container, then re-render. */
  fitWidth(): Promise<void>;
  /** Scroll the container to the given 1-based page. No-op if out of range. */
  scrollToPage(page: number): void;
  /** Replace the controlled overlay marks (consumer owns the feed). */
  setMarks(marks: Mark[]): void;
  /** Current overlay marks (copy). */
  getMarks(): Mark[];
  /** Apply/replace the verdict palette as CSS custom properties. */
  setPalette(palette: PdfPalette): void;
  /** Tear down listeners and detach from the container. */
  destroy(): void;
}
