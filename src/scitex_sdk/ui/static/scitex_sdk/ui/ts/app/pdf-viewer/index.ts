/**
 * @scitex/ui/pdf-viewer — L1 neutral PDF viewer (ADR 0001).
 *
 * Framework-neutral vanilla-TS PDF.js renderer + always-on minimal pen UI
 * (Pointer Events → Wacom / iPad / finger), exported as the named subpath
 * `@scitex/ui/pdf-viewer` so it is reachable WITHOUT the app/shell bundle.
 *
 * IMPORTANT — import must stay INERT: no shell import, no DOM work, no
 * side effects at module load. pdfjs-dist is pulled in via a dynamic
 * import inside `load()`, never at module top level, so importing this
 * file from workspace-shell or standalone-app contexts does nothing until
 * `createPdfViewer()` + `load()` run.
 *
 * Controlled overlay: L1 EMITS pen/region events; the consumer owns the
 * feed and echoes committed marks back via `setMarks`. L1 never
 * auto-creates a mark.
 */

import type {
  Mark,
  PdfCoords,
  PdfPalette,
  PdfRect,
  PdfSource,
  PdfTool,
  PdfViewerApi,
  PdfViewerHooks,
  PdfViewerOptions,
  PenPoint,
} from "./types";

export * from "./types";

/** Construct an L1 viewer bound to `options.container`. */
export function createPdfViewer(options: PdfViewerOptions): PdfViewerApi {
  return new PdfViewer(options);
}

// pdfjs is dynamically imported; type its surface loosely at the boundary to
// avoid coupling this file's typecheck to pdfjs-dist's exact type exports.
interface PdfjsViewport {
  width: number;
  height: number;
  convertToViewportPoint(x: number, y: number): number[];
  convertToPdfPoint(x: number, y: number): number[];
}
interface PdfjsPage {
  getViewport(params: { scale: number }): PdfjsViewport;
  render(params: {
    canvasContext: CanvasRenderingContext2D;
    viewport: PdfjsViewport;
  }): { promise: Promise<void> };
}
interface PdfjsDocument {
  numPages: number;
  getPage(n: number): Promise<PdfjsPage>;
}

interface PageView {
  pageNum: number;
  viewport: PdfjsViewport;
  wrap: HTMLElement;
  page: HTMLCanvasElement;
  overlay: HTMLCanvasElement;
}

interface DrawState {
  view: PageView;
  tool: PdfTool;
  points: PenPoint[]; // PDF-space
}

function applyPalette(el: HTMLElement, palette: PdfPalette): void {
  for (const [key, value] of Object.entries(palette)) {
    el.style.setProperty(`--stx-verdict-${key}`, value);
  }
}

/**
 * The width a fit-to-width page may occupy: the container's CONTENT box.
 *
 * ``clientWidth`` INCLUDES the horizontal padding (it excludes borders and the
 * scrollbar only), so dividing by it sizes the page to the PADDED width. The
 * page canvas then overflows the content box by exactly the two paddings and
 * the container scrolls sideways.
 *
 * MEASURED BY scitex-writer at 390x844 (chromium, their PR #396/v2.43.3, the
 * first app to render this primitive on a phone): with
 * ``.pdf-viewer-host { padding: 16px }``, fit-width produced a 382px canvas
 * positioned at x=16 — right edge 398 on a 390px viewport, container
 * scrollWidth 414 > clientWidth 382. They worked around it by deleting the
 * horizontal gutter at phone width. Every adopter would have inherited the
 * same bug, so it is fixed HERE, where the geometry is computed, rather than
 * per consumer.
 *
 * Pure on purpose: the arithmetic is the whole defect, and a pure function is
 * the only form in which it has a test that can fail (`clientWidth` is 0 under
 * jsdom, so a DOM-reading version is untestable in the unit suite).
 */
export function contentBoxWidth(
  clientWidth: number,
  paddingLeft: number,
  paddingRight: number,
): number {
  const content = clientWidth - (paddingLeft + paddingRight);
  return content > 0 ? content : 0;
}

/** The container's content-box width, from the live box model. */
function containerContentWidth(container: HTMLElement): number {
  const style = getComputedStyle(container);
  return contentBoxWidth(
    container.clientWidth,
    parseFloat(style.paddingLeft) || 0,
    parseFloat(style.paddingRight) || 0,
  );
}

