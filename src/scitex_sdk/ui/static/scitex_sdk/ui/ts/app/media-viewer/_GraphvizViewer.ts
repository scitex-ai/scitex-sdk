/**
 * GraphvizViewer -- renders .dot/.gv files as Graphviz diagrams.
 *
 * Uses lazy import of @hpcc-js/wasm-graphviz (listed in package.json).
 * Ported from scitex-cloud media-viewer.
 */

import type { MediaViewerConfig } from "./types";

const CLS = "stx-app-media-viewer";

export class GraphvizViewer {
  private config: MediaViewerConfig;

  constructor(config: MediaViewerConfig) {
    this.config = config;
  }

  async render(container: HTMLElement, filePath: string): Promise<void> {
    container.innerHTML = `<div class="${CLS}__loading">
      <i class="fas fa-spinner fa-spin"></i> Loading graphviz diagram...
    </div>`;

    try {
      const url = this.config.getFileUrl(filePath, true);
      const response = await fetch(url);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const ct = response.headers.get("content-type") || "";
      let code: string;
      if (ct.includes("application/json")) {
        const json = await response.json();
        code = (json.content ?? "").trim();
      } else {
        code = (await response.text()).trim();
      }

      if (!code) {
        container.innerHTML = `<div class="${CLS}__placeholder">Empty diagram file</div>`;
        return;
      }

      const { Graphviz } = await import("@hpcc-js/wasm-graphviz");
      const graphviz = await Graphviz.load();
      const svg = graphviz.dot(code);

      const wrapper = document.createElement("div");
      wrapper.className = `${CLS}__graphviz-wrapper`;
      wrapper.innerHTML = svg;
      container.innerHTML = "";
      container.appendChild(wrapper);
    } catch (err) {
      console.error("[GraphvizViewer] Render error:", err);
      container.innerHTML = `
        <div class="${CLS}__error">
          <i class="fas fa-exclamation-triangle"></i>
          <p>Failed to render diagram: ${err instanceof Error ? err.message : String(err)}</p>
        </div>
      `;
    }
  }
}
