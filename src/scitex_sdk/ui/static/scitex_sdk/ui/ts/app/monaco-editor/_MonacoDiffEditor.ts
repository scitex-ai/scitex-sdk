/**
 * MonacoDiffEditor — scitex-ui
 * Side-by-side or inline diff visualization using Monaco's diff editor.
 * Supports hunk navigation, accept/reject per hunk, and change highlighting.
 */

import { BaseComponent } from "../../_base/BaseComponent";
import type { MonacoDiffEditorConfig, DiffHunk } from "./types";
import { detectLanguage } from "./types";
import { MONACO_EDITOR_DEFAULTS } from "./_MonacoDefaults";
import {
  initializeMonacoThemes,
  setupMonacoThemeObserver,
  getCurrentThemeMode,
  getThemeForMode,
} from "./_MonacoTheme";
import { waitForMonaco } from "./_MonacoLoader";

export class MonacoDiffEditor extends BaseComponent<MonacoDiffEditorConfig> {
  private diffEditor: any = null;
  private monacoInstance: any = null;
  private originalModel: any = null;
  private modifiedModel: any = null;

  private hunks: DiffHunk[] = [];
  private currentHunkIndex: number = -1;
  private toolbarEl: HTMLElement | null = null;
  private hunkDecorations: string[] = [];

  constructor(config: MonacoDiffEditorConfig) {
    super(config);
  }

  async initialize(): Promise<void> {
    this.monacoInstance = await waitForMonaco();
    const monaco = this.monacoInstance;

    initializeMonacoThemes(monaco);
    setupMonacoThemeObserver(monaco);

    const theme = this.config.theme || getThemeForMode(getCurrentThemeMode());

    // Auto-detect language from filePath when language is not explicitly set
    const language =
      this.config.language ||
      (this.config.filePath
        ? detectLanguage(this.config.filePath, this.config.modified)
        : "plaintext");

    // Build wrapper: optional toolbar + editor container
    const editorContainer = this.buildLayout();

    this.diffEditor = monaco.editor.createDiffEditor(editorContainer, {
      automaticLayout: MONACO_EDITOR_DEFAULTS.automaticLayout,
      fontSize: MONACO_EDITOR_DEFAULTS.fontSize,
      fontFamily: MONACO_EDITOR_DEFAULTS.fontFamily,
      readOnly: this.config.readOnly ?? true,
      theme,
      renderSideBySide: this.config.renderSideBySide ?? true,
      scrollBeyondLastLine: false,
      minimap: { enabled: false },
      glyphMargin: true,
      folding: true,
    });

    // Create models
    this.originalModel = monaco.editor.createModel(
      this.config.original || "",
      language,
    );
    this.modifiedModel = monaco.editor.createModel(
      this.config.modified || "",
      language,
    );

    this.diffEditor.setModel({
      original: this.originalModel,
      modified: this.modifiedModel,
    });

    // Wait for diff computation, then extract hunks
    this.diffEditor.onDidUpdateDiff(() => {
      this.extractHunks();
      this.highlightCurrentHunk();
      this.updateToolbarState();
    });

    this.emit("monaco-diff-editor:initialized", {
      diffEditor: this.diffEditor,
    });
  }

  // ── Layout ──────────────────────────────────────────────────────────

  /**
   * Build the internal DOM: optional toolbar above the editor container.
   * Returns the element that Monaco should mount into.
   */
  private buildLayout(): HTMLElement {
    const showToolbar =
      this.config.enableHunkNavigation || this.config.enableHunkActions;

    if (showToolbar) {
      this.container.style.display = "flex";
      this.container.style.flexDirection = "column";

      this.toolbarEl = document.createElement("div");
      this.toolbarEl.className = "monaco-diff-toolbar";
      this.toolbarEl.style.cssText =
        "display:flex;align-items:center;gap:8px;padding:6px 12px;" +
        "border-bottom:1px solid var(--color-border-default,#30363d);" +
        "background:var(--color-canvas-subtle,#161b22);" +
        "font-size:12px;flex-shrink:0;";
      this.buildToolbarButtons();
      this.container.appendChild(this.toolbarEl);
    }

    const editorContainer = document.createElement("div");
    editorContainer.style.cssText = "flex:1;min-height:0;";
    this.container.appendChild(editorContainer);
    return editorContainer;
  }

