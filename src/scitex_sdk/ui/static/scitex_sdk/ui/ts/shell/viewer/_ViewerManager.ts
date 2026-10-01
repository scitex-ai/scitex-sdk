/**
 * ViewerManager - Coordinates tab management and file viewing.
 *
 * Ported from scitex-cloud's WorkspaceViewer (index.ts).
 * Uses ViewerAdapter for backend abstraction.
 *
 * Responsibilities:
 * - Open/close files via TabManager
 * - Route to text fallback or dedicated media viewer
 * - Manage show/hide of textContainer vs mediaContainer vs previewContainer
 * - Edit / Preview mode toggle for markdown files
 */

import { gettext } from "../../_base/gettext";
import { MarkdownPreviewPanel } from "./_MarkdownPreview";
import { TabManager } from "./_TabManager";
import { ViewerRouter } from "./_ViewerRouter";
import {
  detectFileType,
  detectShebang,
  FILENAME_LANGUAGE_MAP,
  LANGUAGE_MAP,
  type ViewerAdapter,
  type ViewerConfig,
  type OpenFile,
  type TabInfo,
} from "./types";

type ViewMode = "edit" | "preview";

/** Extensions that support edit + preview toggle */
const PREVIEWABLE_EXTENSIONS = new Set([
  ".md",
  ".mmd",
  ".mermaid",
  ".dot",
  ".gv",
  ".csv",
  ".tsv",
]);

function isPreviewable(filePath: string): boolean {
  const ext = filePath.substring(filePath.lastIndexOf(".")).toLowerCase();
  return PREVIEWABLE_EXTENSIONS.has(ext);
}

export class ViewerManager {
  private tabManager: TabManager;
  private router: ViewerRouter;
  private adapter: ViewerAdapter;
  private textContainer: HTMLElement;
  private mediaContainer: HTMLElement;
  private previewContainer: HTMLElement | null;
  private previewPanel: MarkdownPreviewPanel | null = null;
  private modeToggle: HTMLElement | null;
  private viewMode: ViewMode = "edit";
  private tabsContainer: HTMLElement;
  private config: ViewerConfig;
  private currentFile: string | null = null;

  constructor(config: ViewerConfig) {
    this.config = config;
    this.adapter = config.adapter;

    // Resolve containers
    const contentEl = document.getElementById("ws-viewer-content");
    const tabsEl = document.getElementById("ws-viewer-tabs");
    const textEl = document.getElementById("ws-viewer-monaco");
    const mediaEl = document.getElementById("ws-viewer-media");
    const previewEl = document.getElementById("ws-viewer-preview");
    const modeToggleEl = document.getElementById("ws-viewer-mode-toggle");

    if (!contentEl) {
      throw new Error("[ViewerManager] #ws-viewer-content not found");
    }

    this.tabsContainer = tabsEl || contentEl;
    this.textContainer = textEl || contentEl;
    this.mediaContainer = mediaEl || contentEl;
    this.previewContainer = previewEl ?? null;
    this.modeToggle = modeToggleEl ?? null;

    if (this.previewContainer) {
      this.previewPanel = new MarkdownPreviewPanel(this.previewContainer);
      this.previewPanel.setAdapter(this.adapter);
    }

    // Restore saved view mode
    const savedMode = localStorage.getItem("ws-viewer-mode") as ViewMode | null;
    if (savedMode && ["edit", "preview"].includes(savedMode)) {
      this.viewMode = savedMode;
    }

    this.initModeToggle();
    this.initDoubleClickToggle();
    this.router = new ViewerRouter();

    this.tabManager = new TabManager({
      container: this.tabsContainer,
      storageKey: "ws-viewer-tabs",
      onSwitch: (path) => this.handleTabSwitch(path),
      onClose: (path) => this.handleTabClose(path),
    });

    // Wire keyboard shortcuts button
    const shortcutsBtn = document.getElementById("ws-viewer-shortcuts-btn");
    shortcutsBtn?.addEventListener("click", () => {
      (window as any).toggleShortcutsModal?.();
    });

    // Listen for file-open events from file tree
    document.addEventListener("file-open", ((e: CustomEvent) => {
      const path = e.detail?.path;
      if (path) this.openFileFromTree(path);
    }) as EventListener);

    document.addEventListener("workspace-file-open", ((e: CustomEvent) => {
      const path = e.detail?.path;
      if (path) this.openFileFromTree(path);
    }) as EventListener);
  }

