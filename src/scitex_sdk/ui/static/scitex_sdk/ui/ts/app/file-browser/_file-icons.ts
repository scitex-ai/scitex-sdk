/**
 * File icon map — VS Code / Gitea-inspired colorful icons.
 *
 * Ported from scitex-cloud's _file-tree-builder.ts + file-tree.ts.
 * Single source of truth for file type → icon + color mapping.
 */

export interface FileIconDef {
  icon: string;
  color: string;
}

/** Extension → icon + color */
const EXTENSION_ICONS: Record<string, FileIconDef> = {
  // Programming languages
  ".py": { icon: "fab fa-python", color: "#3776ab" },
  ".js": { icon: "fab fa-js", color: "#f7df1e" },
  ".ts": { icon: "fab fa-js", color: "#3178c6" },
  ".jsx": { icon: "fab fa-react", color: "#61dafb" },
  ".tsx": { icon: "fab fa-react", color: "#61dafb" },
  ".java": { icon: "fab fa-java", color: "#007396" },
  ".go": { icon: "fas fa-code", color: "#00add8" },
  ".rs": { icon: "fas fa-gear", color: "#ce422b" },
  ".c": { icon: "fas fa-file-code", color: "#555555" },
  ".cpp": { icon: "fas fa-file-code", color: "#f34b7d" },
  ".el": { icon: "fas fa-file-code", color: "#7f5ab6" },

  // Web
  ".html": { icon: "fab fa-html5", color: "#e34c26" },
  ".css": { icon: "fab fa-css3-alt", color: "#264de4" },
  ".scss": { icon: "fab fa-sass", color: "#cc6699" },

  // Data & Config
  ".json": { icon: "fas fa-brackets-curly", color: "#ffa500" },
  ".yaml": { icon: "fas fa-file-code", color: "#cb171e" },
  ".yml": { icon: "fas fa-file-code", color: "#cb171e" },
  ".toml": { icon: "fas fa-file-code", color: "#9c4121" },
  ".xml": { icon: "fas fa-file-code", color: "#e37933" },
  ".csv": { icon: "fas fa-table", color: "#217346" },

  // Documentation
  ".md": { icon: "fab fa-markdown", color: "#000000" },
  ".txt": { icon: "fas fa-file-alt", color: "#777777" },
  ".pdf": { icon: "fas fa-file-pdf", color: "#ff0000" },

  // Scripts & Shell
  ".sh": { icon: "fas fa-terminal", color: "#89e051" },
  ".bash": { icon: "fas fa-terminal", color: "#89e051" },

  // Data Science
  ".r": { icon: "fab fa-r-project", color: "#276dc3" },
  ".ipynb": { icon: "fas fa-book", color: "#ff6f00" },
  ".sql": { icon: "fas fa-database", color: "#e38c00" },

  // Images
  ".jpg": { icon: "fas fa-image", color: "#00bfa5" },
  ".jpeg": { icon: "fas fa-image", color: "#00bfa5" },
  ".png": { icon: "fas fa-image", color: "#00bfa5" },
  ".gif": { icon: "fas fa-image", color: "#00bfa5" },
  ".svg": { icon: "fas fa-image", color: "#ffb300" },
  ".webp": { icon: "fas fa-image", color: "#00bfa5" },

  // Archives
  ".zip": { icon: "fas fa-file-archive", color: "#8b8b8b" },
  ".tar": { icon: "fas fa-file-archive", color: "#8b8b8b" },
  ".gz": { icon: "fas fa-file-archive", color: "#8b8b8b" },

  // Others
  ".tex": { icon: "fas fa-file-alt", color: "#3d6117" },
  ".log": { icon: "fas fa-file-lines", color: "#777777" },
  ".env": { icon: "fas fa-cog", color: "#edb92e" },
};

/** Special file names (case-insensitive match) */
const SPECIAL_FILES: Record<string, FileIconDef> = {
  "readme.md": { icon: "fas fa-book", color: "#00b0ff" },
  readme: { icon: "fas fa-book", color: "#00b0ff" },
  license: { icon: "fas fa-scroll", color: "#ffab00" },
  dockerfile: { icon: "fab fa-docker", color: "#2496ed" },
  makefile: { icon: "fas fa-cog", color: "#6d6d6d" },
  ".gitignore": { icon: "fab fa-git-alt", color: "#f05032" },
  ".gitattributes": { icon: "fab fa-git-alt", color: "#f05032" },
  "package.json": { icon: "fab fa-npm", color: "#cb3837" },
  "tsconfig.json": { icon: "fab fa-js", color: "#3178c6" },
  "requirements.txt": { icon: "fab fa-python", color: "#3776ab" },
  "setup.py": { icon: "fab fa-python", color: "#3776ab" },
  "pyproject.toml": { icon: "fab fa-python", color: "#3776ab" },
};

const DEFAULT_ICON: FileIconDef = { icon: "fas fa-file", color: "#777777" };
const FOLDER_ICON: FileIconDef = { icon: "fas fa-folder", color: "#dcb67a" };
const FOLDER_OPEN_ICON: FileIconDef = {
  icon: "fas fa-folder-open",
  color: "#dcb67a",
};

/**
 * Get the icon definition for a file or directory.
 */
export function getFileIconDef(
  filename: string,
  type: "file" | "directory" = "file",
  expanded?: boolean,
): FileIconDef {
  if (type === "directory") {
    return expanded ? FOLDER_OPEN_ICON : FOLDER_ICON;
  }

  const name = filename.toLowerCase();
  if (SPECIAL_FILES[name]) return SPECIAL_FILES[name];

  const ext = name.substring(name.lastIndexOf(".")).toLowerCase();
  if (EXTENSION_ICONS[ext]) return EXTENSION_ICONS[ext];

  return DEFAULT_ICON;
}

/**
 * Get Font Awesome class string for a file (backward-compatible).
 */
export function getFileIconClass(filename: string): string {
  return getFileIconDef(filename, "file").icon;
}
