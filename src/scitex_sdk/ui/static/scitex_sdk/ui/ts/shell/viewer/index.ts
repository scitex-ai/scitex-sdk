/**
 * Shell viewer -- barrel export.
 *
 * Ported from scitex-cloud's workspace-viewer module.
 */

export { ViewerManager } from "./_ViewerManager";
export { TabManager } from "./_TabManager";
export { ViewerRouter } from "./_ViewerRouter";
export { MarkdownPreviewPanel, renderMarkdown } from "./_MarkdownPreview";
export { ImageViewer, renderImageViewer } from "./_ImageViewer";
export { PdfViewer, renderPdfViewer } from "./_PdfViewer";
export { CsvViewer } from "./_CsvViewer";
export { AudioViewer } from "./_AudioViewer";
export { VideoViewer } from "./_VideoViewer";
export { MermaidViewer } from "./_MermaidViewer";
export { GraphvizViewer } from "./_GraphvizViewer";
export { detectFileType } from "./types";
export type {
  ViewerAdapter,
  ViewerConfig,
  OpenFile,
  FileType,
  TabInfo,
  Viewer,
} from "./types";
