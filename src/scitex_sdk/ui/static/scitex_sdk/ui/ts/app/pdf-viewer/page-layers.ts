/** SDK-owned PDF.js text and link layers. No application routes or data ports. */
import type { PDFDocumentProxy, PDFPageProxy, PageViewport } from "pdfjs-dist";

interface LayerOptions {
  TextLayer: typeof import("pdfjs-dist").TextLayer;
  page: PDFPageProxy;
  doc: PDFDocumentProxy;
  viewport: PageViewport;
  element: HTMLElement;
  text: boolean;
  links: boolean;
  navigate(page: number): void;
}

/** Return cleanup for PDF.js text tasks and layer event listeners. */
export async function renderPageLayers(options: LayerOptions): Promise<() => void> {
  const { page, doc, viewport, element } = options;
  const owned: HTMLElement[] = [];
  let cancelText = () => {};
  if (options.text) {
    const { TextLayer } = options;
    const layer = document.createElement("div");
    layer.dataset.stxPdfLayer = "text";
    Object.assign(layer.style, {
      position: "absolute", inset: "0", overflow: "hidden", lineHeight: "1",
      textAlign: "initial", textSizeAdjust: "none", forcedColorAdjust: "none",
      transformOrigin: "0 0", zIndex: "1",
    });
    layer.style.setProperty("--scale-factor", String(viewport.scale));
    element.append(layer);
    owned.push(layer);
    const task = new TextLayer({ textContentSource: await page.getTextContent(), container: layer, viewport });
    cancelText = () => task.cancel();
    await task.render();
    for (const span of layer.querySelectorAll<HTMLElement>("span, br")) {
      Object.assign(span.style, { position: "absolute", whiteSpace: "pre", color: "transparent", cursor: "text", transformOrigin: "0 0" });
    }
  }
  if (options.links) {
    const layer = document.createElement("div");
    layer.dataset.stxPdfLayer = "links";
    Object.assign(layer.style, { position: "absolute", inset: "0", pointerEvents: "none", zIndex: "2" });
    element.append(layer);
    owned.push(layer);
    for (const annotation of await page.getAnnotations({ intent: "display" })) {
      if (annotation.subtype !== "Link" || !Array.isArray(annotation.rect)) continue;
      const [x0, y0, x1, y1] = viewport.convertToViewportRectangle(annotation.rect);
      const link = document.createElement("a");
      const destination: unknown = annotation.dest;
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
        position: "absolute", pointerEvents: "auto", display: "block",
        left: `${Math.min(x0, x1)}px`, top: `${Math.min(y0, y1)}px`,
        width: `${Math.abs(x1 - x0)}px`, height: `${Math.abs(y1 - y0)}px`,
      });
      layer.append(link);
    }
  }
  return () => { cancelText(); for (const layer of owned) layer.remove(); };
}

async function resolveDestination(doc: PDFDocumentProxy, destination: unknown): Promise<number | null> {
  const dest = typeof destination === "string" ? await doc.getDestination(destination) : destination;
  if (!Array.isArray(dest) || !dest.length) return null;
  const ref: unknown = dest[0];
  if (Number.isInteger(ref)) return (ref as number) + 1;
  if (ref && typeof ref === "object" && "num" in ref && "gen" in ref) {
    return (await doc.getPageIndex(ref as { num: number; gen: number })) + 1;
  }
  return null;
}
