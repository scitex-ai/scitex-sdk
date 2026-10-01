/**
 * Model badge display for the AI chat panel.
 *
 * Ported from scitex-cloud's model-badge.ts.
 * Decoupled from Django API URLs — uses ChatAdapter.fetchCurrentModel() instead.
 */

const MODEL_KEY = "stx-shell-ai-model";
const MODEL_DISPLAY_KEY = "stx-shell-ai-model-display";

export { MODEL_KEY };

export function setModelBadge(
  badge: HTMLElement | null,
  modelName: string,
  campaign?: boolean,
  displayName?: string,
): void {
  if (!badge) return;
  if (!modelName || modelName === "undefined" || modelName === "null") {
    badge.textContent = "No AI model configured";
    badge.title = "No AI provider configured";
    return;
  }
  const display = displayName || modelName;
  const suffix = campaign ? " (Campaign)" : "";
  badge.textContent = display + suffix;
  badge.title = campaign ? `${modelName} — Campaign mode (limited)` : modelName;
  try {
    sessionStorage.setItem(MODEL_KEY, modelName);
    if (displayName) sessionStorage.setItem(MODEL_DISPLAY_KEY, displayName);
  } catch {
    /* ignore */
  }
}
