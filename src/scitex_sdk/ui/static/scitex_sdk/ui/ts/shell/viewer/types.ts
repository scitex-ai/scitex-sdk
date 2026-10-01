/**
 * Shell viewer types — adapter interface for file viewing.
 *
 * Ported from scitex-cloud's workspace-viewer/types.ts.
 * Uses adapter pattern so consumers provide their own backend.
 */

export type FileType =
  | "text"
  | "image"
  | "pdf"
  | "csv"
  | "mermaid"
  | "graphviz"
  | "audio"
  | "video"
  | "binary";

/** Backend adapter for file content. */
export interface ViewerAdapter {
  /** Read file content (text files). */
  readFile(path: string): Promise<{ content: string; language?: string }>;

  /** Save file content (text files). */
  saveFile?(path: string, content: string): Promise<void>;

  /** Get a URL to serve the raw file (images, PDFs, etc.). */
  getFileUrl(path: string): string;

  /**
   * Get a URL for file content API (JSON response with content field).
   * Falls back to getFileUrl if not provided.
   */
  getFileApiUrl?(path: string): string;
}

/** An open file in the viewer. */
export interface OpenFile {
  path: string;
  name: string;
  content: string;
  fileType: FileType;
  language?: string;
  dirty?: boolean;
}

/** Describes a single open tab in the workspace viewer */
export interface TabInfo {
  path: string;
  title: string;
  fileType: FileType;
}

/** Interface for viewer components that render file content */
export interface Viewer {
  render(
    container: HTMLElement,
    filePath: string,
    adapter: ViewerAdapter,
  ): Promise<void>;
  destroy(): void;
}

export interface ViewerConfig {
  /** Container for the viewer content (default: "#ws-viewer-content") */
  container?: string | HTMLElement;

  /** Container for file tabs (default: "#ws-viewer-tabs") */
  tabsContainer?: string | HTMLElement;

  /** Backend adapter. */
  adapter: ViewerAdapter;

  /** Called when a file is opened/switched. */
  onFileOpen?: (file: OpenFile) => void;

  /** Called when a file is saved. */
  onFileSave?: (path: string) => void;
}

export const LANGUAGE_MAP: { [key: string]: string } = {
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
  ".bib": "bibtex",
  ".txt": "plaintext",
  ".xml": "xml",
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
  ".toml": "toml",
  ".ini": "ini",
  ".cfg": "ini",
  ".conf": "ini",
  ".mmd": "markdown",
  ".mermaid": "markdown",
  ".dot": "plaintext",
  ".gv": "plaintext",
  ".csv": "plaintext",
  ".tsv": "plaintext",
};

/** Map filenames (no extension) to languages */
export const FILENAME_LANGUAGE_MAP: { [key: string]: string } = {
  makefile: "shell",
  dockerfile: "dockerfile",
  bashrc: "shell",
  bash_profile: "shell",
  bash_aliases: "shell",
  zshrc: "shell",
  vimrc: "plaintext",
  gitconfig: "ini",
  gitignore: "plaintext",
  screenrc: "plaintext",
};

/** Image file extensions */
export const IMAGE_EXTENSIONS = new Set([
  ".png",
  ".jpg",
  ".jpeg",
  ".gif",
  ".webp",
  ".svg",
  ".bmp",
  ".ico",
]);

/** PDF file extension */
export const PDF_EXTENSIONS = new Set([".pdf"]);

/** CSV/TSV file extensions for table view */
export const CSV_EXTENSIONS = new Set([".csv", ".tsv"]);

/** Mermaid diagram file extensions */
export const MERMAID_EXTENSIONS = new Set([".mmd", ".mermaid"]);

/** Graphviz diagram file extensions */
export const GRAPHVIZ_EXTENSIONS = new Set([".dot", ".gv"]);

/** Audio file extensions */
export const AUDIO_EXTENSIONS = new Set([
  ".mp3",
  ".wav",
  ".ogg",
  ".flac",
  ".m4a",
  ".aac",
  ".wma",
]);

/** Video file extensions */
export const VIDEO_EXTENSIONS = new Set([
  ".mp4",
  ".webm",
  ".avi",
  ".mov",
  ".mkv",
  ".ogv",
]);

/**
 * Binary file extensions that cannot be rendered as text or media.
 */
export const BINARY_EXTENSIONS = new Set([
  ".zip",
  ".tar",
  ".gz",
  ".rar",
  ".7z",
  ".exe",
  ".dll",
  ".so",
  ".dylib",
  ".doc",
  ".docx",
  ".xls",
  ".xlsx",
  ".ppt",
  ".pptx",
  ".woff",
  ".woff2",
  ".ttf",
  ".eot",
  ".otf",
]);

/** Detect language from shebang line (e.g. #!/bin/bash -> "shell"). */
export function detectShebang(content: string): string | null {
  const firstLine = content.split("\n", 1)[0];
  if (!firstLine.startsWith("#!")) return null;
  const shebang = firstLine.toLowerCase();
  if (shebang.includes("python")) return "python";
  if (shebang.includes("bash") || shebang.includes("/sh")) return "shell";
  if (shebang.includes("node")) return "javascript";
  if (shebang.includes("ruby")) return "ruby";
  if (shebang.includes("perl")) return "perl";
  if (shebang.includes("zsh")) return "shell";
  return null;
}

/**
 * Detect file type from file path extension.
 */
export function detectFileType(filePath: string): FileType {
  const ext = filePath.substring(filePath.lastIndexOf(".")).toLowerCase();

  if (IMAGE_EXTENSIONS.has(ext)) return "image";
  if (PDF_EXTENSIONS.has(ext)) return "pdf";
  if (CSV_EXTENSIONS.has(ext)) return "csv";
  if (MERMAID_EXTENSIONS.has(ext)) return "mermaid";
  if (GRAPHVIZ_EXTENSIONS.has(ext)) return "graphviz";
  if (AUDIO_EXTENSIONS.has(ext)) return "audio";
  if (VIDEO_EXTENSIONS.has(ext)) return "video";
  if (BINARY_EXTENSIONS.has(ext)) return "binary";
  return "text";
}
