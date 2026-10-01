/**
 * Keyboard Shortcuts Modal Component
 *
 * Ported from scitex-cloud/static/shared/ts/components/shortcuts-modal.ts
 *
 * Shows context-aware keyboard shortcuts help with sleek vis-style layout.
 * Context detection is pluggable: apps register their own shortcuts via
 * registerShortcuts(context, sections).
 */

/* ── Types ──────────────────────────────────────────────── */

/** App context type — apps can register any string as a context. */
export type ShortcutContext = string;

/** Single shortcut definition. */
export interface ShortcutDef {
  keys: string;
  description: string;
}

/** A section of related shortcuts. */
export interface ShortcutSection {
  title: string;
  shortcuts: ShortcutDef[];
}

/* ── Registry ───────────────────────────────────────────── */

const contextSections: Map<ShortcutContext, ShortcutSection[]> = new Map();

// Default global shortcuts (always shown)
contextSections.set("global", [
  {
    title: "Global Navigation",
    shortcuts: [
      { keys: "Alt+A", description: "Toggle AI panel" },
      { keys: "Alt+T", description: "Cycle to next pane" },
      { keys: "Alt+Shift+T", description: "Cycle to previous pane" },
      { keys: "Alt+Right", description: "Focus next pane" },
      { keys: "Alt+Left", description: "Focus previous pane" },
      { keys: "Alt+Shift+Right", description: "Collapse rightward" },
      { keys: "Alt+Shift+Left", description: "Collapse leftward" },
      { keys: "Ctrl+U", description: "Upload files" },
    ],
  },
  {
    title: "Terminal (Right-Click)",
    shortcuts: [
      { keys: "Right \u00d71", description: "Send 1 + Enter (0.5s delay)" },
      { keys: "Right \u00d72", description: "Send 2 + Enter (0.5s delay)" },
      { keys: "Right \u00d73", description: "Send 3 + Enter (0.5s delay)" },
      { keys: "Right \u00d74", description: "Send 4 + Enter (0.5s delay)" },
    ],
  },
]);

/* ── Context detection ──────────────────────────────────── */

type ContextDetector = () => ShortcutContext;
let detectContextFn: ContextDetector = () => "global";

/**
 * Register shortcut sections for a given context.
 * Subsequent calls for the same context append to existing sections.
 */
export function registerShortcuts(
  context: ShortcutContext,
  sections: ShortcutSection[],
): void {
  const existing = contextSections.get(context) || [];
  contextSections.set(context, [...existing, ...sections]);
}

/**
 * Override the context detection function.
 * By default returns "global". Apps can set a custom detector
 * that inspects the URL, DOM, or application state.
 */
export function setContextDetector(fn: ContextDetector): void {
  detectContextFn = fn;
}

/* ── HTML generation ────────────────────────────────────── */

function generateSectionsHTML(sections: ShortcutSection[]): string {
  return sections
    .map(
      (section) => `
    <div class="shortcuts-section">
      <h4>${section.title}</h4>
      ${section.shortcuts
        .map(
          (s) => `
        <div class="shortcut-row"><kbd>${s.keys}</kbd> ${s.description}</div>
      `,
        )
        .join("")}
    </div>
  `,
    )
    .join("");
}

/* ── Modal lifecycle ────────────────────────────────────── */

/**
 * Show the keyboard shortcuts modal.
 * If already open, closes it (toggle behavior).
 */
export function showShortcutsModal(): void {
  // Remove existing modal (toggle)
  const existing = document.getElementById("shortcuts-modal-global");
  if (existing) {
    existing.remove();
    return;
  }

  const context = detectContextFn();

  // Build sections — always include global, then context-specific
  const allSections: ShortcutSection[] = [
    ...(contextSections.get("global") || []),
  ];
  if (context !== "global" && contextSections.has(context)) {
    allSections.push(...contextSections.get(context)!);
  }

  // Context display name: capitalize first letter
  const contextName = context.charAt(0).toUpperCase() + context.slice(1);

  // Create modal
  const modal = document.createElement("div");
  modal.id = "shortcuts-modal-global";
  modal.innerHTML = `
    <div class="shortcuts-modal-content">
      <div class="shortcuts-modal-header">
        <h3><i class="fas fa-keyboard"></i> Keyboard Shortcuts</h3>
        <span class="shortcuts-context-badge">${contextName}</span>
        <button class="shortcuts-modal-close">&times;</button>
      </div>
      <div class="shortcuts-modal-body">
        ${generateSectionsHTML(allSections)}
      </div>
      <div class="shortcuts-modal-footer">
        <span class="shortcuts-hint">Press <kbd>Esc</kbd> to close</span>
      </div>
    </div>
  `;

  // Overlay style (applied inline to avoid depending on class being in CSS)
  modal.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.6);
    backdrop-filter: blur(4px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10000;
    opacity: 0;
    transition: opacity 0.2s ease;
  `;

  // Add to page
  document.body.appendChild(modal);

  // Animate in
  requestAnimationFrame(() => {
    modal.style.opacity = "1";
  });

  // Close handlers
  const closeModal = () => {
    modal.style.opacity = "0";
    setTimeout(() => modal.remove(), 200);
  };

  modal
    .querySelector(".shortcuts-modal-close")
    ?.addEventListener("click", closeModal);
  modal.addEventListener("click", (e) => {
    if (e.target === modal) closeModal();
  });

  // Escape key closes
  const escHandler = (e: KeyboardEvent) => {
    if (e.key === "Escape") {
      closeModal();
      document.removeEventListener("keydown", escHandler);
    }
  };
  document.addEventListener("keydown", escHandler);
}

/**
 * Toggle shortcuts modal (open if closed, close if open).
 */
export function toggleShortcutsModal(): void {
  const existing = document.getElementById("shortcuts-modal-global");
  if (existing) {
    existing.style.opacity = "0";
    setTimeout(() => existing.remove(), 200);
  } else {
    showShortcutsModal();
  }
}

/* ── Window globals ─────────────────────────────────────── */

declare global {
  interface Window {
    showShortcutsModal: typeof showShortcutsModal;
    toggleShortcutsModal: typeof toggleShortcutsModal;
    registerShortcuts: typeof registerShortcuts;
  }
}

window.showShortcutsModal = showShortcutsModal;
window.toggleShortcutsModal = toggleShortcutsModal;
window.registerShortcuts = registerShortcuts;
