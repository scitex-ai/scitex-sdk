/**
 * Monaco Editor Types — scitex-ui
 * Shared types, config interfaces, and language detection.
 */

import type { BaseComponentConfig } from "../../_base/types";

// ── Config interfaces ────────────────────────────────────────────────

export interface MonacoEditorConfig extends BaseComponentConfig {
  language?: string;
  value?: string;
  readOnly?: boolean;
  minimap?: boolean;
  lineNumbers?: "on" | "off" | "relative";
  wordWrap?: "on" | "off" | "wordWrapColumn" | "bounded";
  fontSize?: number;
  tabSize?: number;
  theme?: string;
  keybindingMode?: "emacs" | "vim" | "vscode";
}

export interface MonacoDiffEditorConfig extends BaseComponentConfig {
  original?: string;
  modified?: string;
  language?: string;
  readOnly?: boolean;
  renderSideBySide?: boolean;
  theme?: string;
  /** Show hunk navigation toolbar (prev/next buttons). Default false. */
  enableHunkNavigation?: boolean;
  /** Show accept/reject buttons per hunk. Requires enableHunkNavigation. Default false. */
  enableHunkActions?: boolean;
  /** Callback when a hunk is accepted (applied to the original). */
  onHunkAccept?: (hunk: DiffHunk) => void;
  /** Callback when a hunk is rejected (reverted in the modified). */
  onHunkReject?: (hunk: DiffHunk) => void;
  /** File path — used for language auto-detection. */
  filePath?: string;
}

/** Represents a contiguous block of changes between original and modified. */
export interface DiffHunk {
  /** Zero-based index among all hunks. */
  index: number;
  /** Line range in the original model (1-based, inclusive). */
  originalStartLine: number;
  originalEndLine: number;
  /** Line range in the modified model (1-based, inclusive). */
  modifiedStartLine: number;
  modifiedEndLine: number;
  /** The original text in this range. */
  originalText: string;
  /** The modified text in this range. */
  modifiedText: string;
}

// ── Language detection ───────────────────────────────────────────────

export const LANGUAGE_MAP: Record<string, string> = {
  ".py": "python",
  ".js": "javascript",
  ".ts": "typescript",
  ".tsx": "typescript",
  ".jsx": "javascript",
  ".html": "html",
  ".htm": "html",
  ".css": "css",
  ".scss": "scss",
  ".less": "less",
  ".json": "json",
  ".md": "markdown",
  ".yaml": "yaml",
  ".yml": "yaml",
  ".sh": "shell",
  ".bash": "shell",
  ".zsh": "shell",
  ".r": "r",
  ".R": "r",
  ".tex": "latex",
  ".sty": "latex",
  ".cls": "latex",
  ".ltx": "latex",
  ".bib": "bibtex",
  ".txt": "plaintext",
  ".xml": "xml",
  ".svg": "xml",
  ".sql": "sql",
  ".go": "go",
  ".rs": "rust",
  ".java": "java",
  ".c": "c",
  ".cpp": "cpp",
  ".h": "c",
  ".hpp": "cpp",
  ".rb": "ruby",
  ".php": "php",
  ".lua": "lua",
  ".pl": "perl",
  ".swift": "swift",
  ".kt": "kotlin",
  ".scala": "scala",
  ".dockerfile": "dockerfile",
  ".toml": "toml",
  ".ini": "ini",
  ".cfg": "ini",
  ".conf": "ini",
  ".el": "plaintext",
  ".lisp": "plaintext",
  ".hs": "plaintext",
  ".ml": "plaintext",
  ".org": "plaintext",
  ".rst": "plaintext",
  ".makefile": "plaintext",
};

const SHEBANG_MAP: Record<string, string> = {
  python: "python",
  bash: "shell",
  "/sh": "shell",
  node: "javascript",
  ruby: "ruby",
  perl: "perl",
};

/**
 * Detect language from file path and optional content (shebang).
 * Like Emacs major-mode detection: extension first, shebang fallback.
 */
export function detectLanguage(filePath: string, content?: string): string {
  // Shebang detection (highest priority, like Emacs)
  if (content) {
    const firstLine = content.split("\n")[0];
    if (firstLine.startsWith("#!")) {
      const shebang = firstLine.toLowerCase();
      for (const [key, lang] of Object.entries(SHEBANG_MAP)) {
        if (shebang.includes(key)) return lang;
      }
    }
  }

  // Extension detection
  const ext = filePath.substring(filePath.lastIndexOf(".")).toLowerCase();
  return LANGUAGE_MAP[ext] || "plaintext";
}
