/**
 * Monaco Theme — scitex-ui
 * SciTeX dark/light themes with LaTeX syntax highlighting.
 * Auto-switches with document data-theme attribute.
 */

export const MONACO_COLORS = {
  dark: {
    background: "#1e1e1e",
    gutterBackground: "#1e1e1e",
    foreground: "#e8e8e8",
    lineHighlight: "#2d2d2d",
    lineNumber: "#858585",
    lineNumberActive: "#c6c6c6",
    selection: "#264f78",
    selectionInactive: "#3a3d41",
  },
  light: {
    background: "#fdfcfa",
    gutterBackground: "#fdfcfa",
    foreground: "#333333",
    lineHighlight: "#f5f0eb",
    lineNumber: "#6b6b6b",
    lineNumberActive: "#333333",
    selection: "#c8ddf0",
    selectionInactive: "#e5ebf1",
  },
} as const;

// LaTeX token rules for dark theme
const DARK_LATEX_RULES = [
  { token: "comment.latex", foreground: "6A9955", fontStyle: "italic" },
  { token: "keyword.latex", foreground: "569CD6" },
  { token: "keyword.control.latex", foreground: "C586C0" },
  { token: "keyword.section.latex", foreground: "DCDCAA", fontStyle: "bold" },
  { token: "keyword.math.latex", foreground: "9CDCFE" },
  { token: "string.math.latex", foreground: "CE9178" },
  { token: "type.identifier.latex", foreground: "4EC9B0" },
  { token: "delimiter.curly.latex", foreground: "FFD700" },
  { token: "delimiter.square.latex", foreground: "DA70D6" },
  { token: "number.latex", foreground: "B5CEA8" },
  { token: "operator.latex", foreground: "D4D4D4" },
];

// LaTeX token rules for light theme
const LIGHT_LATEX_RULES = [
  { token: "comment.latex", foreground: "008000", fontStyle: "italic" },
  { token: "keyword.latex", foreground: "3366aa" },
  { token: "keyword.control.latex", foreground: "7744aa" },
  { token: "keyword.section.latex", foreground: "795E26", fontStyle: "bold" },
  { token: "keyword.math.latex", foreground: "001080" },
  { token: "string.math.latex", foreground: "A31515" },
  { token: "type.identifier.latex", foreground: "267F99" },
  { token: "delimiter.curly.latex", foreground: "B8860B" },
  { token: "delimiter.square.latex", foreground: "800080" },
  { token: "number.latex", foreground: "098658" },
  { token: "operator.latex", foreground: "333333" },
];

function makeThemeColors(mode: "dark" | "light") {
  const c = MONACO_COLORS[mode];
  return {
    "editor.background": c.background,
    "editor.foreground": c.foreground,
    "editorGutter.background": c.gutterBackground,
    "editor.lineHighlightBackground": c.lineHighlight,
    "editorLineNumber.foreground": c.lineNumber,
    "editorLineNumber.activeForeground": c.lineNumberActive,
    "editor.selectionBackground": c.selection,
    "editor.inactiveSelectionBackground": c.selectionInactive,
  };
}

export function defineScitexDarkTheme(monaco: any): void {
  monaco.editor.defineTheme("scitex-dark", {
    base: "vs-dark",
    inherit: true,
    rules: DARK_LATEX_RULES,
    colors: makeThemeColors("dark"),
  });
}

export function defineScitexLightTheme(monaco: any): void {
  monaco.editor.defineTheme("scitex-light", {
    base: "vs",
    inherit: true,
    rules: LIGHT_LATEX_RULES,
    colors: makeThemeColors("light"),
  });
}

export function initializeMonacoThemes(monaco: any): void {
  defineScitexDarkTheme(monaco);
  defineScitexLightTheme(monaco);
}

export function getThemeForMode(mode: "dark" | "light"): string {
  return mode === "dark" ? "scitex-dark" : "scitex-light";
}

export function getCurrentThemeMode(): "dark" | "light" {
  return document.documentElement.getAttribute("data-theme") === "dark"
    ? "dark"
    : "light";
}

export function setupMonacoThemeObserver(monaco: any): void {
  const observer = new MutationObserver(() => {
    const theme = getThemeForMode(getCurrentThemeMode());
    monaco.editor.setTheme(theme);
  });
  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["data-theme"],
  });
}

export function setupMonacoTheme(monaco: any): void {
  initializeMonacoThemes(monaco);
  setupMonacoThemeObserver(monaco);
  const theme = getThemeForMode(getCurrentThemeMode());
  monaco.editor.setTheme(theme);
}
