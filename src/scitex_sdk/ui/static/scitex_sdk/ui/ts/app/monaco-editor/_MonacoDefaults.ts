/**
 * Monaco Editor Defaults — scitex-ui
 * Single source of truth for editor options across all SciTeX modules.
 */

export const MONACO_EDITOR_DEFAULTS = {
  automaticLayout: true,
  fontSize: 14,
  fontFamily: "'JetBrains Mono', 'Monaco', 'Menlo', monospace",
  minimap: { enabled: true },
  lineNumbers: "on" as const,
  renderWhitespace: "selection" as const,
  scrollBeyondLastLine: false,
  wordWrap: "on" as const,
  tabSize: 4,
  insertSpaces: true,
  glyphMargin: true,
  folding: true,
  suggest: {
    showKeywords: true,
    showSnippets: true,
  },
  quickSuggestions: true,
  parameterHints: { enabled: true },
  formatOnPaste: true,
  formatOnType: true,
} as const;