  async openFile(filePath: string): Promise<void> {
    const fileType = detectFileType(filePath);
    const title = filePath.split("/").pop() || filePath;
    const tabInfo: TabInfo = { path: filePath, title, fileType };
    this.tabManager.openTab(tabInfo);
    this.currentFile = filePath;
    await this.renderFile(filePath);
    this.updateActiveFileHint(filePath, fileType);

    this.config.onFileOpen?.({
      path: filePath,
      name: title,
      content: "",
      fileType,
    });
  }

  closeFile(filePath: string): void {
    this.tabManager.closeTab(filePath);
  }

  getCurrentFile(): string | null {
    return this.currentFile;
  }

  destroy(): void {
    this.router.destroyAll();
    this.currentFile = null;
  }

  /* ── Private ──────────────────────────────────── */

  private openFileFromTree(path: string): void {
    const sidebar = document.getElementById("ws-viewer-sidebar");

    // Toggle: if same file is already open, collapse
    const activeFile = sidebar?.dataset.aiViewerActive?.split(" (")[0] ?? "";
    const isCollapsed = sidebar?.classList.contains("collapsed");
    if (activeFile === path && !isCollapsed) {
      sidebar?.classList.add("collapsed");
      sidebar!.style.width = "";
      return;
    }

    // Hide empty state
    const emptyState = document.getElementById("ws-viewer-empty");
    if (emptyState) emptyState.style.display = "none";

    // Auto-expand viewer pane if collapsed
    if (sidebar?.classList.contains("collapsed")) {
      sidebar.classList.remove("collapsed");
      const savedWidth = localStorage.getItem("ws-viewer-width");
      sidebar.style.width = savedWidth ? `${savedWidth}px` : "480px";
    }

    void this.openFile(path);
  }

  private async handleTabSwitch(path: string): Promise<void> {
    await this.renderFile(path);
    this.updateActiveFileHint(path, detectFileType(path));
  }

  private handleTabClose(_path: string): void {
    if (!this.tabManager.getActiveTab()) {
      this.textContainer.style.display = "none";
      this.mediaContainer.style.display = "none";
      if (this.previewContainer) this.previewContainer.style.display = "none";
      this.updateActiveFileHint("", "text");
      this.currentFile = null;
      const emptyState = document.getElementById("ws-viewer-empty");
      if (emptyState) emptyState.style.display = "";
    }
  }

  private updateActiveFileHint(filePath: string, fileType: string): void {
    const sidebar = document.getElementById("ws-viewer-sidebar");
    if (sidebar) {
      sidebar.dataset.aiViewerActive = filePath
        ? `${filePath} (${fileType})`
        : "";
    }
  }

  private async renderFile(filePath: string): Promise<void> {
    const previewable = isPreviewable(filePath);
    const fileType = detectFileType(filePath);
    this.showModeToggle(previewable, fileType);

    // Hide empty state
    const emptyState = document.getElementById("ws-viewer-empty");
    if (emptyState) emptyState.style.display = "none";

    if (previewable && fileType !== "text") {
      if (this.viewMode === "edit") {
        await this.showTextFile(filePath);
      } else {
        await this.showMediaFile(filePath);
      }
      return;
    }

    if (fileType === "text") {
      await this.showTextFile(filePath);
    } else {
      await this.showMediaFile(filePath);
    }
  }

  private async showTextFile(filePath: string): Promise<void> {
    this.mediaContainer.style.display = "none";
    if (this.previewContainer) this.previewContainer.style.display = "none";
    this.textContainer.style.display = "block";
    this.textContainer.style.width = "100%";

    let content = "";
    try {
      const result = await this.adapter.readFile(filePath);
      content = result.content;
    } catch (err) {
      console.error("[ViewerManager] Failed to load file:", filePath, err);
      content = `// Error loading file: ${filePath}\n// ${err}`;
    }

    this.showFallbackPre(content, filePath);
  }

