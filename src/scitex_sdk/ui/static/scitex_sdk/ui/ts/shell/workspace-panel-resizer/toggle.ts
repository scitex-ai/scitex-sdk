/** Toggle icon update and click-handler logic for WorkspacePanelResizer */

import type { PanelConfig } from "./types";
import { getValidExpandWidth } from "./state";

export function updateToggleIcon(
  toggleBtn: HTMLElement,
  direction: "left" | "right",
  isCollapsed: boolean,
): void {
  const icon = toggleBtn.querySelector("i");
  if (!icon) return;

  if (direction === "left") {
    if (isCollapsed) {
      icon.classList.remove("fa-chevron-left");
      icon.classList.add("fa-chevron-right");
    } else {
      icon.classList.remove("fa-chevron-right");
      icon.classList.add("fa-chevron-left");
    }
  } else {
    if (isCollapsed) {
      icon.classList.remove("fa-chevron-right");
      icon.classList.add("fa-chevron-left");
    } else {
      icon.classList.remove("fa-chevron-left");
      icon.classList.add("fa-chevron-right");
    }
  }
}

export function initToggleClickHandler(
  storagePrefix: string,
  config: PanelConfig,
): void {
  if (!config.toggleButtonId) return;

  const toggleBtn = document.getElementById(config.toggleButtonId);
  const targetPanel = document.querySelector(config.targetPanel) as HTMLElement;

  if (!toggleBtn || !targetPanel) {
    console.warn(
      `[WorkspacePanelResizer] Missing toggle elements for ${config.toggleButtonId}`,
    );
    return;
  }

  // Guard: prevent double-registering click handler on same element
  if (toggleBtn.dataset.wprToggleInit === "true") {
    console.log(
      `[WorkspacePanelResizer] Toggle already initialized for ${config.toggleButtonId}, skipping.`,
    );
    return;
  }
  toggleBtn.dataset.wprToggleInit = "true";

  // Double-click on the sidebar header also toggles the panel
  const sidebarHeader = targetPanel.querySelector<HTMLElement>(
    ".stx-shell-sidebar__header",
  );
  if (sidebarHeader) {
    sidebarHeader.addEventListener("dblclick", () => {
      toggleBtn.click();
    });
  }

  toggleBtn.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();

    const isCollapsed = targetPanel.classList.toggle("collapsed");

    if (isCollapsed) {
      targetPanel.style.width = "";
      targetPanel.style.height = "";
      targetPanel.style.maxWidth = "";
      targetPanel.style.maxHeight = "";
      targetPanel.style.flexShrink = "";
      targetPanel.style.flexGrow = "";
      // On mobile vertical layout, also clear pane wrapper's inline styles
      // so CSS :has(.collapsed) rule can take effect
      const paneWrapper = targetPanel.closest(
        ".ws-ai-pane, .ws-worktree-pane, .ws-viewer-pane",
      ) as HTMLElement | null;
      if (paneWrapper) {
        paneWrapper.style.flex = "";
        paneWrapper.style.height = "";
        paneWrapper.style.minHeight = "";
        paneWrapper.style.maxHeight = "";
      }
    } else {
      const validSize = getValidExpandWidth(storagePrefix, config, targetPanel);
      if (validSize) {
        // Detect axis from container
        const container = targetPanel.closest(
          ".workspace-three-col",
        ) as HTMLElement;
        const isVertical =
          container && getComputedStyle(container).flexDirection === "column";
        if (isVertical) {
          targetPanel.style.height = `${validSize}px`;
          targetPanel.style.width = "";
        } else {
          targetPanel.style.width = `${validSize}px`;
          targetPanel.style.height = "";
        }
        targetPanel.style.flexShrink = "0";
        targetPanel.style.flexGrow = "0";
      } else {
        targetPanel.style.width = "";
        targetPanel.style.height = "";
        targetPanel.style.maxWidth = "";
        targetPanel.style.maxHeight = "";
        targetPanel.style.flexShrink = "";
        targetPanel.style.flexGrow = "";
      }
    }

    // On expand, also clear pane wrapper inline styles to restore CSS flex defaults
    if (!isCollapsed) {
      const paneWrapper = targetPanel.closest(
        ".ws-ai-pane, .ws-worktree-pane, .ws-viewer-pane",
      ) as HTMLElement | null;
      if (paneWrapper) {
        paneWrapper.style.flex = "";
        paneWrapper.style.height = "";
        paneWrapper.style.minHeight = "";
        paneWrapper.style.maxHeight = "";
      }
    }

    updateToggleIcon(toggleBtn, config.resizeDirection, isCollapsed);

    if (config.collapseStorageKey) {
      localStorage.setItem(config.collapseStorageKey, isCollapsed.toString());
    }
  });

  console.log(
    `[WorkspacePanelResizer] Toggle click handler attached for ${config.toggleButtonId}`,
  );
}
