/**
 * Keyboard shortcuts — barrel export.
 *
 * Navigation shortcuts (Alt+A, Alt+T, etc.) and shortcuts modal.
 */

export { initKeyboardShortcuts } from "./_KeyboardShortcuts";

export {
  showShortcutsModal,
  toggleShortcutsModal,
  registerShortcuts,
  setContextDetector,
} from "./_ShortcutsModal";

export type {
  ShortcutContext,
  ShortcutDef,
  ShortcutSection,
} from "./_ShortcutsModal";