class PdfViewer implements PdfViewerApi {
  private readonly container: HTMLElement;
  private readonly hooks: PdfViewerHooks;
  private scale: number;
  private readonly workerSrc?: string;
  private marks: Mark[] = [];
  private tool: PdfTool;
  private views: PageView[] = [];
  private draw: DrawState | null = null;
  private destroyed = false;
  private doc: PdfjsDocument | null = null;
  private interactive = true;

  constructor(options: PdfViewerOptions) {
    this.container = options.container;
    this.hooks = options.hooks ?? {};
    this.tool = options.tool ?? "highlight";
    this.scale = options.scale ?? 1.5;
    this.workerSrc = options.workerSrc;
    if (options.palette) applyPalette(this.container, options.palette);
    if (options.src !== undefined) void this.load(options.src);
  }

  async load(src: PdfSource): Promise<void> {
    const pdfjs = (await import("pdfjs-dist")) as unknown as {
      GlobalWorkerOptions: { workerSrc: string };
      getDocument(params: unknown): { promise: Promise<PdfjsDocument> };
    };
    if (!pdfjs.GlobalWorkerOptions.workerSrc) {
      pdfjs.GlobalWorkerOptions.workerSrc =
        this.workerSrc ??
        new URL("pdfjs-dist/build/pdf.worker.min.mjs", import.meta.url).href;
    }

    const params =
      typeof src === "string" || src instanceof URL
        ? { url: src.toString() }
        : { data: src };
    const doc = await pdfjs.getDocument(params).promise;
    if (this.destroyed) return;
    this.doc = doc;
    await this.renderAll();
  }

  /** (Re)render every page of the loaded document at the current scale. */
  private async renderAll(): Promise<void> {
    const doc = this.doc;
    if (!doc) return;
    this.teardownViews();
    this.container.replaceChildren();

    for (let n = 1; n <= doc.numPages; n++) {
      const page = await doc.getPage(n);
      if (this.destroyed) return;
      const viewport = page.getViewport({ scale: this.scale });
      const view = this.mountPage(n, viewport);
      const ctx = view.page.getContext("2d");
      if (ctx) await page.render({ canvasContext: ctx, viewport }).promise;
      this.hooks.onPageRender?.(n, {
        width: viewport.width,
        height: viewport.height,
        scale: this.scale,
      });
    }
    this.repaint();
  }

  getScale(): number {
    return this.scale;
  }

  async setScale(scale: number): Promise<void> {
    if (scale <= 0 || !this.doc) return;
    // Preserve scroll position across the re-render as a height ratio.
    const ratio =
      this.container.scrollHeight > 0
        ? this.container.scrollTop / this.container.scrollHeight
        : 0;
    this.scale = scale;
    await this.renderAll();
    this.container.scrollTop = ratio * this.container.scrollHeight;
  }

  async fitWidth(): Promise<void> {
    const view = this.views[0];
    if (!view) return;
    const baseWidth = view.viewport.width / this.scale; // unscaled page width
    // The CONTENT box, never clientWidth: clientWidth includes the horizontal
    // padding, and sizing to it overflows the container by 2x padding.
    const target = containerContentWidth(this.container) / baseWidth;
    if (target > 0 && Number.isFinite(target)) await this.setScale(target);
  }

  scrollToPage(page: number): void {
    const view = this.views[page - 1];
    view?.wrap.scrollIntoView({ block: "start" });
  }

  private mountPage(pageNum: number, viewport: PdfjsViewport): PageView {
    const wrap = document.createElement("div");
    wrap.className = "stx-pdf-page";
    wrap.style.position = "relative";
    wrap.style.width = `${viewport.width}px`;
    wrap.style.height = `${viewport.height}px`;
    wrap.style.margin = "0 auto";

    const page = document.createElement("canvas");
    page.width = viewport.width;
    page.height = viewport.height;

    const overlay = document.createElement("canvas");
    overlay.width = viewport.width;
    overlay.height = viewport.height;
    overlay.style.position = "absolute";
    overlay.style.inset = "0";
    overlay.style.touchAction = "none"; // let Pointer Events own gestures
    // In non-interactive (Read/Review) mode the overlay must not capture
    // pointer events, so scroll / text-selection reach the page beneath.
    overlay.style.pointerEvents = this.interactive ? "auto" : "none";

    wrap.append(page, overlay);
    this.container.append(wrap);

    const view: PageView = { pageNum, viewport, wrap, page, overlay };
    this.bindPointer(view);
    this.views.push(view);
    return view;
  }

