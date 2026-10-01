/**
 * MediaViewer -- displays non-text files (images, PDFs, diagrams, binaries).
 *
 * Delegates rendering to specialised viewer classes:
 *   ImageViewer, PdfViewer, MermaidViewer, GraphvizViewer, BinaryPlaceholder.
 *
 * CSV type is detected but not rendered here -- consumers should handle CSV
 * files via their own editor/table component (e.g. DataTable from scitex-ui).
 *
 * Usage:
 *   import { MediaViewer } from 'scitex_sdk/ui/ts/app/media-viewer';
 *   const viewer = new MediaViewer({
 *     container: '#media-panel',
 *     getFileUrl: (path, raw) => `/api/file/${path}?raw=${raw}`,
 *   });
 *   viewer.displayFile('plot.png');
 */

import { BaseComponent } from "../../_base/BaseComponent";
import type { MediaViewerConfig, MediaFileType } from "./types";
import { detectFileType } from "./types";
import { ImageViewer } from "./_ImageViewer";
import { PdfViewer } from "./_PdfViewer";
import { MermaidViewer } from "./_MermaidViewer";
import { GraphvizViewer } from "./_GraphvizViewer";
import { BinaryPlaceholder } from "./_BinaryPlaceholder";

const CLS = "stx-app-media-viewer";

export class MediaViewer extends BaseComponent<MediaViewerConfig> {
  private currentFile: string | null = null;
  private imageViewer: ImageViewer;
  private pdfViewer: PdfViewer;
  private mermaidViewer: MermaidViewer;
  private graphvizViewer: GraphvizViewer;
  private binaryPlaceholder: BinaryPlaceholder;
  private editorElement: HTMLElement | null = null;

  constructor(config: MediaViewerConfig) {
    super(config);
    this.container.classList.add(CLS);
    this.imageViewer = new ImageViewer(config);
    this.pdfViewer = new PdfViewer(config);
    this.mermaidViewer = new MermaidViewer(config);
    this.graphvizViewer = new GraphvizViewer(config);
    this.binaryPlaceholder = new BinaryPlaceholder(config);
  }

  /**
   * Set the editor element to hide/show when switching views.
   * Optional -- only needed when MediaViewer coexists with an editor.
   */
  setEditorElement(element: HTMLElement | string): void {
    if (typeof element === "string") {
      this.editorElement = document.getElementById(element);
    } else {
      this.editorElement = element;
    }
  }

  /** Show media viewer and hide editor. */
  show(): void {
    this.container.style.display = "flex";
    if (this.editorElement) {
      this.editorElement.style.display = "none";
    }
    this.config.onVisibilityChange?.(true);
  }

  /** Hide media viewer and show editor. */
  hide(): void {
    this.container.style.display = "none";
    if (this.editorElement) {
      this.editorElement.style.display = "block";
    }
    this.config.onVisibilityChange?.(false);
  }

  /** Display a file. Auto-detects type from extension. */
  async displayFile(
    filePath: string,
    fileType?: MediaFileType,
    blobUrl?: string,
  ): Promise<void> {
    const type = fileType || detectFileType(filePath);

    // Text and CSV files should be handled externally
    if (type === "text" || type === "csv") {
      this.hide();
      return;
    }

    this.currentFile = filePath;
    this.container.innerHTML = "";

    switch (type) {
      case "image":
        this.imageViewer.render(this.container, filePath, blobUrl);
        break;
      case "pdf":
        this.pdfViewer.render(this.container, filePath, blobUrl);
        break;
      case "mermaid":
        await this.mermaidViewer.render(this.container, filePath);
        break;
      case "graphviz":
        await this.graphvizViewer.render(this.container, filePath);
        break;
      case "binary":
        this.binaryPlaceholder.render(this.container, filePath);
        break;
    }

    this.show();
  }

  /** Check if a file can be displayed by this viewer. */
  canDisplay(filePath: string): boolean {
    const type = detectFileType(filePath);
    return type !== "text" && type !== "csv";
  }

  /** Get current file path. */
  getCurrentFile(): string | null {
    return this.currentFile;
  }

  /** Check if the viewer is currently visible. */
  isVisible(): boolean {
    return this.container.style.display !== "none";
  }

  /** Clean up resources. */
  override destroy(): void {
    this.pdfViewer.cleanup();
    this.currentFile = null;
    this.container.classList.remove(CLS);
    super.destroy();
  }
}
