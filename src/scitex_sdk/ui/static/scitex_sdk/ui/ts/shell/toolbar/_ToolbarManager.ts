/**
 * ToolbarManager — wires toolbar buttons to shell commands via CustomEvents.
 *
 * Ported from scitex-cloud's ToolbarManager.ts but decoupled from
 * concrete manager classes. Instead of calling methods directly,
 * dispatches "stx-shell:command" CustomEvents that consumers handle.
 *
 * Usage:
 *   import { ToolbarManager } from "scitex-ui/ts/shell/toolbar";
 *   const toolbar = new ToolbarManager();
 *   toolbar.init();
 *
 *   // App registers handlers:
 *   document.addEventListener("stx-shell:command", (e) => {
 *     if (e.detail.command === "save") saveCurrentFile();
 *   });
 */

import type { ToolbarConfig, ButtonBinding, CommandEventDetail } from "./types";

/** Default button bindings (matching scitex-cloud button IDs). */
const DEFAULT_BUTTONS: ButtonBinding[] = [
  { elementId: "btn-save", command: "save" },
  { elementId: "btn-delete", command: "delete" },
  { elementId: "btn-commit", command: "commit" },
  { elementId: "btn-run", command: "run" },
  { elementId: "monaco-theme-toggle", command: "theme-toggle" },
  { elementId: "btn-editor-shortcuts", command: "shortcuts-editor" },
  { elementId: "btn-terminal-shortcuts", command: "shortcuts-terminal" },
  { elementId: "btn-copy-terminal", command: "copy-terminal" },
];

export class ToolbarManager {
  private config: ToolbarConfig;
  private handlers: Map<string, (data?: unknown) => void> = new Map();

  constructor(config: ToolbarConfig = {}) {
    this.config = config;
  }

  /** Initialize all button and keyboard bindings. */
  init(): void {
    this.attachButtons();
    console.log("[ToolbarManager] Buttons attached");
  }

  /**
   * Register a command handler directly (alternative to listening for events).
   * If a handler is registered, the command is handled directly instead of
   * dispatching a CustomEvent.
   */
  registerCommand(command: string, handler: (data?: unknown) => void): void {
    this.handlers.set(command, handler);
  }

  /** Dispatch a command (used internally and can be called externally). */
  dispatch(command: string, data?: unknown): void {
    const handler = this.handlers.get(command);
    if (handler) {
      handler(data);
      return;
    }

    const detail: CommandEventDetail = { command, data };
    document.dispatchEvent(
      new CustomEvent("stx-shell:command", { detail, bubbles: true }),
    );
  }

  private attachButtons(): void {
    const bindings = [...DEFAULT_BUTTONS, ...(this.config.buttons ?? [])];

    for (const binding of bindings) {
      const el = document.getElementById(binding.elementId);
      if (!el) continue;

      el.addEventListener("click", () => {
        this.dispatch(binding.command, binding.data);
      });
    }
  }
}
