/**
 * EmptyState — the "nothing here" block, once.
 *
 * Replaces the most duplicated shape in the fleet: four apps rolled their own
 * (scitex-cards 22 classes, figrecipe 16, scitex-writer 6, scitex-scholar 2)
 * and scitex-ui itself carried ~20 more, every one welded to a host component.
 * Base had empties but no empty.
 *
 * `title` is REQUIRED rather than optional. An empty state with no words is a
 * blank area, and a blank area is indistinguishable from a load that failed —
 * which is the one thing an empty state exists to rule out.
 */

import type { EmptyStateConfig } from "./types";

export function renderEmptyState(config: EmptyStateConfig): HTMLElement {
  const el = document.createElement("div");
  el.className = "stx-app-empty";
  if (config.compact) el.classList.add("stx-app-empty--compact");
  // Announced as a unit: a screen reader should hear "no results, add one"
  // rather than two orphaned fragments.
  el.setAttribute("role", "status");

  if (config.iconClass && !config.compact) {
    const icon = document.createElement("i");
    icon.className = `stx-app-empty__icon ${config.iconClass}`;
    // The icon repeats the title; announcing it adds nothing.
    icon.setAttribute("aria-hidden", "true");
    el.appendChild(icon);
  }

  const title = document.createElement("div");
  title.className = "stx-app-empty__title";
  title.textContent = config.title;
  el.appendChild(title);

  if (config.hint) {
    const hint = document.createElement("div");
    hint.className = "stx-app-empty__hint";
    hint.textContent = config.hint;
    el.appendChild(hint);
  }

  if (config.action && !config.compact) {
    const wrap = document.createElement("div");
    wrap.className = "stx-app-empty__action";
    wrap.appendChild(config.action);
    el.appendChild(wrap);
  }

  return el;
}
