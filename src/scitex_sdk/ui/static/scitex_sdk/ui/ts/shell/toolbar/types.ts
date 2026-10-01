/**
 * Shell toolbar types — command registry for decoupled button/shortcut wiring.
 *
 * Commands are dispatched as CustomEvents on `document`:
 *   document.addEventListener("stx-shell:command", (e) => {
 *     console.log(e.detail.command, e.detail.data);
 *   });
 */

/** Built-in toolbar commands. Apps can extend with custom strings. */
export type ToolbarCommand =
  | "save"
  | "delete"
  | "commit"
  | "run"
  | "new-file"
  | "new-folder"
  | "rename"
  | "theme-toggle"
  | "next-tab"
  | "prev-tab"
  | "new-terminal"
  | "next-terminal"
  | "prev-terminal"
  | "shortcuts-editor"
  | "shortcuts-terminal"
  | "copy-terminal"
  | (string & {}); // Allow custom commands

/** Payload for the stx-shell:command CustomEvent. */
export interface CommandEventDetail {
  command: ToolbarCommand;
  data?: unknown;
}

/** Button-to-command mapping. */
export interface ButtonBinding {
  /** DOM element ID (e.g., "btn-save") */
  elementId: string;
  /** Command to dispatch on click */
  command: ToolbarCommand;
  /** Optional data to include in the event */
  data?: unknown;
}

/** Keyboard shortcut definition. */
export interface KeyShortcut {
  /** Key (e.g., "s", "Tab", "PageDown") */
  key: string;
  ctrlKey?: boolean;
  shiftKey?: boolean;
  altKey?: boolean;
  /** Command to dispatch */
  command: ToolbarCommand;
  /** Only active in this keybinding mode (e.g., "emacs"). Null = always active. */
  mode?: string | null;
}

export interface ToolbarConfig {
  /** Additional button bindings beyond defaults. */
  buttons?: ButtonBinding[];
  /** Additional keyboard shortcuts beyond defaults. */
  shortcuts?: KeyShortcut[];
  /** Default keybinding mode (default: "emacs"). */
  keybindingMode?: string;
  /** ID of keybinding mode selector element (default: "keybinding-mode"). */
  keybindingModeSelector?: string;
}
