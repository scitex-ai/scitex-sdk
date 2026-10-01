/**
 * MediaViewer module -- reusable viewers for non-text files.
 *
 * @module media-viewer
 */

export { MediaViewer } from "./_MediaViewer";
export { ImageViewer } from "./_ImageViewer";
export { PdfViewer } from "./_PdfViewer";
export { MermaidViewer } from "./_MermaidViewer";
export { GraphvizViewer } from "./_GraphvizViewer";
export { BinaryPlaceholder } from "./_BinaryPlaceholder";

export type { MediaViewerConfig, MediaFileType } from "./types";
export {
  detectFileType,
  IMAGE_EXTENSIONS,
  PDF_EXTENSIONS,
  CSV_EXTENSIONS,
  MERMAID_EXTENSIONS,
  GRAPHVIZ_EXTENSIONS,
  BINARY_EXTENSIONS,
} from "./types";
