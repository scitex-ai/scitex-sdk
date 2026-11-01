/* AUTO-GENERATED from ts/app/pdf-viewer/index.ts via esbuild — do not edit by hand. Rebuild: npm run build:ui -- --only js/app/pdf-viewer.js */

// ts/app/pdf-viewer/page-layers.ts
async function renderPageLayers(options) {
  const { page, doc, viewport, element } = options;
  const owned = [];
  let cancelText = () => {
  };
  if (options.text) {
    const { TextLayer } = options;
    const layer = document.createElement("div");
    layer.className = "stx-pdf-text-layer";
    Object.assign(layer.style, {
      position: "absolute",
      inset: "0",
      overflow: "hidden",
      lineHeight: "1",
      textAlign: "initial",
      textSizeAdjust: "none",
      forcedColorAdjust: "none",
      transformOrigin: "0 0",
      zIndex: "1"
    });
    layer.style.setProperty("--scale-factor", String(viewport.scale));
    element.append(layer);
    owned.push(layer);
    const task = new TextLayer({ textContentSource: await page.getTextContent(), container: layer, viewport });
    cancelText = () => task.cancel();
    await task.render();
    for (const span of layer.querySelectorAll("span, br")) {
      Object.assign(span.style, { position: "absolute", whiteSpace: "pre", color: "transparent", cursor: "text", transformOrigin: "0 0" });
    }
  }
  if (options.links) {
    const layer = document.createElement("div");
    layer.className = "stx-pdf-link-layer";
    Object.assign(layer.style, { position: "absolute", inset: "0", pointerEvents: "none", zIndex: "2" });
    element.append(layer);
    owned.push(layer);
    for (const annotation of await page.getAnnotations({ intent: "display" })) {
      if (annotation.subtype !== "Link" || !Array.isArray(annotation.rect)) continue;
      const [x0, y0, x1, y1] = viewport.convertToViewportRectangle(annotation.rect);
      const link = document.createElement("a");
      const destination = annotation.dest;
      if (annotation.url) {
        const url = new URL(annotation.url, document.baseURI);
        if (!["http:", "https:", "mailto:"].includes(url.protocol)) continue;
        link.href = url.href;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.setAttribute("aria-label", annotation.title || "Open PDF link");
      } else if (destination) {
        link.href = "#";
        link.setAttribute("aria-label", "Go to PDF destination");
        link.addEventListener("click", (event) => {
          event.preventDefault();
          void resolveDestination(doc, destination).then((target) => {
            if (target !== null && element.isConnected) options.navigate(target);
          });
        });
      } else continue;
      Object.assign(link.style, {
        position: "absolute",
        pointerEvents: "auto",
        display: "block",
        left: `${Math.min(x0, x1)}px`,
        top: `${Math.min(y0, y1)}px`,
        width: `${Math.abs(x1 - x0)}px`,
        height: `${Math.abs(y1 - y0)}px`
      });
      layer.append(link);
    }
  }
  return () => {
    cancelText();
    for (const layer of owned) layer.remove();
  };
}
async function resolveDestination(doc, destination) {
  const dest = typeof destination === "string" ? await doc.getDestination(destination) : destination;
  if (!Array.isArray(dest) || !dest.length) return null;
  const ref = dest[0];
  if (Number.isInteger(ref)) return ref + 1;
  if (ref && typeof ref === "object" && "num" in ref && "gen" in ref) {
    return await doc.getPageIndex(ref) + 1;
  }
  return null;
}

