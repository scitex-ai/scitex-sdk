/**
 * PdfViewer -- renders PDF files using PDF.js with page navigation and zoom.
 *
 * PDF.js is loaded from CDN on first use (no bundled dependency required).
 * Ported from scitex-cloud media-viewer.
 */

import type { MediaViewerConfig } from "./types";

const CLS = "stx-app-media-viewer";

export class PdfViewer {
  private config: MediaViewerConfig;
  private pdf: any = null;
  private currentPage = 1;
  private currentScale = 1.0;
  private canvas: HTMLCanvasElement | null = null;
  private pdfContainer: HTMLElement | null = null;

  constructor(config: MediaViewerConfig) {
    this.config = config;
  }

  render(container: HTMLElement, filePath: string, blobUrl?: string): void {
    const wrapper = document.createElement("div");
    wrapper.className = `${CLS}__pdf-wrapper`;

    wrapper.appendChild(this.createToolbar(filePath));

    this.pdfContainer = document.createElement("div");
    this.pdfContainer.className = `${CLS}__pdf-container`;

    this.canvas = document.createElement("canvas");
    this.canvas.className = `${CLS}__pdf-canvas`;
    this.pdfContainer.appendChild(this.canvas);

    wrapper.appendChild(this.pdfContainer);
    container.appendChild(wrapper);

    this.loadPdf(filePath, blobUrl);
  }

  private createToolbar(filePath: string): HTMLElement {
    const toolbar = document.createElement("div");
    toolbar.className = `${CLS}__toolbar`;

    const fileName = filePath.split("/").pop() || filePath;

    toolbar.innerHTML = `
      <div class="${CLS}__toolbar-left">
        <i class="fas fa-file-pdf"></i>
        <span title="${filePath}">${fileName}</span>
      </div>
      <div class="${CLS}__toolbar-center">
        <div class="${CLS}__pdf-controls">
          <button class="${CLS}__pdf-prev" title="Previous page">
            <i class="fas fa-chevron-left"></i>
          </button>
          <span class="${CLS}__pdf-page-info">
            <input type="number" class="${CLS}__pdf-page-input" min="1" value="1">
            <span> / </span>
            <span class="${CLS}__pdf-total-pages">-</span>
          </span>
          <button class="${CLS}__pdf-next" title="Next page">
            <i class="fas fa-chevron-right"></i>
          </button>
          <span class="${CLS}__pdf-separator"></span>
          <button class="${CLS}__pdf-zoom-out" title="Zoom out">
            <i class="fas fa-search-minus"></i>
          </button>
          <span class="${CLS}__pdf-zoom-level">100%</span>
          <button class="${CLS}__pdf-zoom-in" title="Zoom in">
            <i class="fas fa-search-plus"></i>
          </button>
          <button class="${CLS}__pdf-fit-width" title="Fit width">
            <i class="fas fa-arrows-alt-h"></i>
          </button>
        </div>
      </div>
      <div class="${CLS}__toolbar-right">
        <button class="${CLS}__btn" title="Download">
          <i class="fas fa-download"></i>
        </button>
        <button class="${CLS}__btn ${CLS}__open-new-tab" title="Open in new tab">
          <i class="fas fa-external-link-alt"></i>
        </button>
      </div>
    `;

    const buttons = toolbar.querySelectorAll(
      `.${CLS}__toolbar-right .${CLS}__btn`,
    );
    buttons[0]?.addEventListener("click", () => this.download(filePath));
    toolbar
      .querySelector(`.${CLS}__open-new-tab`)
      ?.addEventListener("click", () => {
        window.open(this.config.getFileUrl(filePath, true, false), "_blank");
      });

    return toolbar;
  }

