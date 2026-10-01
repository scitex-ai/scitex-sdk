/**
 * MonacoEditor — scitex-ui
 * Reusable Monaco editor component extending BaseComponent.
 * Handles init, themes, language detection, and keybinding modes.
 */

import { BaseComponent } from "../../_base/BaseComponent";
import type { MonacoEditorConfig } from "./types";
import { detectLanguage } from "./types";
import { MONACO_EDITOR_DEFAULTS } from "./_MonacoDefaults";
import {
  initializeMonacoThemes,
  setupMonacoThemeObserver,
  getCurrentThemeMode,
  getThemeForMode,
} from "./_MonacoTheme";
import { setKeybindingMode } from "./_MonacoKeybindings";
import { waitForMonaco } from "./_MonacoLoader";

export class MonacoEditor extends BaseComponent<MonacoEditorConfig> {
  private editor: any = null;
  private monacoInstance: any = null;

  constructor(config: MonacoEditorConfig) {
    super(config);
  }

  async initialize(): Promise<void> {
    this.monacoInstance = await waitForMonaco();
    const monaco = this.monacoInstance;

    // Register themes and auto-switch observer
    initializeMonacoThemes(monaco);
    setupMonacoThemeObserver(monaco);

    // Determine initial theme
    const theme = this.config.theme || getThemeForMode(getCurrentThemeMode());

    // Create editor with shared defaults + config overrides
    this.editor = monaco.editor.create(this.container, {
      ...MONACO_EDITOR_DEFAULTS,
      value: this.config.value || "",
      language: this.config.language || "plaintext",
      theme,
      readOnly: this.config.readOnly ?? false,
      fontSize: this.config.fontSize ?? MONACO_EDITOR_DEFAULTS.fontSize,
      tabSize: this.config.tabSize ?? MONACO_EDITOR_DEFAULTS.tabSize,
      minimap: { enabled: this.config.minimap ?? true },
      lineNumbers: this.config.lineNumbers ?? "on",
      wordWrap: this.config.wordWrap ?? "on",
    });

    // Apply keybinding mode
    const mode =
      this.config.keybindingMode ||
      (localStorage.getItem("scitex-keybinding-mode") as any) ||
      "emacs";
    setKeybindingMode(this.editor, monaco, mode);

    this.emit("monaco-editor:initialized", { editor: this.editor });
  }

  getEditor(): any {
    return this.editor;
  }

  getMonaco(): any {
    return this.monacoInstance;
  }

  setValue(content: string): void {
    if (this.editor) {
      this.editor.setValue(content);
    }
  }

  getValue(): string {
    return this.editor ? this.editor.getValue() : "";
  }

  setLanguage(language: string): void {
    if (this.editor && this.monacoInstance) {
      const model = this.editor.getModel();
      if (model) {
        this.monacoInstance.editor.setModelLanguage(model, language);
      }
    }
  }

  detectLanguage(filePath: string, content?: string): string {
    return detectLanguage(filePath, content);
  }

  updateTheme(theme: "dark" | "light"): void {
    if (this.editor && this.monacoInstance) {
      const monacoTheme = getThemeForMode(theme);
      this.editor.updateOptions({ theme: monacoTheme });
    }
  }

  toggleTheme(): void {
    if (!this.editor || !this.monacoInstance) return;
    const current = this.getCurrentTheme();
    const isDark = current === "scitex-dark" || current === "vs-dark";
    const next = isDark ? "scitex-light" : "scitex-dark";
    this.editor.updateOptions({ theme: next });
  }

  getCurrentTheme(): string {
    if (!this.editor || !this.monacoInstance) return "scitex-dark";
    return this.editor.getOption(this.monacoInstance.editor.EditorOption.theme);
  }

  setKeybindingMode(mode: "emacs" | "vim" | "vscode"): void {
    if (this.editor && this.monacoInstance) {
      setKeybindingMode(this.editor, this.monacoInstance, mode);
    }
  }

  addKeybinding(keyMod: number, keyCode: number, handler: () => void): void {
    if (this.editor) {
      this.editor.addCommand(keyMod | keyCode, handler);
    }
  }

  setReadOnly(readOnly: boolean): void {
    if (this.editor) {
      this.editor.updateOptions({ readOnly });
    }
  }

  focus(): void {
    if (this.editor) {
      this.editor.focus();
    }
  }

  destroy(): void {
    if (this.editor) {
      this.editor.dispose();
      this.editor = null;
    }
    this.monacoInstance = null;
    super.destroy();
  }
}