  // ---- coordinate helpers -------------------------------------------------

  private localPoint(
    view: PageView,
    clientX: number,
    clientY: number,
  ): { cx: number; cy: number } {
    const rect = view.overlay.getBoundingClientRect();
    const cx = ((clientX - rect.left) / rect.width) * view.overlay.width;
    const cy = ((clientY - rect.top) / rect.height) * view.overlay.height;
    return { cx, cy };
  }

  private viewAt(clientX: number, clientY: number): PageView | null {
    for (const view of this.views) {
      const rect = view.overlay.getBoundingClientRect();
      if (
        clientX >= rect.left &&
        clientX <= rect.right &&
        clientY >= rect.top &&
        clientY <= rect.bottom
      ) {
        return view;
      }
    }
    return null;
  }

  getCoords(clientX: number, clientY: number): PdfCoords | null {
    const view = this.viewAt(clientX, clientY);
    if (!view) return null;
    const { cx, cy } = this.localPoint(view, clientX, clientY);
    const [pdfX, pdfY] = view.viewport.convertToPdfPoint(cx, cy);
    return { page: view.pageNum, pdfX, pdfY };
  }

  // ---- pen input ----------------------------------------------------------

  private bindPointer(view: PageView): void {
    view.overlay.addEventListener("pointerdown", (e) => this.onDown(view, e));
    view.overlay.addEventListener("pointermove", (e) => this.onMove(view, e));
    view.overlay.addEventListener("pointerup", () => this.onUp(view));
    view.overlay.addEventListener("pointercancel", () => (this.draw = null));
  }

  private toPdf(view: PageView, e: PointerEvent): PenPoint {
    const { cx, cy } = this.localPoint(view, e.clientX, e.clientY);
    const [x, y] = view.viewport.convertToPdfPoint(cx, cy);
    return e.pressure ? { x, y, pressure: e.pressure } : { x, y };
  }

  private onDown(view: PageView, e: PointerEvent): void {
    if (!this.interactive) return;
    view.overlay.setPointerCapture(e.pointerId);
    this.draw = { view, tool: this.tool, points: [this.toPdf(view, e)] };
  }

  private onMove(view: PageView, e: PointerEvent): void {
    if (!this.draw || this.draw.view !== view) return;
    const pt = this.toPdf(view, e);
    if (this.draw.tool === "freehand") this.draw.points.push(pt);
    else this.draw.points[1] = pt; // shape tools: [start, current]
    this.repaint();
  }

  private onUp(view: PageView): void {
    if (!this.draw || this.draw.view !== view) return;
    const { tool, points } = this.draw;
    this.draw = null;
    if (points.length < 2) {
      this.repaint();
      return;
    }
    this.hooks.onPenInput?.({ page: view.pageNum, tool, path: points });
    if (tool === "rect") {
      this.hooks.onRegionSelect?.(this.bbox(view.pageNum, points));
    }
    this.repaint();
  }

  private bbox(page: number, pts: PenPoint[]): PdfRect {
    const xs = pts.map((p) => p.x);
    const ys = pts.map((p) => p.y);
    const x = Math.min(...xs);
    const y = Math.min(...ys);
    return { page, x, y, w: Math.max(...xs) - x, h: Math.max(...ys) - y };
  }

  // ---- overlay rendering --------------------------------------------------

  setTool(tool: PdfTool): void {
    this.tool = tool;
  }

  setInteractive(enabled: boolean): void {
    this.interactive = enabled;
    if (!enabled) this.draw = null; // cancel any in-progress stroke
    for (const view of this.views) {
      view.overlay.style.pointerEvents = enabled ? "auto" : "none";
    }
    this.repaint(); // marks keep rendering; only the live pen preview clears
  }