  private async loadPdf(filePath: string, blobUrl?: string): Promise<void> {
    await this.ensurePdfJsLoaded();

    const lib = (window as any).pdfjsLib;
    if (!lib) {
      console.error("[PdfViewer] PDF.js not available");
      return;
    }

    const pdfUrl = blobUrl || this.config.getFileUrl(filePath, true, false);

    try {
      const loadingTask = lib.getDocument(pdfUrl);
      this.pdf = await loadingTask.promise;
      this.currentPage = 1;
      this.currentScale = 1.0;

      const totalEl = document.querySelector(`.${CLS}__pdf-total-pages`);
      if (totalEl) {
        totalEl.textContent = this.pdf.numPages.toString();
      }

      await this.renderPage();
      this.setupControls();
    } catch (error) {
      console.error("[PdfViewer] Error loading PDF:", error);
      if (this.pdfContainer) {
        this.pdfContainer.innerHTML = `
          <div class="${CLS}__error">
            <i class="fas fa-exclamation-triangle"></i>
            <p>Failed to load PDF</p>
            <small>${filePath}</small>
          </div>
        `;
      }
    }
  }

  private ensurePdfJsLoaded(): Promise<void> {
    return new Promise((resolve, reject) => {
      if ((window as any).pdfjsLib) {
        resolve();
        return;
      }

      const script = document.createElement("script");
      script.src =
        "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js";
      script.onload = () => {
        const lib = (window as any).pdfjsLib;
        if (lib) {
          lib.GlobalWorkerOptions.workerSrc =
            "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
        }
        resolve();
      };
      script.onerror = reject;
      document.head.appendChild(script);
    });
  }

  private async renderPage(): Promise<void> {
    if (!this.pdf || !this.canvas) return;

    const page = await this.pdf.getPage(this.currentPage);
    const viewport = page.getViewport({ scale: this.currentScale });

    this.canvas.height = viewport.height;
    this.canvas.width = viewport.width;

    const context = this.canvas.getContext("2d");
    if (!context) return;

    await page.render({ canvasContext: context, viewport }).promise;

    const pageInput = document.querySelector(
      `.${CLS}__pdf-page-input`,
    ) as HTMLInputElement | null;
    if (pageInput) {
      pageInput.value = this.currentPage.toString();
    }

    const zoomEl = document.querySelector(`.${CLS}__pdf-zoom-level`);
    if (zoomEl) {
      zoomEl.textContent = `${Math.round(this.currentScale * 100)}%`;
    }
  }

  private setupControls(): void {
    if (!this.pdf) return;

    const goToPage = async (num: number) => {
      if (num < 1 || num > this.pdf.numPages) return;
      this.currentPage = num;
      await this.renderPage();
    };

    const setZoom = async (scale: number) => {
      this.currentScale = scale;
      await this.renderPage();
    };

    document
      .querySelector(`.${CLS}__pdf-prev`)
      ?.addEventListener("click", () => goToPage(this.currentPage - 1));

    document
      .querySelector(`.${CLS}__pdf-next`)
      ?.addEventListener("click", () => goToPage(this.currentPage + 1));

    const pageInput = document.querySelector(
      `.${CLS}__pdf-page-input`,
    ) as HTMLInputElement | null;
    pageInput?.addEventListener("change", () => {
      goToPage(parseInt(pageInput.value, 10));
    });

    document
      .querySelector(`.${CLS}__pdf-zoom-in`)
      ?.addEventListener("click", () => setZoom(this.currentScale * 1.25));

    document
      .querySelector(`.${CLS}__pdf-zoom-out`)
      ?.addEventListener("click", () => setZoom(this.currentScale / 1.25));

    document
      .querySelector(`.${CLS}__pdf-fit-width`)
      ?.addEventListener("click", async () => {
        if (!this.pdfContainer || !this.pdf) return;
        const page = await this.pdf.getPage(this.currentPage);
        const viewport = page.getViewport({ scale: 1 });
        const scale = (this.pdfContainer.clientWidth - 40) / viewport.width;
        setZoom(scale);
      });
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

  cleanup(): void {
    this.pdf = null;
    this.canvas = null;
    this.pdfContainer = null;
    this.currentPage = 1;
    this.currentScale = 1.0;
  }
}
