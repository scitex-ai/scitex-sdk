/**
 * KeyboardShortcuts — document-level keyboard shortcuts for the shell.
 *
 * Ported from scitex-cloud's ToolbarManager.attachKeyboardShortcuts().
 * Dispatches "stx-shell:command" CustomEvents (same as ToolbarManager).
 *
 * Supports:
 *  - Emacs chord sequences (C-x C-f, C-x C-s)
 *  - Standard shortcuts (Ctrl+S, Ctrl+Tab, Ctrl+Shift+T)
 *  - Keybinding mode switching (emacs/vim/default)
 */

import type { KeyShortcut, CommandEventDetail } from "./types";

interface EmacsChordState {
  ctrlXPressed: boolean;
  timeout: number | null;
}

/** Default keyboard shortcuts (matching scitex-cloud). */
const DEFAULT_SHORTCUTS: KeyShortcut[] = [
  // Universal
  { key: "s", ctrlKey: true, command: "save" },
  { key: "Tab", ctrlKey: true, command: "next-tab" },
  { key: "T", ctrlKey: true, shiftKey: true, command: "new-terminal" },
  { key: "PageDown", ctrlKey: true, command: "next-terminal" },
  { key: "PageUp", ctrlKey: true, command: "prev-terminal" },

  // Non-emacs only
  { key: "n", ctrlKey: true, command: "new-file", mode: "!emacs" },
];

/** Emacs chord definitions (C-x prefix). */
const EMACS_CHORDS: Array<{ key: string; command: string }> = [
  { key: "f", command: "new-file" }, // C-x C-f
  { key: "s", command: "save" }, // C-x C-s
];

export class KeyboardShortcuts {
  private shortcuts: KeyShortcut[];
  private emacsChord: EmacsChordState = { ctrlXPressed: false, timeout: null };
  private keybindingModeSelector: string;
  private boundHandler: (e: KeyboardEvent) => void;

  constructor(
    shortcuts: KeyShortcut[] = [],
    keybindingModeSelector: string = "keybinding-mode",
  ) {
    this.shortcuts = [...DEFAULT_SHORTCUTS, ...shortcuts];
    this.keybindingModeSelector = keybindingModeSelector;
    this.boundHandler = this.handleKeydown.bind(this);
  }

  /** Attach keyboard listeners. */
  init(): void {
    document.addEventListener("keydown", this.boundHandler, true);
    console.log("[KeyboardShortcuts] Listeners attached");
  }

  /** Remove keyboard listeners. */
  destroy(): void {
    document.removeEventListener("keydown", this.boundHandler, true);
  }

  private getKeybindingMode(): string {
    const el = document.getElementById(
      this.keybindingModeSelector,
    ) as HTMLSelectElement | null;
    return el?.value || "emacs";
  }

  private dispatch(command: string, data?: unknown): void {
    const detail: CommandEventDetail = { command, data };
    document.dispatchEvent(
      new CustomEvent("stx-shell:command", { detail, bubbles: true }),
    );
  }

  private handleKeydown(e: KeyboardEvent): void {
    const mode = this.getKeybindingMode();
    const isEmacs = mode === "emacs";

    // Emacs: C-x prefix
    if (isEmacs && e.ctrlKey && e.key === "x" && !e.shiftKey && !e.altKey) {
      e.preventDefault();
      e.stopPropagation();
      this.startEmacsChord();
      return;
    }

    // Emacs: C-x C-{key} chord completion
    if (isEmacs && this.emacsChord.ctrlXPressed && e.ctrlKey) {
      for (const chord of EMACS_CHORDS) {
        if (e.key === chord.key) {
          e.preventDefault();
          e.stopPropagation();
          this.clearEmacsChord();
          this.dispatch(chord.command);
          return;
        }
      }
      // Unknown chord key — cancel
      this.clearEmacsChord();
    }

    // Standard shortcuts
    for (const shortcut of this.shortcuts) {
      // Mode filter
      if (shortcut.mode === "!emacs" && isEmacs) continue;
      if (shortcut.mode && shortcut.mode !== "!emacs" && mode !== shortcut.mode)
        continue;

      if (
        e.key === shortcut.key &&
        !!e.ctrlKey === !!shortcut.ctrlKey &&
        !!e.shiftKey === !!shortcut.shiftKey &&
        !!e.altKey === !!shortcut.altKey
      ) {
        e.preventDefault();
        this.dispatch(shortcut.command);
        return;
      }
    }
  }

  private startEmacsChord(): void {
    this.emacsChord.ctrlXPressed = true;
    if (this.emacsChord.timeout) {
      window.clearTimeout(this.emacsChord.timeout);
    }
    this.emacsChord.timeout = window.setTimeout(() => {
      this.clearEmacsChord();
    }, 2000);
  }

  private clearEmacsChord(): void {
    this.emacsChord.ctrlXPressed = false;
    if (this.emacsChord.timeout) {
      window.clearTimeout(this.emacsChord.timeout);
      this.emacsChord.timeout = null;
    }
  }
}
