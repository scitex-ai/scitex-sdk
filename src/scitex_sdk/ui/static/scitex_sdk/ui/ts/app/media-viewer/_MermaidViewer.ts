/**
 * MermaidViewer -- renders .mmd files as Mermaid diagrams.
 *
 * Uses lazy import of the mermaid library (listed in package.json).
 * Ported from scitex-cloud media-viewer.
 */

import type { MediaViewerConfig } from "./types";

const CLS = "stx-app-media-viewer";

export class MermaidViewer {
  private config: MediaViewerConfig;

  constructor(config: MediaViewerConfig) {
    this.config = config;
  }

  async render(container: HTMLElement, filePath: string): Promise<void> {
    container.innerHTML = `<div class="${CLS}__loading">
      <i class="fas fa-spinner fa-spin"></i> Loading mermaid diagram...
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

      const { default: mermaid } = await import("mermaid");
      mermaid.initialize({
        startOnLoad: false,
        theme:
          document.documentElement.getAttribute("data-theme") === "dark"
            ? "dark"
            : "default",
        securityLevel: "loose",
      });

      const id = `mmd-${Date.now()}`;
      const wrapper = document.createElement("div");
      wrapper.className = `${CLS}__mermaid-wrapper`;
      wrapper.innerHTML = `<div class="mermaid" id="${id}">${code}</div>`;
      container.innerHTML = "";
      container.appendChild(wrapper);

      await mermaid.run({ nodes: [wrapper.querySelector(".mermaid")!] });
    } catch (err) {
      console.error("[MermaidViewer] Render error:", err);
      container.innerHTML = `
        <div class="${CLS}__error">
          <i class="fas fa-exclamation-triangle"></i>
          <p>Failed to render diagram: ${err instanceof Error ? err.message : String(err)}</p>
        </div>
      `;
    }
  }
}
