/**
 * Type definitions for the MediaViewer component.
 */

import type { BaseComponentConfig } from "../../_base/types";

export type MediaFileType =
  | "image"
  | "pdf"
  | "csv"
  | "mermaid"
  | "graphviz"
  | "binary"
  | "text";

export interface MediaViewerConfig extends BaseComponentConfig {
  /** Build a URL for fetching file content */
  getFileUrl: (filePath: string, raw?: boolean, download?: boolean) => string;
  /** Called when file is downloaded */
  onDownload?: (filePath: string) => void;
  /** Called when viewer visibility changes */
  onVisibilityChange?: (visible: boolean) => void;
}

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

export const PDF_EXTENSIONS = new Set([".pdf"]);

export const CSV_EXTENSIONS = new Set([".csv", ".tsv"]);

export const MERMAID_EXTENSIONS = new Set([".mmd", ".mermaid"]);

export const GRAPHVIZ_EXTENSIONS = new Set([".dot", ".gv"]);

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
  ".mp3",
  ".mp4",
  ".wav",
  ".avi",
  ".mkv",
  ".mov",
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

export function detectFileType(filePath: string): MediaFileType {
  const ext = filePath.substring(filePath.lastIndexOf(".")).toLowerCase();
  if (IMAGE_EXTENSIONS.has(ext)) return "image";
  if (PDF_EXTENSIONS.has(ext)) return "pdf";
  if (CSV_EXTENSIONS.has(ext)) return "csv";
  if (MERMAID_EXTENSIONS.has(ext)) return "mermaid";
  if (GRAPHVIZ_EXTENSIONS.has(ext)) return "graphviz";
  if (BINARY_EXTENSIONS.has(ext)) return "binary";
  return "text";
}
