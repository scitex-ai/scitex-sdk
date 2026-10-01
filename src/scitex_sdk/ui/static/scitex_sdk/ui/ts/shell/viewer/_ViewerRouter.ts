/**
 * ViewerRouter - Routes file types to dedicated viewer instances.
 *
 * Ported from scitex-cloud's workspace-viewer/_ViewerRouter.ts.
 * Uses adapter pattern: viewers receive ViewerAdapter instead of
 * calling global getFileUrl().
 */

import { detectFileType, type FileType, type Viewer } from "./types";
import { ImageViewer } from "./_ImageViewer";
import { PdfViewer } from "./_PdfViewer";
import { CsvViewer } from "./_CsvViewer";
import { AudioViewer } from "./_AudioViewer";
import { VideoViewer } from "./_VideoViewer";
import { MermaidViewer } from "./_MermaidViewer";
import { GraphvizViewer } from "./_GraphvizViewer";

export class ViewerRouter {
  private viewers: Map<FileType, Viewer> = new Map();

  /**
   * Return the appropriate Viewer for a file path, or null for text/binary.
   * Viewer instances are reused across files of the same type.
   */
  getViewer(filePath: string): Viewer | null {
    const fileType = detectFileType(filePath);

    if (fileType === "text") return null;
    if (fileType === "binary") return null;

    if (!this.viewers.has(fileType)) {
      const viewer = this.createViewer(fileType);
      if (!viewer) return null;
      this.viewers.set(fileType, viewer);
    }

    return this.viewers.get(fileType) ?? null;
  }

  destroyAll(): void {
    this.viewers.forEach((v) => v.destroy());
    this.viewers.clear();
  }

  private createViewer(fileType: FileType): Viewer | null {
    switch (fileType) {
      case "image":
        return new ImageViewer();
      case "pdf":
        return new PdfViewer();
      case "csv":
        return new CsvViewer();
      case "mermaid":
        return new MermaidViewer();
      case "graphviz":
        return new GraphvizViewer();
      case "audio":
        return new AudioViewer();
      case "video":
        return new VideoViewer();
      default:
        return null;
    }
  }
}