  setMarks(marks: Mark[]): void {
    this.marks = marks.map((m) => ({ ...m }));
    this.hooks.onMarksChange?.(this.getMarks());
    this.repaint();
  }

  getMarks(): Mark[] {
    return this.marks.map((m) => ({ ...m }));
  }

  setPalette(palette: PdfPalette): void {
    applyPalette(this.container, palette);
  }

  private resolveColor(color: string | undefined): string {
    const fallback = "#d32f2f";
    if (!color) return fallback;
    const m = color.match(/^var\((--[\w-]+)\)$/);
    if (!m) return color;
    const resolved = getComputedStyle(this.container)
      .getPropertyValue(m[1])
      .trim();
    return resolved || fallback;
  }

  private repaint(): void {
    for (const view of this.views) {
      const ctx = view.overlay.getContext("2d");
      if (!ctx) continue;
      ctx.clearRect(0, 0, view.overlay.width, view.overlay.height);
      for (const mark of this.marks) {
        if (mark.page === view.pageNum) this.drawMark(ctx, view, mark);
      }
      if (this.draw && this.draw.view === view) {
        this.drawStroke(ctx, view, this.draw.tool, this.draw.points, undefined);
      }
    }
  }

  private vp(view: PageView, p: PenPoint): [number, number] {
    const [x, y] = view.viewport.convertToViewportPoint(p.x, p.y);
    return [x, y];
  }

  private drawMark(
    ctx: CanvasRenderingContext2D,
    view: PageView,
    mark: Mark,
  ): void {
    const pts: PenPoint[] =
      mark.path ??
      (mark.rect
        ? [
            { x: mark.rect.x, y: mark.rect.y },
            { x: mark.rect.x + mark.rect.w, y: mark.rect.y + mark.rect.h },
          ]
        : []);
    if (pts.length) this.drawStroke(ctx, view, mark.tool, pts, mark.color);
  }

  private drawStroke(
    ctx: CanvasRenderingContext2D,
    view: PageView,
    tool: PdfTool,
    pts: PenPoint[],
    color: string | undefined,
  ): void {
    const c = this.resolveColor(color);
    ctx.save();
    ctx.strokeStyle = c;
    ctx.fillStyle = c;
    ctx.lineWidth = 2;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";

    if (tool === "freehand") {
      ctx.beginPath();
      pts.forEach((p, i) => {
        const [x, y] = this.vp(view, p);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();
    } else if (pts.length >= 2) {
      const [x0, y0] = this.vp(view, pts[0]);
      const [x1, y1] = this.vp(view, pts[pts.length - 1]);
      const w = x1 - x0;
      const h = y1 - y0;
      if (tool === "highlight") {
        ctx.globalAlpha = 0.3;
        ctx.fillRect(x0, y0, w, h);
      } else if (tool === "rect") {
        ctx.strokeRect(x0, y0, w, h);
      } else if (tool === "circle") {
        ctx.beginPath();
        ctx.ellipse(
          x0 + w / 2,
          y0 + h / 2,
          Math.abs(w / 2),
          Math.abs(h / 2),
          0,
          0,
          2 * Math.PI,
        );
        ctx.stroke();
      } else if (tool === "arrow") {
        this.drawArrow(ctx, x0, y0, x1, y1);
      }
    }
    ctx.restore();
  }

  private drawArrow(
    ctx: CanvasRenderingContext2D,
    x0: number,
    y0: number,
    x1: number,
    y1: number,
  ): void {
    const head = 10;
    const angle = Math.atan2(y1 - y0, x1 - x0);
    ctx.beginPath();
    ctx.moveTo(x0, y0);
    ctx.lineTo(x1, y1);
    ctx.lineTo(
      x1 - head * Math.cos(angle - Math.PI / 6),
      y1 - head * Math.sin(angle - Math.PI / 6),
    );
    ctx.moveTo(x1, y1);
    ctx.lineTo(
      x1 - head * Math.cos(angle + Math.PI / 6),
      y1 - head * Math.sin(angle + Math.PI / 6),
    );
    ctx.stroke();
  }

  private teardownViews(): void {
    this.views = [];
    this.draw = null;
  }

  destroy(): void {
    this.destroyed = true;
    this.doc = null;
    this.teardownViews();
    this.marks = [];
    this.container.replaceChildren();
  }
}