  private buildToolbarButtons(): void {
    if (!this.toolbarEl) return;

    if (this.config.enableHunkNavigation) {
      // Hunk counter
      const counter = document.createElement("span");
      counter.className = "diff-hunk-counter";
      counter.style.cssText = "color:var(--color-fg-muted,#8b949e);";
      counter.textContent = "No changes";
      this.toolbarEl.appendChild(counter);

      // Previous hunk
      const prevBtn = this.createToolbarButton(
        "diff-prev-hunk",
        "\u2191 Prev",
        "Navigate to previous change",
        () => this.goToPreviousHunk(),
      );
      this.toolbarEl.appendChild(prevBtn);

      // Next hunk
      const nextBtn = this.createToolbarButton(
        "diff-next-hunk",
        "\u2193 Next",
        "Navigate to next change",
        () => this.goToNextHunk(),
      );
      this.toolbarEl.appendChild(nextBtn);
    }

    if (this.config.enableHunkActions) {
      // Spacer
      const spacer = document.createElement("span");
      spacer.style.cssText = "flex:1;";
      this.toolbarEl.appendChild(spacer);

      // Accept hunk
      const acceptBtn = this.createToolbarButton(
        "diff-accept-hunk",
        "Accept",
        "Apply this change to the original",
        () => this.acceptCurrentHunk(),
      );
      acceptBtn.style.color = "#2da44e";
      this.toolbarEl.appendChild(acceptBtn);

      // Reject hunk
      const rejectBtn = this.createToolbarButton(
        "diff-reject-hunk",
        "Reject",
        "Revert this change in the modified",
        () => this.rejectCurrentHunk(),
      );
      rejectBtn.style.color = "#cf222e";
      this.toolbarEl.appendChild(rejectBtn);
    }
  }

  private createToolbarButton(
    className: string,
    label: string,
    title: string,
    onClick: () => void,
  ): HTMLButtonElement {
    const btn = document.createElement("button");
    btn.className = className;
    btn.textContent = label;
    btn.title = title;
    btn.disabled = true;
    btn.style.cssText =
      "background:none;border:1px solid var(--color-border-default,#30363d);" +
      "border-radius:4px;padding:2px 10px;cursor:pointer;" +
      "color:var(--color-fg-default,#e6edf3);font-size:12px;" +
      "transition:opacity 0.15s;";
    btn.addEventListener("click", onClick);
    return btn;
  }

  // ── Hunk extraction ─────────────────────────────────────────────────

  private extractHunks(): void {
    if (!this.diffEditor) {
      this.hunks = [];
      return;
    }

    const lineChanges = this.diffEditor.getLineChanges();
    if (!lineChanges || lineChanges.length === 0) {
      this.hunks = [];
      return;
    }

    this.hunks = lineChanges.map((change: any, idx: number) => {
      const origStart = change.originalStartLineNumber;
      const origEnd = change.originalEndLineNumber;
      const modStart = change.modifiedStartLineNumber;
      const modEnd = change.modifiedEndLineNumber;

      return {
        index: idx,
        originalStartLine: origStart,
        originalEndLine: origEnd,
        modifiedStartLine: modStart,
        modifiedEndLine: modEnd,
        originalText: this.getModelText(this.originalModel, origStart, origEnd),
        modifiedText: this.getModelText(this.modifiedModel, modStart, modEnd),
      } as DiffHunk;
    });

    // Auto-select first hunk if none selected
    if (this.hunks.length > 0 && this.currentHunkIndex < 0) {
      this.currentHunkIndex = 0;
    }
  }

