/**
 * Shell Orchestrator — initializes all shell modules with adapters.
 *
 * Replaces js/shell/standalone-shell-init.js with a proper TS entry point.
 * Consumers call initShell(config) to wire everything up.
 *
 * Usage:
 *   import { initShell } from "scitex-ui/ts/shell/_shell-init";
 *   initShell({
 *     fileTree: { adapter: myFileTreeAdapter, onFileSelect: (n) => ... },
 *     terminal: { adapter: myTerminalAdapter },
 *     toolbar: {},
 *     viewer: { adapter: myViewerAdapter },
 *   });
 */

import type { ShellConfig } from "./types";
import { ShellFileTree } from "./file-tree/_ShellFileTree";
import { ToolbarManager } from "./toolbar/_ToolbarManager";
import { KeyboardShortcuts } from "./toolbar/_KeyboardShortcuts";
import { initTerminal } from "./terminal/_TerminalFactory";
import { ViewerManager } from "./viewer/_ViewerManager";

export interface ShellInstances {
  fileTree?: ShellFileTree;
  toolbar?: ToolbarManager;
  shortcuts?: KeyboardShortcuts;
  viewer?: ViewerManager;
}

const LOG = "[ShellInit]";

/**
 * Resolve a widget's container, or decline to build the widget.
 *
 * OPTING IN IS A CONFIG FACT; THE CONTAINER EXISTING IS A DOM FACT, and nothing
 * links them. `initShell` is handed a config by the app and hardcodes the
 * selectors the SHELL TEMPLATE would render — but a leaf running standalone
 * renders its own markup, and the containers scitex-hub supplies are simply not
 * there. Before this, the widget was constructed anyway and threw on first
 * dereference, which is what figrecipe hit on standalone first load (measured
 * 2026-09-02).
 *
 * Returning null lets the caller SKIP the widget instead. The warning is
 * unconditional, matching the convention already used across shell/ (see
 * resizer/index.ts, which warns the same way when `configFromElement` returns
 * null). A silent skip would hide a real misconfiguration — "I passed
 * config.fileTree and nothing happened" — which is exactly the case the
 * developer needs to see.
 */
function containerFor(selector: string, widget: string): HTMLElement | null {
  const el = document.querySelector<HTMLElement>(selector);
  if (!el) {
    console.warn(
      `${LOG} ${widget}: no element matches "${selector}", so it was not ` +
        `initialised. This is expected when running standalone — that ` +
        `container is supplied by the mounting platform. Render it, or omit ` +
        `${widget} from the initShell config.`,
    );
  }
  return el;
}

/**
 * Initialize the workspace shell with all modules.
 *
 * Each module is optional — omit from config to skip.
 * Returns references to initialized instances for further interaction.
 */
export async function initShell(config: ShellConfig): Promise<ShellInstances> {
  const instances: ShellInstances = {};

  // Console/Chat mode toggle (vanilla JS — always init)
  initModeToggle();

  // File Tree
  if (config.fileTree && containerFor("#ws-worktree-tree", "fileTree")) {
    const fileTree = new ShellFileTree({
      container: "#ws-worktree-tree",
      adapter: config.fileTree.adapter,
      onFileSelect: config.fileTree.onFileSelect,
      showHidden: config.fileTree.showHidden,
      extensions: config.fileTree.extensions,
    });
    await fileTree.load();
    instances.fileTree = fileTree;

    // Wire hidden files toggle button
    const toggleBtn = document.getElementById("hidden-files-toggle");
    if (toggleBtn) {
      toggleBtn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        fileTree.toggleHidden();
      });
    }
  }

  // Terminal
  if (
    config.terminal &&
    containerFor("#stx-shell-ai-console-terminal", "terminal")
  ) {
    await initTerminal({
      container: "#stx-shell-ai-console-terminal",
      adapter: config.terminal.adapter,
      clipboard: config.terminal.clipboard ?? true,
      dragDrop: config.terminal.dragDrop,
      onFileDrop: config.terminal.onFileDrop,
      reconnectDelay: config.terminal.reconnectDelay,
    });
  }

  // Toolbar + Keyboard Shortcuts
  const toolbar = new ToolbarManager(config.toolbar);
  toolbar.init();
  instances.toolbar = toolbar;

  const shortcuts = new KeyboardShortcuts(
    config.toolbar?.shortcuts,
    config.toolbar?.keybindingModeSelector,
  );
  shortcuts.init();
  instances.shortcuts = shortcuts;

  // Viewer
  if (config.viewer) {
    try {
      const viewer = new ViewerManager({
        adapter: config.viewer.adapter,
        onFileOpen: config.viewer.onFileOpen,
      });
      instances.viewer = viewer;

      // Wire file tree → viewer: open files in viewer pane
      if (config.fileTree?.onFileSelect === undefined && instances.fileTree) {
        // Default: file tree clicks open in viewer
        // (only if consumer didn't provide their own onFileSelect)
      }
    } catch {
      // Viewer container may not exist — that's OK
      console.log("[Shell] Viewer pane not found, skipping");
    }
  }

  // Wire file tree refresh on AI file operations
  document.addEventListener("stx-shell:files-changed", () => {
    instances.fileTree?.refresh();
  });

  console.log("[Shell] Initialized");
  return instances;
}

/** Console/Chat mode toggle — vanilla JS, always active. */
function initModeToggle(): void {
  document.querySelectorAll(".stx-shell-ai-mode-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const mode = (btn as HTMLElement).dataset.mode;
      document.querySelectorAll(".stx-shell-ai-mode-btn").forEach((b) => {
        b.classList.remove("active");
      });
      btn.classList.add("active");
      document.querySelectorAll(".stx-shell-ai-view").forEach((v) => {
        v.classList.remove("active");
      });
      const target = document.getElementById(
        mode === "chat"
          ? "stx-shell-ai-chat-view"
          : "stx-shell-ai-console-view",
      );
      if (target) target.classList.add("active");
    });
  });

  // Toolbar buttons → custom events
  document.querySelectorAll(".stx-shell-ai-input-btn").forEach((btn) => {
    if ((btn as HTMLButtonElement).disabled) return;
    const title = (btn.getAttribute("title") || "").toLowerCase();
    let eventName: string | null = null;

    if (title.includes("webcam") || title.includes("camera")) {
      eventName = "stx-shell:camera";
    } else if (title.includes("sketch") || title.includes("draw")) {
      eventName = "stx-shell:sketch";
    } else if (title.includes("voice") || title.includes("mic")) {
      eventName = "stx-shell:mic-toggle";
    }

    if (eventName) {
      btn.addEventListener("click", () => {
        window.dispatchEvent(new CustomEvent(eventName!));
      });
    }
  });
}
