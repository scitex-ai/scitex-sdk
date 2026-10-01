// @scitex/ui/pdf-viewer/react — React adapter barrel.
export { PdfViewer } from "./PdfViewer";
export type { PdfViewerProps } from "./PdfViewer";

// Re-export the L1 hook-API types so React consumers get them from one place.
export type {
  Mark,
  PdfCoords,
  PdfPalette,
  PdfRect,
  PdfSource,
  PdfTool,
  PdfViewerApi,
  PdfViewerHooks,
  PdfViewport,
  PenInput,
  PenPoint,
} from "../../../ts/app/pdf-viewer";
