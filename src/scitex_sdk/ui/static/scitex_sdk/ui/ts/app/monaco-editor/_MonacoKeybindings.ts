/**
 * Monaco Keybindings — scitex-ui
 * Generic editor keybindings (Emacs cursor movement).
 * App-specific shortcuts (navigation, run-code) stay in consuming apps.
 */

/**
 * Add Emacs-style cursor keybindings to a Monaco editor.
 * Ctrl+F/B/N/P/A/E for navigation, Alt+F/B for word movement.
 */
export function addEmacsKeybindings(editor: any, monaco: any): void {
  if (!editor) return;

  // Prevent Chrome from intercepting Ctrl+N/P/W/T/Y when editor is focused
  const preventDefaultForEmacs = (e: KeyboardEvent) => {
    const active = document.activeElement;
    const inEditor =
      active?.classList?.contains("inputarea") ||
      active?.closest(".monaco-editor") !== null;
    if (!inEditor) return;

    if (e.ctrlKey && !e.shiftKey && !e.altKey && !e.metaKey) {
      const key = e.key.toLowerCase();
      if (["n", "p", "w", "t", "y"].includes(key)) {
        e.preventDefault();
      }
    }
  };

  document.addEventListener("keydown", preventDefaultForEmacs, true);
  (editor as any)._emacsPreventDefaultHandler = preventDefaultForEmacs;

  // Character navigation
  editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyF, () => {
    editor.trigger("keyboard", "cursorRight", {});
  });
  editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyB, () => {
    editor.trigger("keyboard", "cursorLeft", {});
  });
  editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyN, () => {
    editor.trigger("keyboard", "cursorDown", {});
  });
  editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyP, () => {
    editor.trigger("keyboard", "cursorUp", {});
  });

  // Alt fallbacks for Chrome-blocked keys
  editor.addCommand(monaco.KeyMod.Alt | monaco.KeyCode.KeyN, () => {
    editor.trigger("keyboard", "cursorDown", {});
  });
  editor.addCommand(monaco.KeyMod.Alt | monaco.KeyCode.KeyP, () => {
    editor.trigger("keyboard", "cursorUp", {});
  });

  // Word navigation
  editor.addCommand(monaco.KeyMod.Alt | monaco.KeyCode.KeyF, () => {
    editor.trigger("keyboard", "cursorWordRight", {});
  });
  editor.addCommand(monaco.KeyMod.Alt | monaco.KeyCode.KeyB, () => {
    editor.trigger("keyboard", "cursorWordLeft", {});
  });

  // Line beginning/end
  editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyA, () => {
    editor.trigger("keyboard", "cursorHome", {});
  });
  editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyE, () => {
    editor.trigger("keyboard", "cursorEnd", {});
  });
}

/**
 * Remove Emacs event listener if previously installed.
 */
export function removeEmacsKeybindings(editor: any): void {
  if ((editor as any)?._emacsPreventDefaultHandler) {
    document.removeEventListener(
      "keydown",
      (editor as any)._emacsPreventDefaultHandler,
      true,
    );
    (editor as any)._emacsPreventDefaultHandler = null;
  }
}

/**
 * Set keybinding mode on an editor instance.
 */
export function setKeybindingMode(
  editor: any,
  monaco: any,
  mode: "emacs" | "vim" | "vscode",
): void {
  if (!editor) return;

  // Clean up previous emacs handler
  removeEmacsKeybindings(editor);

  // Clear dynamic keybindings
  if ((editor as any)._standaloneKeybindingService) {
    (editor as any)._standaloneKeybindingService._dynamicKeybindings = [];
  }

  if (mode === "emacs") {
    addEmacsKeybindings(editor, monaco);
  }
  // vim mode would require monaco-vim extension
  // vscode mode is the default — no extra keybindings needed

  localStorage.setItem("scitex-keybinding-mode", mode);
}
