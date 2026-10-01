/**
 * AjaxLoader — fetches pages and injects content without full reload.
 *
 * Usage:
 *   const loader = new AjaxLoader({
 *     containerSelector: "#main-content",
 *     linkSelector: "[data-ajax-load]",
 *   });
 *   loader.init();
 */

import type { AjaxLoaderOptions } from "./types";

export class AjaxLoader {
  private opts: Required<AjaxLoaderOptions>;

  constructor(options: AjaxLoaderOptions) {
    this.opts = {
      headerName: "X-Workspace-Shell",
      headerValue: "1",
      pushState: true,
      onLoad: () => {},
      onError: () => {},
      ...options,
    };
  }

  /** Initialize delegated click handler for AJAX links */
  init(): void {
    document.addEventListener("click", (e) => {
      const link = (e.target as HTMLElement).closest<HTMLElement>(
        this.opts.linkSelector,
      );
      if (!link) return;

      e.preventDefault();
      const url =
        link.getAttribute("data-ajax-load") || link.getAttribute("href");
      if (!url) return;

      void this.load(url);
    });
  }

  /** Fetch a page via AJAX and inject its content */
  async load(url: string): Promise<void> {
    const container = document.querySelector<HTMLElement>(
      this.opts.containerSelector,
    );
    if (!container) return;

    try {
      const resp = await fetch(url, {
        headers: { [this.opts.headerName]: this.opts.headerValue },
        credentials: "same-origin",
      });

      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

      const html = await resp.text();

      // If response is a partial (no <html> tag), use directly
      if (!html.includes("<!DOCTYPE") && !html.includes("<html")) {
        container.innerHTML = html;
      } else {
        // Extract content from full page
        const doc = new DOMParser().parseFromString(html, "text/html");
        const content =
          doc.querySelector(this.opts.containerSelector) ||
          doc.querySelector("main") ||
          doc.body;
        container.innerHTML = content?.innerHTML || html;
      }

      // Re-execute inline scripts
      container.querySelectorAll("script").forEach((old) => {
        if (old.type === "importmap") {
          old.remove();
          return;
        }
        const replacement = document.createElement("script");
        Array.from(old.attributes).forEach((attr) =>
          replacement.setAttribute(attr.name, attr.value),
        );
        replacement.textContent = old.textContent;
        old.replaceWith(replacement);
      });

      if (this.opts.pushState) {
        history.pushState({ page: url }, "", url);
      }

      this.opts.onLoad(url, container);
    } catch (err) {
      console.error("[AjaxLoader] Failed to load:", url, err);
      this.opts.onError(url, err as Error);
      // Fallback: navigate normally
      location.href = url;
    }
  }
}