  private async showMediaFile(filePath: string): Promise<void> {
    this.textContainer.style.display = "none";
    if (this.previewContainer) this.previewContainer.style.display = "none";
    this.mediaContainer.style.display = "block";

    const viewer = this.router.getViewer(filePath);
    if (!viewer) {
      this.mediaContainer.innerHTML = `
        <div class="ws-viewer-placeholder">
          <p>Cannot preview: <code>${filePath.split("/").pop()}</code></p>
        </div>`;
      return;
    }
    try {
      await viewer.render(this.mediaContainer, filePath, this.adapter);
    } catch (err) {
      console.error("[ViewerManager] Viewer render error:", err);
      this.mediaContainer.innerHTML = `
        <div class="ws-viewer-placeholder">
          <p>Error rendering file: ${err instanceof Error ? err.message : String(err)}</p>
        </div>`;
    }
  }

  /* ── View mode toggle ──────────────────────────── */

  private initDoubleClickToggle(): void {
    const toggleIfPreviewable = () => {
      const active = this.tabManager.getActiveTab();
      if (!active) return;
      if (isPreviewable(active)) {
        this.setViewMode(this.viewMode === "edit" ? "preview" : "edit");
      }
    };

    let lastRightClick = 0;
    const handleRightDblClick = (e: MouseEvent) => {
      const now = Date.now();
      if (now - lastRightClick < 400) {
        e.preventDefault();
        e.stopPropagation();
        toggleIfPreviewable();
        lastRightClick = 0;
      } else {
        lastRightClick = now;
      }
    };
    this.textContainer.addEventListener(
      "contextmenu",
      handleRightDblClick,
      true,
    );
    this.mediaContainer.addEventListener(
      "contextmenu",
      handleRightDblClick,
      true,
    );
    if (this.previewContainer) {
      this.previewContainer.addEventListener(
        "contextmenu",
        handleRightDblClick,
        true,
      );
    }

    this.tabsContainer.addEventListener("dblclick", (e: MouseEvent) => {
      const tab = (e.target as HTMLElement).closest(".ws-viewer-tab");
      if (!tab) return;
      e.preventDefault();
      toggleIfPreviewable();
    });

    let lastTabRightClick = 0;
    this.tabsContainer.addEventListener("contextmenu", (e: MouseEvent) => {
      const tab = (e.target as HTMLElement).closest(".ws-viewer-tab");
      if (!tab) return;
      const now = Date.now();
      if (now - lastTabRightClick < 400) {
        e.preventDefault();
        e.stopPropagation();
        toggleIfPreviewable();
        lastTabRightClick = 0;
      } else {
        lastTabRightClick = now;
      }
    });
  }

  private initModeToggle(): void {
    if (!this.modeToggle) return;
    this.updateToggleIcon();

    const isTitle = this.modeToggle.classList.contains(
      "ws-viewer-mode-toggle-title",
    );

    if (isTitle) {
      let clickTimer: ReturnType<typeof setTimeout> | null = null;

      this.modeToggle.addEventListener("click", () => {
        if (clickTimer) clearTimeout(clickTimer);
        clickTimer = setTimeout(() => {
          this.setViewMode(this.viewMode === "edit" ? "preview" : "edit");
          clickTimer = null;
        }, 250);
      });

      this.modeToggle.addEventListener("dblclick", () => {
        if (clickTimer) {
          clearTimeout(clickTimer);
          clickTimer = null;
        }
        const toggleBtn = document.getElementById("ws-viewer-toggle");
        toggleBtn?.click();
      });
    } else {
      this.modeToggle.addEventListener("click", () => {
        this.setViewMode(this.viewMode === "edit" ? "preview" : "edit");
      });
    }
  }

  private setViewMode(mode: ViewMode): void {
    this.viewMode = mode;
    localStorage.setItem("ws-viewer-mode", mode);
    this.updateToggleIcon();
    const active = this.tabManager.getActiveTab();
    if (active && isPreviewable(active)) {
      this.applyViewMode(active);
    }
  }

