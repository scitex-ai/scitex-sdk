/**
 * Monaco Editor — scitex-ui
 * Public API for Monaco editor components.
 */

// Components
export { MonacoEditor } from "./_MonacoEditor";
export { MonacoDiffEditor } from "./_MonacoDiffEditor";

// Types
export type {
  MonacoEditorConfig,
  MonacoDiffEditorConfig,
  DiffHunk,
} from "./types";
export { LANGUAGE_MAP, detectLanguage } from "./types";

// Defaults
export { MONACO_EDITOR_DEFAULTS } from "./_MonacoDefaults";

// Theme
export {
  MONACO_COLORS,
  initializeMonacoThemes,
  setupMonacoTheme,
  setupMonacoThemeObserver,
  getThemeForMode,
  getCurrentThemeMode,
} from "./_MonacoTheme";

// Keybindings
export {
  addEmacsKeybindings,
  removeEmacsKeybindings,
  setKeybindingMode,
} from "./_MonacoKeybindings";

// Languages
export {
  registerLatexLanguage,
  registerBibtexLanguage,
  registerLatexSnippetProvider,
  registerCustomLanguages,
} from "./_MonacoLanguages";

// Loader
export { monaco, waitForMonaco } from "./_MonacoLoader";