// ts/app/pdf-viewer/index.ts
function createPdfViewer(options) {
  return new PdfViewer(options);
}
function applyPalette(el, palette) {
  for (const [key, value] of Object.entries(palette)) {
    el.style.setProperty(`--stx-verdict-${key}`, value);
  }
}
function contentBoxWidth(clientWidth, paddingLeft, paddingRight) {
  const content = clientWidth - (paddingLeft + paddingRight);
  return content > 0 ? content : 0;
}
function containerContentWidth(container) {
  const style = getComputedStyle(container);
  return contentBoxWidth(
    container.clientWidth,
    parseFloat(style.paddingLeft) || 0,
    parseFloat(style.paddingRight) || 0
  );
}
var PdfViewer = class {
  container;
  hooks;
  scale;
  workerSrc;
  runtime;
  textLayer;
  linkLayer;
  layerCleanups = [];
  marks = [];
  tool;
  views = [];
  draw = null;
  destroyed = false;
  loadEpoch = 0;
  renderEpoch = 0;
  doc = null;
  loadedRuntime;
  interactive = true;
  constructor(options) {
    this.container = options.container;
    this.hooks = options.hooks ?? {};
    this.tool = options.tool ?? "highlight";
    this.scale = options.scale ?? 1.5;
    this.workerSrc = options.workerSrc;
    this.runtime = options.pdfjs;
    this.textLayer = options.textLayer ?? false;
    this.linkLayer = options.linkLayer ?? false;
    if (options.palette) applyPalette(this.container, options.palette);
    if (options.src !== void 0) void this.load(options.src);
  }
  async load(src) {
    const epoch = ++this.loadEpoch;
    const pdfjs = this.runtime ?? await import("pdfjs-dist");
    this.loadedRuntime = pdfjs;
    if (!pdfjs.GlobalWorkerOptions.workerSrc) {
      pdfjs.GlobalWorkerOptions.workerSrc = this.workerSrc ?? new URL("pdfjs-dist/build/pdf.worker.min.mjs", import.meta.url).href;
    }
    const params = typeof src === "string" || src instanceof URL ? { url: src.toString() } : { data: src };
    const doc = await pdfjs.getDocument(params).promise;
    if (this.destroyed || epoch !== this.loadEpoch) {
      await doc.destroy();
      return;
    }
    const previous = this.doc;
    this.doc = doc;
    if (previous) void previous.destroy();
    await this.renderAll();
  }
  /** (Re)render every page of the loaded document at the current scale. */
  async renderAll() {
    const doc = this.doc;
    const epoch = ++this.renderEpoch;
    if (!doc) return;
    this.teardownViews();
    this.container.replaceChildren();
    for (let n = 1; n <= doc.numPages; n++) {
      const page = await doc.getPage(n);
      if (this.destroyed || epoch !== this.renderEpoch) return;
      const viewport = page.getViewport({ scale: this.scale });
      const view = this.mountPage(n, viewport);
      const ctx = view.page.getContext("2d");
      if (ctx) await page.render({ canvasContext: ctx, viewport }).promise;
      if (this.destroyed || epoch !== this.renderEpoch) return;
      if (this.textLayer || this.linkLayer) {
        const cleanup = await renderPageLayers({
          page,
          doc,
          viewport,
          element: view.wrap,
          TextLayer: this.loadedRuntime.TextLayer,
          text: this.textLayer,
          links: this.linkLayer,
          navigate: (target) => this.scrollToPage(target)
        });
        if (this.destroyed || epoch !== this.renderEpoch) {
          cleanup();
          return;
        }
        this.layerCleanups.push(cleanup);
      }
      this.hooks.onPageRender?.(n, {
        width: viewport.width,
        height: viewport.height,
        scale: this.scale
      }, {
        element: view.wrap,
        pdfToViewportPoint: (x, y) => viewport.convertToViewportPoint(x, y),
        pdfToViewportRect: (rect) => viewport.convertToViewportRectangle(rect),
        viewportToPdfPoint: (x, y) => viewport.convertToPdfPoint(x, y)
      });
    }
    this.repaint();
  }
  getScale() {
    return this.scale;
  }
  async setScale(scale) {
    if (scale <= 0 || !this.doc) return;
    const ratio = this.container.scrollHeight > 0 ? this.container.scrollTop / this.container.scrollHeight : 0;
    this.scale = scale;
    await this.renderAll();
    this.container.scrollTop = ratio * this.container.scrollHeight;
  }
  async fitWidth() {
    const view = this.views[0];
    if (!view) return;
    const baseWidth = view.viewport.width / this.scale;
    const target = containerContentWidth(this.container) / baseWidth;
    if (target > 0 && Number.isFinite(target)) await this.setScale(target);
  }
  scrollToPage(page) {
    const view = this.views[page - 1];
    view?.wrap.scrollIntoView({ block: "start" });
  }
  mountPage(pageNum, viewport) {
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
    overlay.style.zIndex = "3";
    overlay.style.inset = "0";
    overlay.style.touchAction = "none";
    overlay.style.pointerEvents = this.interactive ? "auto" : "none";
    wrap.append(page, overlay);
    this.container.append(wrap);
    const view = { pageNum, viewport, wrap, page, overlay };
    this.bindPointer(view);
    this.views.push(view);
    return view;
  }
  // ---- coordinate helpers -------------------------------------------------
  localPoint(view, clientX, clientY) {
    const rect = view.overlay.getBoundingClientRect();
    const cx = (clientX - rect.left) / rect.width * view.overlay.width;
    const cy = (clientY - rect.top) / rect.height * view.overlay.height;
    return { cx, cy };
  }
  viewAt(clientX, clientY) {
    for (const view of this.views) {
      const rect = view.overlay.getBoundingClientRect();
      if (clientX >= rect.left && clientX <= rect.right && clientY >= rect.top && clientY <= rect.bottom) {
        return view;
      }
    }
    return null;
  }
  getCoords(clientX, clientY) {
    const view = this.viewAt(clientX, clientY);
    if (!view) return null;
    const { cx, cy } = this.localPoint(view, clientX, clientY);
    const [pdfX, pdfY] = view.viewport.convertToPdfPoint(cx, cy);
    return { page: view.pageNum, pdfX, pdfY };
  }
  // ---- pen input ----------------------------------------------------------
  bindPointer(view) {
    view.overlay.addEventListener("pointerdown", (e) => this.onDown(view, e));
    view.overlay.addEventListener("pointermove", (e) => this.onMove(view, e));
    view.overlay.addEventListener("pointerup", () => this.onUp(view));
    view.overlay.addEventListener("pointercancel", () => this.draw = null);
  }
  toPdf(view, e) {
    const { cx, cy } = this.localPoint(view, e.clientX, e.clientY);
    const [x, y] = view.viewport.convertToPdfPoint(cx, cy);
    return e.pressure ? { x, y, pressure: e.pressure } : { x, y };
  }
  onDown(view, e) {
    if (!this.interactive) return;
    view.overlay.setPointerCapture(e.pointerId);
    this.draw = { view, tool: this.tool, points: [this.toPdf(view, e)] };
  }
  onMove(view, e) {
    if (!this.draw || this.draw.view !== view) return;
    const pt = this.toPdf(view, e);
    if (this.draw.tool === "freehand") this.draw.points.push(pt);
    else this.draw.points[1] = pt;
    this.repaint();
  }
  onUp(view) {
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
  bbox(page, pts) {
    const xs = pts.map((p) => p.x);
    const ys = pts.map((p) => p.y);
    const x = Math.min(...xs);
    const y = Math.min(...ys);
    return { page, x, y, w: Math.max(...xs) - x, h: Math.max(...ys) - y };
  }
  // ---- overlay rendering --------------------------------------------------
  setTool(tool) {
    this.tool = tool;
  }
  setInteractive(enabled) {
    this.interactive = enabled;
    if (!enabled) this.draw = null;
    for (const view of this.views) {
      view.overlay.style.pointerEvents = enabled ? "auto" : "none";
    }
    this.repaint();
  }
  setMarks(marks) {
    this.marks = marks.map((m) => ({ ...m }));
    this.hooks.onMarksChange?.(this.getMarks());
    this.repaint();
  }
  getMarks() {
    return this.marks.map((m) => ({ ...m }));
  }
  setPalette(palette) {
    applyPalette(this.container, palette);
  }
  resolveColor(color) {
    const fallback = "#d32f2f";
    if (!color) return fallback;
    const m = color.match(/^var\((--[\w-]+)\)$/);
    if (!m) return color;
    const resolved = getComputedStyle(this.container).getPropertyValue(m[1]).trim();
    return resolved || fallback;
  }
  repaint() {
    for (const view of this.views) {
      const ctx = view.overlay.getContext("2d");
      if (!ctx) continue;
      ctx.clearRect(0, 0, view.overlay.width, view.overlay.height);
      for (const mark of this.marks) {
        if (mark.page === view.pageNum) this.drawMark(ctx, view, mark);
      }
      if (this.draw && this.draw.view === view) {
        this.drawStroke(ctx, view, this.draw.tool, this.draw.points, void 0);
      }
    }
  }
  vp(view, p) {
    const [x, y] = view.viewport.convertToViewportPoint(p.x, p.y);
    return [x, y];
  }
  drawMark(ctx, view, mark) {
    const pts = mark.path ?? (mark.rect ? [
      { x: mark.rect.x, y: mark.rect.y },
      { x: mark.rect.x + mark.rect.w, y: mark.rect.y + mark.rect.h }
    ] : []);
    if (pts.length) this.drawStroke(ctx, view, mark.tool, pts, mark.color);
  }
  drawStroke(ctx, view, tool, pts, color) {
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
          2 * Math.PI
        );
        ctx.stroke();
      } else if (tool === "arrow") {
        this.drawArrow(ctx, x0, y0, x1, y1);
      }
    }
    ctx.restore();
  }
  drawArrow(ctx, x0, y0, x1, y1) {
    const head = 10;
    const angle = Math.atan2(y1 - y0, x1 - x0);
    ctx.beginPath();
    ctx.moveTo(x0, y0);
    ctx.lineTo(x1, y1);
    ctx.lineTo(
      x1 - head * Math.cos(angle - Math.PI / 6),
      y1 - head * Math.sin(angle - Math.PI / 6)
    );
    ctx.moveTo(x1, y1);
    ctx.lineTo(
      x1 - head * Math.cos(angle + Math.PI / 6),
      y1 - head * Math.sin(angle + Math.PI / 6)
    );
    ctx.stroke();
  }
  teardownViews() {
    for (const cleanup of this.layerCleanups.splice(0)) cleanup();
    this.views = [];
    this.draw = null;
  }
  destroy() {
    this.destroyed = true;
    this.loadEpoch++;
    this.renderEpoch++;
    if (this.doc) void this.doc.destroy();
    this.doc = null;
    this.teardownViews();
    this.marks = [];
    this.container.replaceChildren();
  }
};
export {
  contentBoxWidth,
  createPdfViewer
};
