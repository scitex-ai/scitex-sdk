/** Drag-resize mouse event logic for WorkspacePanelResizer
 *
 * Features:
 * - Axis-agnostic: auto-detects horizontal (row) or vertical (column) layout
 *   from the container's flex-direction. Desktop and mobile use the same logic.
 * - Smart collapse: when panel is dragged below minSize, it collapses instantly
 * - Curtain propagation: remaining drag delta transfers to the next adjacent panel
 * - Bidirectional: works in both directions along the active axis
 */

import type { PanelConfig } from "./types";
import type { AxisConfig } from "./axis";
import { detectAxis } from "./axis";
import { saveWidth, restoreWidth } from "./state";
import { updateToggleIcon } from "./toggle";
import { magneticSnap, percentSnapPoints } from "../resizer/_snap";

/** Shared collapse threshold — panel collapses when size drops to this */
const COLLAPSE_SIZE = 40;

/** Minimum size the module pane (flex:1, no resizer) must retain. */
const MIN_MODULE_SIZE = 40;

/** Calculate the maximum size a panel can grow to without pushing siblings
 *  off-screen. Uses each sibling's ACTUAL current size so the cap reflects reality.
 */
function getMaxAllowedSize(panel: HTMLElement, axis: AxisConfig): number {
  const paneEl =
    panel.closest(
      ".ws-ai-pane, .ws-worktree-pane, .ws-viewer-pane",
    ) || panel.parentElement;
  if (!paneEl) return Infinity;

  const flexContainer = paneEl.closest(".workspace-three-col") as HTMLElement;
  if (!flexContainer) return Infinity;

  const containerSize = axis.size(flexContainer);
  let reserved = 0;

  for (const child of Array.from(flexContainer.children) as HTMLElement[]) {
    if (child === paneEl) continue;
    if (child.classList.contains("ws-module-pane")) {
      reserved += MIN_MODULE_SIZE;
    } else {
      reserved += axis.size(child);
    }
  }

  return containerSize - reserved;
}

/** Find the next resizable panel in the given direction.
 *  Walks through siblings, skipping panes that have no resizer.
 *  Collapsed panels are skipped by default, but included when curtain=true.
 */
function findAdjacentPanel(
  config: PanelConfig,
  dragDirection: "shrink-left" | "shrink-right",
  curtain: boolean = false,
): { panel: HTMLElement; config: PanelConfig } | null {
  const targetPanel = document.querySelector(config.targetPanel) as HTMLElement;
  if (!targetPanel) return null;

  const paneContainer = targetPanel.closest(
    ".ws-ai-pane, .ws-worktree-pane, .ws-viewer-pane, .ws-module-pane",
  );
  if (!paneContainer) return null;

  let current: Element | null = paneContainer;
  while (current) {
    // Annotated because `current` is reassigned from `sibling` below: without
    // it the two infer through each other and tsc falls back to implicit any.
    const sibling: Element | null =
      dragDirection === "shrink-left"
        ? current.previousElementSibling
        : current.nextElementSibling;
    if (!sibling) return null;

    const siblingResizer = sibling.querySelector(
      "[data-panel-resizer]",
    ) as HTMLElement;
    const siblingPanel = sibling.querySelector(
      ".stx-shell-sidebar",
    ) as HTMLElement;

    if (!siblingResizer || !siblingPanel) {
      current = sibling;
      continue;
    }

    if (siblingPanel.classList.contains("collapsed") && !curtain) {
      current = sibling;
      continue;
    }

    const sibConfig: PanelConfig = {
      resizerId: siblingResizer.id,
      targetPanel: `#${siblingPanel.id}`,
      minWidth: parseInt(siblingResizer.dataset.minWidth || "40", 10),
      storageKey: siblingResizer.dataset.storageKey || "",
      resizeDirection: (siblingResizer.dataset.direction || "left") as
        | "left"
        | "right",
      toggleButtonId: siblingResizer.dataset.toggleBtn,
      collapseStorageKey: siblingResizer.dataset.collapseKey,
      defaultWidth: siblingResizer.dataset.defaultWidth
        ? parseInt(siblingResizer.dataset.defaultWidth, 10)
        : undefined,
    };

    return { panel: siblingPanel, config: sibConfig };
  }

  return null;
}