  private getModelText(model: any, startLine: number, endLine: number): string {
    if (!model || endLine < startLine || startLine === 0) return "";
    const range = {
      startLineNumber: startLine,
      startColumn: 1,
      endLineNumber: endLine,
      endColumn: model.getLineMaxColumn(endLine),
    };
    return model.getValueInRange(range);
  }

  // ── Hunk navigation ─────────────────────────────────────────────────

  getHunks(): DiffHunk[] {
    return this.hunks;
  }

  getHunkCount(): number {
    return this.hunks.length;
  }

  getCurrentHunkIndex(): number {
    return this.currentHunkIndex;
  }

  goToNextHunk(): void {
    if (this.hunks.length === 0) return;
    this.currentHunkIndex = (this.currentHunkIndex + 1) % this.hunks.length;
    this.revealCurrentHunk();
    this.highlightCurrentHunk();
    this.updateToolbarState();
    this.emit("monaco-diff-editor:hunk-changed", {
      hunk: this.hunks[this.currentHunkIndex],
    });
  }

  goToPreviousHunk(): void {
    if (this.hunks.length === 0) return;
    this.currentHunkIndex =
      (this.currentHunkIndex - 1 + this.hunks.length) % this.hunks.length;
    this.revealCurrentHunk();
    this.highlightCurrentHunk();
    this.updateToolbarState();
    this.emit("monaco-diff-editor:hunk-changed", {
      hunk: this.hunks[this.currentHunkIndex],
    });
  }

  goToHunk(index: number): void {
    if (index < 0 || index >= this.hunks.length) return;
    this.currentHunkIndex = index;
    this.revealCurrentHunk();
    this.highlightCurrentHunk();
    this.updateToolbarState();
  }

  private revealCurrentHunk(): void {
    if (!this.diffEditor || this.currentHunkIndex < 0) return;
    const hunk = this.hunks[this.currentHunkIndex];
    if (!hunk) return;

    // Reveal in the modified editor (right side)
    const modifiedEditor = this.diffEditor.getModifiedEditor();
    if (modifiedEditor && hunk.modifiedStartLine > 0) {
      modifiedEditor.revealLineInCenter(hunk.modifiedStartLine);
    }
  }

  // ── Hunk highlighting ───────────────────────────────────────────────

  private highlightCurrentHunk(): void {
    if (!this.diffEditor || !this.monacoInstance) return;

    const modifiedEditor = this.diffEditor.getModifiedEditor();
    if (!modifiedEditor) return;

    // Clear previous decorations
    this.hunkDecorations = modifiedEditor.deltaDecorations(
      this.hunkDecorations,
      [],
    );

    if (this.currentHunkIndex < 0 || this.hunks.length === 0) return;

    const hunk = this.hunks[this.currentHunkIndex];
    if (!hunk || hunk.modifiedStartLine === 0) return;

    // Highlight the active hunk range in the modified editor
    const startLine = hunk.modifiedStartLine;
    const endLine = Math.max(hunk.modifiedEndLine, startLine);

    this.hunkDecorations = modifiedEditor.deltaDecorations(
      [],
      [
        {
          range: new this.monacoInstance.Range(startLine, 1, endLine, 1),
          options: {
            isWholeLine: true,
            className: "diff-active-hunk-line",
            glyphMarginClassName: "diff-active-hunk-glyph",
            overviewRuler: {
              color: "#54aeff",
              position: this.monacoInstance.editor.OverviewRulerLane.Full,
            },
          },
        },
      ],
    );
  }

  // ── Accept / Reject ─────────────────────────────────────────────────

  acceptCurrentHunk(): void {
    if (this.currentHunkIndex < 0 || this.hunks.length === 0) return;
    const hunk = this.hunks[this.currentHunkIndex];
    if (!hunk) return;

    if (this.config.onHunkAccept) {
      this.config.onHunkAccept(hunk);
    }

    this.emit("monaco-diff-editor:hunk-accepted", { hunk });
  }