  private updateToggleIcon(): void {
    if (!this.modeToggle) return;
    const isEdit = this.viewMode === "edit";
    const iconClass = isEdit ? "fas fa-eye" : "fas fa-pencil-alt";
    const label = " " + (isEdit ? gettext("Viewer") : gettext("Editor"));

    if (this.modeToggle.classList.contains("ws-viewer-mode-toggle-title")) {
      this.modeToggle.innerHTML = `<i class="${iconClass}"></i>${label}`;
    } else {
      const icon = this.modeToggle.querySelector("i");
      if (icon) icon.className = iconClass;
    }

    this.modeToggle.title = isEdit ? gettext("Switch to Editor") : gettext("Switch to Viewer");

    const shortTitle = document.getElementById("ws-viewer-title-short");
    if (shortTitle) {
      shortTitle.innerHTML = `<i class="${iconClass}"></i>${label}`;
      shortTitle.title = isEdit ? gettext("Viewer") : gettext("Editor");
    }
  }

  private showModeToggle(show: boolean, fileType?: string): void {
    if (!this.modeToggle) return;
    if (this.modeToggle.classList.contains("ws-viewer-mode-toggle-title")) {
      if (show) {
        this.modeToggle.style.cursor = "";
        this.updateToggleIcon();
      } else {
        const isEditor = fileType === "text";
        const iconClass = isEditor ? "fas fa-pencil-alt" : "fas fa-eye";
        const label = isEditor ? " Editor" : " Viewer";
        this.viewMode = isEditor ? "edit" : "preview";
        this.modeToggle.innerHTML = `<i class="${iconClass}"></i>${label}`;
        this.modeToggle.title = label.trim();
        this.modeToggle.style.cursor = "default";
        const shortTitle = document.getElementById("ws-viewer-title-short");
        if (shortTitle) {
          shortTitle.innerHTML = `<i class="${iconClass}"></i>${label}`;
          shortTitle.title = label.trim();
        }
      }
    } else {
      this.modeToggle.style.display = show ? "inline-flex" : "none";
    }
  }

  private async applyViewMode(filePath?: string): Promise<void> {
    const active = filePath || this.tabManager.getActiveTab() || "";
    const isMd = active.endsWith(".md");
    const hasPreview = !!this.previewContainer && !!this.previewPanel;

    if (this.viewMode === "edit") {
      this.mediaContainer.style.display = "none";
      if (this.previewContainer) this.previewContainer.style.display = "none";
      this.textContainer.style.display = "block";
      this.textContainer.style.width = "100%";
      if (!isMd && active) {
        await this.showTextFile(active);
      }
    } else {
      this.textContainer.style.display = "none";
      if (isMd && hasPreview) {
        this.mediaContainer.style.display = "none";
        this.previewContainer!.style.display = "block";
        this.previewContainer!.style.width = "100%";
        // Re-read file for preview
        try {
          const result = await this.adapter.readFile(active);
          this.previewPanel!.render(result.content);
        } catch (err) {
          console.error("[ViewerManager] Failed to load for preview:", err);
        }
      } else if (active) {
        if (this.previewContainer) this.previewContainer.style.display = "none";
        await this.showMediaFile(active);
      }
    }
  }

  /* ── Text fallback (no Monaco — uses <pre>) ──── */

  private showFallbackPre(content: string, filePath: string): void {
    this.textContainer.innerHTML = "";
    const ext = filePath.substring(filePath.lastIndexOf(".")).toLowerCase();
    const filename = filePath.split("/").pop()?.toLowerCase() ?? "";
    const language =
      LANGUAGE_MAP[ext] ??
      FILENAME_LANGUAGE_MAP[filename] ??
      detectShebang(content) ??
      "plaintext";

    const pre = document.createElement("pre");
    pre.className = "ws-viewer-fallback-pre";
    pre.style.cssText =
      "margin:0;padding:12px 16px;font-family:'JetBrains Mono',Monaco,Menlo,monospace;font-size:13px;line-height:1.5;color:var(--text-primary,#c9d1d9);background:var(--bg-primary,#0d1117);white-space:pre-wrap;word-wrap:break-word;overflow:auto;height:100%;";
    const code = document.createElement("code");
    if (language !== "plaintext") code.className = `language-${language}`;
    code.textContent = content;
    pre.appendChild(code);
    this.textContainer.appendChild(pre);

    // Highlight if hljs is available
    const hljs = (window as any).hljs;
    if (hljs) hljs.highlightElement(code);
  }
}
