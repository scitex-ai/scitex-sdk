/**
 * ImageViewer -- renders image files with zoom and pan.
 *
 * Ported from scitex-cloud media-viewer, adapted for scitex-ui conventions.
 */

import type { MediaViewerConfig } from "./types";

const CLS = "stx-app-media-viewer";

export class ImageViewer {
  private config: MediaViewerConfig;

  constructor(config: MediaViewerConfig) {
    this.config = config;
  }

  render(container: HTMLElement, filePath: string, blobUrl?: string): void {
    const wrapper = document.createElement("div");
    wrapper.className = `${CLS}__image-wrapper`;

    wrapper.appendChild(this.createToolbar(filePath));

    const imgContainer = document.createElement("div");
    imgContainer.className = `${CLS}__image-container`;

    const img = document.createElement("img");
    img.className = `${CLS}__image`;
    img.alt = filePath.split("/").pop() || "Image";
    img.src = blobUrl || this.config.getFileUrl(filePath, true, false);
    img.onerror = () => {
      img.style.display = "none";
      const errorMsg = document.createElement("div");
      errorMsg.className = `${CLS}__error`;
      errorMsg.innerHTML =
        '<i class="fas fa-exclamation-triangle"></i> Failed to load image';
      imgContainer.appendChild(errorMsg);
    };

    imgContainer.appendChild(img);
    wrapper.appendChild(imgContainer);
    container.appendChild(wrapper);

    this.setupZoomPan(img, imgContainer);
  }

  private createToolbar(filePath: string): HTMLElement {
    const toolbar = document.createElement("div");
    toolbar.className = `${CLS}__toolbar`;

    const fileName = filePath.split("/").pop() || filePath;
    toolbar.innerHTML = `
      <div class="${CLS}__toolbar-left">
        <i class="fas fa-image"></i>
        <span title="${filePath}">${fileName}</span>
      </div>
    `;

    const right = document.createElement("div");
    right.className = `${CLS}__toolbar-right`;

    const dlBtn = document.createElement("button");
    dlBtn.className = `${CLS}__btn`;
    dlBtn.title = "Download";
    dlBtn.innerHTML = '<i class="fas fa-download"></i>';
    dlBtn.addEventListener("click", () => this.download(filePath));
    right.appendChild(dlBtn);

    const openBtn = document.createElement("button");
    openBtn.className = `${CLS}__btn`;
    openBtn.title = "Open in new tab";
    openBtn.innerHTML = '<i class="fas fa-external-link-alt"></i>';
    openBtn.addEventListener("click", () => {
      window.open(this.config.getFileUrl(filePath, true, false), "_blank");
    });
    right.appendChild(openBtn);

    toolbar.appendChild(right);
    return toolbar;
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

  private setupZoomPan(img: HTMLImageElement, container: HTMLElement): void {
    let scale = 1;
    let dragging = false;
    let startX = 0;
    let startY = 0;
    let tx = 0;
    let ty = 0;

    const update = () => {
      img.style.transform = `translate(${tx}px, ${ty}px) scale(${scale})`;
    };

    container.addEventListener("wheel", (e) => {
      e.preventDefault();
      scale = Math.max(0.1, Math.min(10, scale * (e.deltaY > 0 ? 0.9 : 1.1)));
      update();
    });

    img.addEventListener("mousedown", (e) => {
      dragging = true;
      startX = e.clientX - tx;
      startY = e.clientY - ty;
      img.style.cursor = "grabbing";
    });

    document.addEventListener("mousemove", (e) => {
      if (!dragging) return;
      tx = e.clientX - startX;
      ty = e.clientY - startY;
      update();
    });

    document.addEventListener("mouseup", () => {
      dragging = false;
      img.style.cursor = "grab";
    });

    img.addEventListener("dblclick", () => {
      scale = 1;
      tx = 0;
      ty = 0;
      update();
    });

    img.style.cursor = "grab";
  }
}
