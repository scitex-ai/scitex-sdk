/** Size and collapse state persistence helpers for WorkspacePanelResizer.
 *
 * These helpers save/restore the panel size (width or height) depending on
 * the current axis. The storage key is shared — on desktop a panel saves its
 * width; on mobile the same key stores height. This is fine because the
 * resizer re-detects the axis on every drag start.
 */

import type { PanelConfig } from "./types";

export function saveWidth(
  storagePrefix: string,
  config: PanelConfig,
  size: number,
): void {
  try {
    localStorage.setItem(storagePrefix + config.storageKey, size.toString());
  } catch (e) {
    console.warn("[WorkspacePanelResizer] Failed to save size:", e);
  }
}

export function restoreWidth(
  storagePrefix: string,
  config: PanelConfig,
  panel: HTMLElement,
): void {
  try {
    // Fixed-width panels keep their CSS size — never override from localStorage
    if (config.fixedWidth) return;

    if (panel.classList.contains("collapsed")) {
      panel.style.width = "";
      panel.style.height = "";
      panel.style.flexShrink = "";
      panel.style.flexGrow = "";
      console.log(
        `[WorkspacePanelResizer] Panel ${config.storageKey} is collapsed, using CSS size`,
      );
      return;
    }
    const savedSize = localStorage.getItem(storagePrefix + config.storageKey);
    if (savedSize) {
      const size = parseInt(savedSize, 10);
      if (size >= config.minWidth) {
        // Detect current axis from container
        const container = panel.closest(".workspace-three-col") as HTMLElement;
        const isVertical =
          container && getComputedStyle(container).flexDirection === "column";

        if (isVertical) {
          panel.style.height = `${size}px`;
        } else {
          panel.style.width = `${size}px`;
        }
        panel.style.flexShrink = "0";
        panel.style.flexGrow = "0";
        console.log(
          `[WorkspacePanelResizer] Restored ${config.storageKey} to ${size}px`,
        );
      }
    }
  } catch (e) {
    console.warn("[WorkspacePanelResizer] Failed to restore size:", e);
  }
}

export function getValidExpandWidth(
  storagePrefix: string,
  config: PanelConfig,
  panel: HTMLElement,
): number | null {
  const saved = localStorage.getItem(storagePrefix + config.storageKey);
  if (!saved) return null;
  const size = parseInt(saved, 10);
  if (size <= config.minWidth + 10) return null;

  const container = panel.parentElement;
  if (container) {
    const isVertical = getComputedStyle(container).flexDirection === "column";
    const maxS =
      (isVertical ? container.offsetHeight : container.offsetWidth) * 0.8;
    if (size > maxS && maxS > 100) return null;
  }
  return size;
}

export function restoreCollapseState(
  config: PanelConfig,
  panel: HTMLElement,
  toggleBtn: HTMLElement | null,
  updateToggleIcon: (
    btn: HTMLElement,
    dir: "left" | "right",
    collapsed: boolean,
  ) => void,
): void {
  if (!config.collapseStorageKey) return;
  try {
    const saved = localStorage.getItem(config.collapseStorageKey);
    if (saved === "true") {
      panel.classList.add("collapsed");
      panel.style.width = "";
      panel.style.height = "";
      panel.style.flexShrink = "";
      panel.style.flexGrow = "";
      if (toggleBtn) updateToggleIcon(toggleBtn, config.resizeDirection, true);
    } else if (saved === "false") {
      panel.classList.remove("collapsed");
      if (toggleBtn) updateToggleIcon(toggleBtn, config.resizeDirection, false);
    }
    // saved === null: keep HTML default, no change
  } catch (e) {
    console.warn(
      "[WorkspacePanelResizer] Failed to restore collapse state:",
      e,
    );
  }
}
