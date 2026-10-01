/**
 * BinaryPlaceholder -- displays download prompt for non-previewable files.
 *
 * Ported from scitex-cloud media-viewer.
 */

import type { MediaViewerConfig } from "./types";

const CLS = "stx-app-media-viewer";

export class BinaryPlaceholder {
  private config: MediaViewerConfig;

  constructor(config: MediaViewerConfig) {
    this.config = config;
  }

  render(container: HTMLElement, filePath: string): void {
    const fileName = filePath.split("/").pop() || filePath;
    const ext = filePath.substring(filePath.lastIndexOf(".")).toLowerCase();

    const wrapper = document.createElement("div");
    wrapper.className = `${CLS}__binary-wrapper`;
    wrapper.innerHTML = `
      <i class="fas fa-file-archive ${CLS}__binary-icon"></i>
      <h3>Binary File</h3>
      <p>${fileName}</p>
      <p class="${CLS}__binary-info">Cannot preview ${ext} files</p>
    `;

    const btn = document.createElement("button");
    btn.className = `${CLS}__download-btn`;
    btn.innerHTML = '<i class="fas fa-download"></i> Download';
    btn.addEventListener("click", () => this.download(filePath));
    wrapper.appendChild(btn);

    container.appendChild(wrapper);
  }

  private download(filePath: string): void {
    const a = document.createElement("a");
    a.href = this.config.getFileUrl(filePath, true, true);
    a.download = filePath.split("/").pop() || "download";
    document.body.appendChild(a);
    a.click();
    a.remove();
    this.config.onDownload?.(filePath);
  }
}