/** Collapse a panel programmatically */
function collapsePanel(
  storagePrefix: string,
  config: PanelConfig,
  panel: HTMLElement,
  axis: AxisConfig,
): void {
  panel.classList.add("collapsed");
  axis.clearSize(panel);
  axis.unlockFlex(panel);

  if (config.toggleButtonId) {
    const toggleBtn = document.getElementById(config.toggleButtonId);
    if (toggleBtn) updateToggleIcon(toggleBtn, config.resizeDirection, true);
  }

  if (config.collapseStorageKey) {
    localStorage.setItem(config.collapseStorageKey, "true");
  }
}

export function initResizer(storagePrefix: string, config: PanelConfig): void {
  const resizer = document.getElementById(config.resizerId);
  const targetPanel = document.querySelector(config.targetPanel) as HTMLElement;

  if (!resizer || !targetPanel) {
    console.warn(
      `[WorkspacePanelResizer] Missing elements for ${config.resizerId}`,
    );
    return;
  }

  restoreWidth(storagePrefix, config, targetPanel);

  let isResizing = false;
  let startPos = 0;
  let startSize = 0;
  let wasCollapsed = false;
  let primaryCollapsed = false;
  let axis: AxisConfig;
  /** On vertical axis, resize the pane wrapper instead of the sidebar */
  let effectiveTarget: HTMLElement = targetPanel;
  let propagationTarget: {
    panel: HTMLElement;
    config: PanelConfig;
    startSize: number;
    startPos: number;
  } | null = null;

  /** Detect axis from container at drag start (responsive to viewport changes).
   *  When vertical (mobile), switch resize target to the pane wrapper
   *  (e.g., .ws-worktree-pane) instead of the sidebar inside it.
   */
  const resolveAxis = (): AxisConfig => {
    const container = resizer.closest(".workspace-three-col") as HTMLElement;
    const detected = container
      ? detectAxis(container)
      : detectAxis(document.createElement("div"));

    if (detected.orientation === "vertical") {
      // On mobile, resize the pane wrapper (parent of sidebar), not the sidebar
      const paneWrapper = targetPanel.closest(
        ".ws-ai-pane, .ws-worktree-pane, .ws-viewer-pane",
      ) as HTMLElement;
      effectiveTarget = paneWrapper || targetPanel;
    } else {
      effectiveTarget = targetPanel;
    }

    return detected;
  };

  const disableTransitions = () => {
    document
      .querySelectorAll<HTMLElement>(".stx-shell-sidebar")
      .forEach((el) => {
        el.style.transition = "none";
      });
  };

  const enableTransitions = () => {
    document
      .querySelectorAll<HTMLElement>(".stx-shell-sidebar")
      .forEach((el) => {
        el.style.transition = "";
      });
  };

  const handleMouseDown = (e: MouseEvent) => {
    axis = resolveAxis();
    wasCollapsed = targetPanel.classList.contains("collapsed");
    propagationTarget = null;
    primaryCollapsed = false;

    if (config.fixedWidth) {
      isResizing = true;
      startPos = axis.pointerPos(e);
      startSize = axis.size(effectiveTarget);
      primaryCollapsed = true;

      document.body.style.cursor = axis.cursor;
      document.body.style.userSelect = "none";
      resizer.classList.add("active");
      disableTransitions();
      e.preventDefault();
      return;
    }

    if (wasCollapsed) {
      targetPanel.classList.remove("collapsed");
      // On vertical axis, minWidth (48px) is too small — use 1/4 of container as starting height
      const uncollapseSize =
        axis.orientation === "vertical"
          ? Math.max(
              150,
              axis.size(effectiveTarget.parentElement || effectiveTarget) / 4,
            )
          : config.minWidth;
      axis.setSize(effectiveTarget, uncollapseSize);
      axis.lockFlex(effectiveTarget);

      if (config.toggleButtonId) {
        const toggleBtn = document.getElementById(config.toggleButtonId);
        if (toggleBtn)
          updateToggleIcon(toggleBtn, config.resizeDirection, false);
      }

      if (config.collapseStorageKey)
        localStorage.setItem(config.collapseStorageKey, "false");
    }

    isResizing = true;
    startPos = axis.pointerPos(e);
    startSize = axis.size(effectiveTarget);
    document.body.style.cursor = axis.cursor;
    document.body.style.userSelect = "none";
    resizer.classList.add("active");
    effectiveTarget.dataset.wprDragging = "true";
    disableTransitions();
    e.preventDefault();
  };

  const handleMouseMove = (e: MouseEvent) => {
    if (!isResizing) return;

    if (config.fixedWidth && !propagationTarget) {
      const delta = axis.pointerPos(e) - startPos;
      if (Math.abs(delta) < 3) return;

      const isShrinking =
        config.resizeDirection === "left" ? delta < 0 : delta > 0;
      const curtainDir: "shrink-left" | "shrink-right" =
        config.resizeDirection === "left" ? "shrink-left" : "shrink-right";

      const adjacent = findAdjacentPanel(config, curtainDir, !isShrinking);
      if (adjacent) {
        if (!isShrinking && adjacent.panel.classList.contains("collapsed")) {
          adjacent.panel.classList.remove("collapsed");
          axis.setSize(adjacent.panel, adjacent.config.minWidth);
          axis.lockFlex(adjacent.panel);
          if (adjacent.config.toggleButtonId) {
            const toggleBtn = document.getElementById(
              adjacent.config.toggleButtonId,
            );
            if (toggleBtn)
              updateToggleIcon(
                toggleBtn,
                adjacent.config.resizeDirection,
                false,
              );
          }
          if (adjacent.config.collapseStorageKey) {
            localStorage.setItem(adjacent.config.collapseStorageKey, "false");
          }
        }
        propagationTarget = {
          panel: adjacent.panel,
          config: adjacent.config,
          startSize: axis.size(adjacent.panel),
          startPos: axis.pointerPos(e),
        };
      }
      return;
    }

    if (primaryCollapsed && !propagationTarget) return;

    if (propagationTarget) {
      const propDelta = axis.pointerPos(e) - propagationTarget.startPos;
      let propNewSize =
        config.resizeDirection === "left"
          ? propagationTarget.startSize + propDelta
          : propagationTarget.startSize - propDelta;

      const propMax = getMaxAllowedSize(propagationTarget.panel, axis);
      if (propNewSize > propMax) propNewSize = propMax;

      const propFlex = propagationTarget.panel.closest(
        ".workspace-three-col",
      ) as HTMLElement;
      if (propFlex) {
        const propSnaps = percentSnapPoints(axis.size(propFlex));
        const propSnap = magneticSnap(propNewSize, propSnaps);
        propNewSize = propSnap.value;
        if (propSnap.snapped) {
          resizer.classList.add("snapped");
        } else {
          resizer.classList.remove("snapped");
        }
      }

      if (propNewSize < COLLAPSE_SIZE) {
        collapsePanel(
          storagePrefix,
          propagationTarget.config,
          propagationTarget.panel,
          axis,
        );

        const dragDir =
          config.resizeDirection === "left" ? "shrink-left" : "shrink-right";
        const next = findAdjacentPanel(propagationTarget.config, dragDir);
        if (next) {
          propagationTarget = {
            panel: next.panel,
            config: next.config,
            startSize: axis.size(next.panel),
            startPos: axis.pointerPos(e),
          };
        } else {
          propagationTarget = null;
        }
        return;
      }

      axis.setSize(propagationTarget.panel, propNewSize);
      axis.lockFlex(propagationTarget.panel);
      return;
    }

    // Normal resize of the primary panel (effectiveTarget = pane wrapper on mobile)
    const delta = axis.pointerPos(e) - startPos;
    let newSize =
      config.resizeDirection === "left" ? startSize + delta : startSize - delta;

    const maxSize = getMaxAllowedSize(effectiveTarget, axis);
    if (newSize > maxSize) newSize = maxSize;

    const flexContainer = effectiveTarget.closest(
      ".workspace-three-col",
    ) as HTMLElement;
    if (flexContainer) {
      const snaps = percentSnapPoints(axis.size(flexContainer));
      const snapResult = magneticSnap(newSize, snaps);
      newSize = snapResult.value;
      if (snapResult.snapped) {
        resizer.classList.add("snapped");
      } else {
        resizer.classList.remove("snapped");
      }
    }

    // Smart collapse: if dragged below threshold, collapse and propagate
    if (newSize < COLLAPSE_SIZE) {
      primaryCollapsed = true;
      collapsePanel(storagePrefix, config, targetPanel, axis);

      const dragDir =
        config.resizeDirection === "left" ? "shrink-left" : "shrink-right";
      const adjacent = findAdjacentPanel(config, dragDir);
      if (adjacent) {
        propagationTarget = {
          panel: adjacent.panel,
          config: adjacent.config,
          startSize: axis.size(adjacent.panel),
          startPos: axis.pointerPos(e),
        };
      }
      return;
    }

    axis.setSize(effectiveTarget, newSize);
    axis.lockFlex(effectiveTarget);
  };

  const handleMouseUp = () => {
    if (!isResizing) return;
    isResizing = false;
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
    resizer.classList.remove("active");
    resizer.classList.remove("snapped");
    enableTransitions();

    requestAnimationFrame(() => {
      delete effectiveTarget.dataset.wprDragging;
    });

    if (propagationTarget) {
      const propSize = axis.size(propagationTarget.panel);
      if (propSize > COLLAPSE_SIZE + 10) {
        saveWidth(storagePrefix, propagationTarget.config, propSize);
      }
      propagationTarget = null;
    }

    if (targetPanel.classList.contains("collapsed")) {
      wasCollapsed = false;
      return;
    }

    const finalSize = axis.size(effectiveTarget);

    if (finalSize <= config.minWidth + 10) {
      collapsePanel(storagePrefix, config, targetPanel, axis);
    } else {
      saveWidth(storagePrefix, config, finalSize);
    }

    wasCollapsed = false;
  };

  // --- Touch event adapters (same logic, touch → mouse mapping) ---
  const handleTouchStart = (e: TouchEvent) => {
    if (e.touches.length !== 1) return;
    const touch = e.touches[0];
    handleMouseDown({
      clientX: touch.clientX,
      clientY: touch.clientY,
      preventDefault: () => e.preventDefault(),
    } as MouseEvent);
  };

  const handleTouchMove = (e: TouchEvent) => {
    if (!isResizing || e.touches.length < 1) return;
    e.preventDefault();
    const touch = e.touches[0];
    handleMouseMove({
      clientX: touch.clientX,
      clientY: touch.clientY,
    } as MouseEvent);
  };

  const handleTouchEnd = () => {
    handleMouseUp();
  };

  // Mouse events (desktop)
  resizer.addEventListener("mousedown", handleMouseDown);
  document.addEventListener("mousemove", handleMouseMove);
  document.addEventListener("mouseup", handleMouseUp);

  // Touch events (mobile) — passive: false to allow preventDefault
  resizer.addEventListener("touchstart", handleTouchStart, { passive: false });
  document.addEventListener("touchmove", handleTouchMove, { passive: false });
  document.addEventListener("touchend", handleTouchEnd, { passive: true });

  console.log(
    `[WorkspacePanelResizer] Initialized ${config.resizerId} (direction: ${config.resizeDirection}, touch: enabled)`,
  );
}