  rejectCurrentHunk(): void {
    if (this.currentHunkIndex < 0 || this.hunks.length === 0) return;
    const hunk = this.hunks[this.currentHunkIndex];
    if (!hunk) return;

    if (this.config.onHunkReject) {
      this.config.onHunkReject(hunk);
    }

    this.emit("monaco-diff-editor:hunk-rejected", { hunk });
  }

  // ── Toolbar state ───────────────────────────────────────────────────

  private updateToolbarState(): void {
    if (!this.toolbarEl) return;

    const counter = this.toolbarEl.querySelector(
      ".diff-hunk-counter",
    ) as HTMLElement;
    if (counter) {
      if (this.hunks.length === 0) {
        counter.textContent = "No changes";
      } else {
        counter.textContent = `Change ${this.currentHunkIndex + 1} of ${this.hunks.length}`;
      }
    }

    const hasHunks = this.hunks.length > 0;

    const prevBtn = this.toolbarEl.querySelector(
      ".diff-prev-hunk",
    ) as HTMLButtonElement;
    if (prevBtn) prevBtn.disabled = !hasHunks;

    const nextBtn = this.toolbarEl.querySelector(
      ".diff-next-hunk",
    ) as HTMLButtonElement;
    if (nextBtn) nextBtn.disabled = !hasHunks;

    const acceptBtn = this.toolbarEl.querySelector(
      ".diff-accept-hunk",
    ) as HTMLButtonElement;
    if (acceptBtn) acceptBtn.disabled = !hasHunks;

    const rejectBtn = this.toolbarEl.querySelector(
      ".diff-reject-hunk",
    ) as HTMLButtonElement;
    if (rejectBtn) rejectBtn.disabled = !hasHunks;
  }

  // ── Public API (original) ───────────────────────────────────────────

  getDiffEditor(): any {
    return this.diffEditor;
  }

  setOriginal(content: string): void {
    if (this.originalModel) {
      this.originalModel.setValue(content);
    }
  }

  setModified(content: string): void {
    if (this.modifiedModel) {
      this.modifiedModel.setValue(content);
    }
  }

  setLanguage(language: string): void {
    if (this.monacoInstance) {
      if (this.originalModel) {
        this.monacoInstance.editor.setModelLanguage(
          this.originalModel,
          language,
        );
      }
      if (this.modifiedModel) {
        this.monacoInstance.editor.setModelLanguage(
          this.modifiedModel,
          language,
        );
      }
    }
  }

  detectLanguage(filePath: string, content?: string): string {
    return detectLanguage(filePath, content);
  }

  toggleSideBySide(): void {
    if (!this.diffEditor) return;
    const current = this.diffEditor.getOption(
      this.monacoInstance.editor.EditorOption.renderSideBySide,
    );
    this.diffEditor.updateOptions({ renderSideBySide: !current });
  }

  /**
   * Load a new diff pair. Resets hunk state.
   */
  setDiff(original: string, modified: string, filePath?: string): void {
    this.currentHunkIndex = -1;
    this.hunkDecorations = [];

    if (filePath && this.monacoInstance) {
      const lang = detectLanguage(filePath, modified);
      if (this.originalModel) {
        this.monacoInstance.editor.setModelLanguage(this.originalModel, lang);
      }
      if (this.modifiedModel) {
        this.monacoInstance.editor.setModelLanguage(this.modifiedModel, lang);
      }
    }

    this.setOriginal(original);
    this.setModified(modified);
  }

  destroy(): void {
    if (this.originalModel) {
      this.originalModel.dispose();
      this.originalModel = null;
    }
    if (this.modifiedModel) {
      this.modifiedModel.dispose();
      this.modifiedModel = null;
    }
    if (this.diffEditor) {
      this.diffEditor.dispose();
      this.diffEditor = null;
    }
    this.monacoInstance = null;
    this.hunks = [];
    this.currentHunkIndex = -1;
    this.hunkDecorations = [];
    this.toolbarEl = null;
    super.destroy();
  }
}
