/**
 * GraphvizViewer - Fetches .dot/.gv file content and renders as Graphviz.
 *
 * Ported from scitex-cloud's workspace-viewer/viewers/GraphvizViewer.ts.
 * Uses ViewerAdapter for file content fetching.
 */

import type { Viewer, ViewerAdapter } from "./types";

export class GraphvizViewer implements Viewer {
  private abortController: AbortController | null = null;

  async render(
    container: HTMLElement,
    filePath: string,
    adapter: ViewerAdapter,
  ): Promise<void> {
    container.innerHTML =
      '<div style="color:#888; padding:10px;">Loading diagram...</div>';
    this.abortController = new AbortController();

    let code: string;
    try {
      const result = await adapter.readFile(filePath);
      code = (result.content ?? "").trim();
    } catch (err: any) {
      if (err.name === "AbortError") return;
      container.innerHTML = `<div style="color:#e55; padding:10px;">Failed to load: ${filePath}</div>`;
      return;
    }

    if (!code) {
      container.innerHTML =
        '<div style="color:#888; padding:10px;">Empty diagram file</div>';
      return;
    }

    try {
      const { Graphviz } = await import("@hpcc-js/wasm-graphviz");
      const graphviz = await Graphviz.load();
      const svg = graphviz.dot(code);

      const wrapper = document.createElement("div");
      wrapper.style.cssText = "padding:16px; overflow:auto; height:100%;";
      wrapper.innerHTML = svg;

      container.innerHTML = "";
      container.appendChild(wrapper);
    } catch (err) {
      console.error("[GraphvizViewer] Render error:", err);
      container.innerHTML = `
        <div style="color:#e55; padding:10px;">
          Failed to render diagram: ${err instanceof Error ? err.message : String(err)}
        </div>
      `;
    }
  }

  destroy(): void {
    this.abortController?.abort();
    this.abortController = null;
  }
}
