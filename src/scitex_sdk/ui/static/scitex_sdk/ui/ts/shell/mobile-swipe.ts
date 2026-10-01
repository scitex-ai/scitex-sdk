/**
 * Mobile Vertical Layout — Pane Collapse Gestures.
 *
 * On mobile (<=768px), workspace panes stack vertically.
 * This module adds:
 *  - Two-finger swipe up on any pane → collapse (shrink to header)
 *  - Two-finger swipe down on collapsed pane → expand
 *  - Double-click on pane header → toggle collapse
 *
 * Single-finger scroll is unaffected (normal content scrolling).
 */

const SWIPE_THRESHOLD = 40; // px — minimum vertical distance to trigger
const MOBILE_QUERY = "(max-width: 768px)";
const MOBILE_COLLAPSE_KEY = "scitex-mobile-collapsed-panes";

let isMobile = false;

/** Sidebar ID → pane wrapper mapping */
const SIDEBAR_IDS = [
  "stx-shell-ai-panel",
  "ws-worktree-sidebar",
  "ws-viewer-sidebar",
  "ws-apps-sidebar",
];

// --- Two-finger swipe tracking ---
let touchStartY = 0;
let touchFingers = 0;
let swipeTarget: HTMLElement | null = null;

function findParentSidebar(el: HTMLElement): HTMLElement | null {
  return el.closest<HTMLElement>(".stx-shell-sidebar");
}

function onTouchStart(e: TouchEvent): void {
  if (!isMobile) return;
  touchFingers = e.touches.length;
  if (touchFingers >= 2) {
    touchStartY = e.touches[0].clientY;
    swipeTarget = findParentSidebar(e.target as HTMLElement);
  }
}

function onTouchMove(e: TouchEvent): void {
  if (!isMobile || touchFingers < 2 || !swipeTarget) return;
  // Allow pinch zoom (two fingers spreading apart) — only prevent vertical two-finger swipe
  if (e.touches.length >= 2) {
    const dx = Math.abs(e.touches[0].clientX - e.touches[1].clientX);
    const dy = Math.abs(e.touches[0].clientY - e.touches[1].clientY);
    // If fingers are spreading (pinch zoom), don't prevent default
    if (dx > 30) return;
    // Only prevent if it's a vertical two-finger swipe
    if (dy > 10) e.preventDefault();
  }
}

function onTouchEnd(e: TouchEvent): void {
  if (!isMobile || touchFingers < 2 || !swipeTarget) {
    touchFingers = 0;
    swipeTarget = null;
    return;
  }

  const dy = e.changedTouches[0].clientY - touchStartY;

  if (Math.abs(dy) > SWIPE_THRESHOLD) {
    if (dy < 0) {
      // Swipe up → collapse
      if (!swipeTarget.classList.contains("collapsed")) {
        const toggleBtn =
          swipeTarget.querySelector<HTMLElement>(".panel-toggle-btn");
        if (toggleBtn) toggleBtn.click();
        console.log(`[MobileGesture] Collapsed: ${swipeTarget.id}`);
        saveMobileCollapseState();
      }
    } else {
      // Swipe down → expand
      if (swipeTarget.classList.contains("collapsed")) {
        const toggleBtn =
          swipeTarget.querySelector<HTMLElement>(".panel-toggle-btn");
        if (toggleBtn) toggleBtn.click();
        console.log(`[MobileGesture] Expanded: ${swipeTarget.id}`);
        saveMobileCollapseState();
      }
    }
  }

  touchFingers = 0;
  swipeTarget = null;
}

// --- Persist collapse state ---

function saveMobileCollapseState(): void {
  const collapsed: string[] = [];
  SIDEBAR_IDS.forEach((id) => {
    const el = document.getElementById(id);
    if (el?.classList.contains("collapsed")) {
      collapsed.push(id);
    }
  });
  localStorage.setItem(MOBILE_COLLAPSE_KEY, JSON.stringify(collapsed));
}

function restoreMobileCollapseState(): void {
  try {
    const saved = localStorage.getItem(MOBILE_COLLAPSE_KEY);
    if (!saved) return;
    const collapsed: string[] = JSON.parse(saved);
    collapsed.forEach((id) => {
      const el = document.getElementById(id);
      if (el) {
        el.classList.add("collapsed");
        console.log(`[MobileGesture] Restored collapsed: ${id}`);
      }
    });
  } catch {
    // Ignore parse errors
  }
}

// --- Double-click on pane header → toggle collapse ---

function onDblClick(e: MouseEvent): void {
  if (!isMobile) return;
  const header = (e.target as HTMLElement).closest<HTMLElement>(
    ".stx-shell-sidebar__header",
  );
  if (!header) return;

  const sidebar = header.closest<HTMLElement>(".stx-shell-sidebar");
  if (!sidebar) return;

  const toggleBtn = sidebar.querySelector<HTMLElement>(".panel-toggle-btn");
  if (toggleBtn) {
    toggleBtn.click();
    saveMobileCollapseState();
    console.log(
      `[MobileGesture] Double-click toggle: ${sidebar.id} → ${sidebar.classList.contains("collapsed") ? "collapsed" : "expanded"}`,
    );
  }
}

// --- Reciprocal vertical resize (mobile only) ---
// Resizes BOTH the pane above and below a resizer simultaneously.
// The axis-agnostic resizer only handles one pane; on mobile vertical
// layout, dragging the border between two panes must grow one and shrink
// the other. This handler works with both mouse and touch events.

let vResTarget: HTMLElement | null = null;
let vResStartY = 0;
let vResPrevPane: HTMLElement | null = null;
let vResNextPane: HTMLElement | null = null;
let vResPrevStartH = 0;
let vResNextStartH = 0;

function findPaneWrapper(el: HTMLElement): HTMLElement | null {
  return el.closest<HTMLElement>(
    ".ws-ai-pane, .ws-worktree-pane, .ws-viewer-pane, .ws-module-pane",
  );
}

function findAdjacentPanes(
  resizer: HTMLElement,
): { prev: HTMLElement; next: HTMLElement } | null {
  // The resizer is inside a sidebar inside a pane wrapper.
  // Find the pane wrapper, then get the previous/next sibling pane wrappers.
  const pane = findPaneWrapper(resizer);
  if (!pane) return null;

  // The resizer is at the TOP of its pane (first child in sidebar HTML).
  // On mobile vertical layout, it sits at the border between the PREVIOUS
  // pane and THIS pane. So: prev = previous sibling pane, next = this pane.
  const isPaneClass = (el: Element) =>
    el.classList.contains("ws-ai-pane") ||
    el.classList.contains("ws-worktree-pane") ||
    el.classList.contains("ws-viewer-pane") ||
    el.classList.contains("ws-module-pane");

  let prevPane = pane.previousElementSibling as HTMLElement | null;
  while (prevPane && !isPaneClass(prevPane)) {
    prevPane = prevPane.previousElementSibling as HTMLElement | null;
  }

  if (!prevPane) return null;
  return { prev: prevPane, next: pane };
}

function onVerticalResizeStart(e: MouseEvent | TouchEvent): void {
  if (!isMobile) return;

  // Accept both .panel-resizer and .stx-shell-sidebar__header as drag sources
  const target = e.target as HTMLElement;
  const resizer = target.closest<HTMLElement>(".panel-resizer");
  const header = target.closest<HTMLElement>(".stx-shell-sidebar__header");
  const dragSource = resizer || header;
  if (!dragSource) return;

  // For headers, find the pane wrapper directly
  let panes: { prev: HTMLElement; next: HTMLElement } | null = null;
  if (resizer) {
    panes = findAdjacentPanes(resizer);
  } else if (header) {
    // Header drag: this pane is "next", previous sibling pane is "prev"
    const paneWrapper = findPaneWrapper(header);
    if (paneWrapper) {
      panes = findAdjacentPanes(header);
    }
  }
  if (!panes) return;

  vResTarget = dragSource;
  vResPrevPane = panes.prev;
  vResNextPane = panes.next;

  const clientY = "touches" in e ? e.touches[0].clientY : e.clientY;
  vResStartY = clientY;
  vResPrevStartH = vResPrevPane.offsetHeight;
  vResNextStartH = vResNextPane.offsetHeight;

  // Uncollapse sidebars so content becomes visible during drag.
  // Don't change heights here — let mousemove handle all sizing
  // so the border always follows the cursor with no jump.
  [vResPrevPane, vResNextPane].forEach((pane) => {
    const sidebar = pane.querySelector<HTMLElement>(
      ".stx-shell-sidebar.collapsed",
    );
    if (sidebar) sidebar.classList.remove("collapsed");
  });

  e.preventDefault();
  document.body.style.cursor = "row-resize";
  document.body.style.userSelect = "none";
  console.log(
    `[MobileResize] Start: prev=${vResPrevPane.id}(${vResPrevStartH}px) next=${vResNextPane.id}(${vResNextStartH}px)`,
  );
}

function onVerticalResizeMove(e: MouseEvent | TouchEvent): void {
  if (!vResTarget || !vResPrevPane || !vResNextPane) return;
  e.preventDefault();

  const clientY = "touches" in e ? e.touches[0].clientY : e.clientY;
  // Clamp delta so neither pane goes below 44px
  const MIN_PANE = 44;
  let dy = clientY - vResStartY;
  const maxUp = -(vResPrevStartH - MIN_PANE); // max drag up
  const maxDown = vResNextStartH - MIN_PANE; // max drag down
  dy = Math.max(maxUp, Math.min(maxDown, dy));

  const newPrevH = vResPrevStartH + dy;
  const newNextH = vResNextStartH - dy;

  vResPrevPane.style.setProperty("height", newPrevH + "px", "important");
  vResPrevPane.style.setProperty("flex", `0 0 ${newPrevH}px`, "important");
  vResNextPane.style.setProperty("height", newNextH + "px", "important");
  vResNextPane.style.setProperty("flex", `0 0 ${newNextH}px`, "important");
}

function onVerticalResizeEnd(): void {
  if (!vResTarget) return;

  // Collapse panes dragged below 60px
  const collapseIfSmall = (pane: HTMLElement | null) => {
    if (!pane || pane.offsetHeight >= 60) return;
    const sidebar = pane.querySelector<HTMLElement>(".stx-shell-sidebar");
    if (sidebar) {
      sidebar.classList.add("collapsed");
      pane.style.removeProperty("height");
      pane.style.removeProperty("flex");
      saveMobileCollapseState();
    }
  };
  collapseIfSmall(vResPrevPane);
  collapseIfSmall(vResNextPane);

  // Convert pixel sizes to flex ratios so panes stay proportional
  // and never overflow the viewport. Use the current heights as flex-grow values.
  if (vResPrevPane && vResPrevPane.offsetHeight >= 60) {
    const h = vResPrevPane.offsetHeight;
    vResPrevPane.style.setProperty("flex", `${h} 1 0%`, "important");
    vResPrevPane.style.removeProperty("height");
  }
  if (vResNextPane && vResNextPane.offsetHeight >= 60) {
    const h = vResNextPane.offsetHeight;
    vResNextPane.style.setProperty("flex", `${h} 1 0%`, "important");
    vResNextPane.style.removeProperty("height");
  }

  document.body.style.cursor = "";
  document.body.style.userSelect = "";

  vResTarget = null;
  vResPrevPane = null;
  vResNextPane = null;
}

// --- Media query listener ---

function onMediaChange(mql: MediaQueryList | MediaQueryListEvent): void {
  if (mql.matches && !isMobile) {
    isMobile = true;
    enableMobile();
  } else if (!mql.matches && isMobile) {
    isMobile = false;
    disableMobile();
  }
}

function enableMobile(): void {
  console.log("[MobileGesture] Enabling vertical layout gestures");

  const container = document.getElementById("workspace-three-col");
  if (!container) return;

  // Clear only mobile-specific inline styles from pane WRAPPERS (not sidebars).
  // Pane wrappers get inline flex/height from mobile drag — clear on re-init.
  // Do NOT touch sidebar inline styles — desktop resizer depends on them.
  const paneSelectors =
    ".ws-ai-pane, .ws-worktree-pane, .ws-viewer-pane, .ws-module-pane";
  container.querySelectorAll<HTMLElement>(paneSelectors).forEach((pane) => {
    pane.style.removeProperty("flex");
    pane.style.removeProperty("height");
  });

  // First: uncollapse all panels (clear desktop collapse state)
  container
    .querySelectorAll<HTMLElement>(".stx-shell-sidebar.collapsed")
    .forEach((panel) => {
      panel.classList.remove("collapsed");
    });

  // Then: restore mobile-specific collapse preferences
  restoreMobileCollapseState();

  container.addEventListener("touchstart", onTouchStart, { passive: true });
  container.addEventListener("touchmove", onTouchMove, { passive: false });
  container.addEventListener("touchend", onTouchEnd, { passive: true });
  container.addEventListener("dblclick", onDblClick);

  // Reciprocal vertical resize — mouse + touch on panel resizers AND headers
  const dragTargets = container.querySelectorAll<HTMLElement>(
    ".panel-resizer, .stx-shell-sidebar__header",
  );
  dragTargets.forEach((el) => {
    el.addEventListener("mousedown", onVerticalResizeStart as EventListener);
    el.addEventListener("touchstart", onVerticalResizeStart as EventListener, {
      passive: false,
    });
    // Visual hint: headers are draggable on mobile
    if (el.classList.contains("stx-shell-sidebar__header")) {
      el.style.cursor = "row-resize";
    }
  });
  document.addEventListener("mousemove", onVerticalResizeMove as EventListener);
  document.addEventListener("mouseup", onVerticalResizeEnd);
  document.addEventListener(
    "touchmove",
    onVerticalResizeMove as EventListener,
    { passive: false },
  );
  document.addEventListener("touchend", onVerticalResizeEnd);
}

function disableMobile(): void {
  const container = document.getElementById("workspace-three-col");
  if (!container) return;

  container.removeEventListener("touchstart", onTouchStart);
  container.removeEventListener("touchmove", onTouchMove);
  container.removeEventListener("touchend", onTouchEnd);
  container.removeEventListener("dblclick", onDblClick);

  // Remove mobile drag listeners from headers and resizers
  container
    .querySelectorAll<HTMLElement>(".panel-resizer, .stx-shell-sidebar__header")
    .forEach((el) => {
      el.removeEventListener(
        "mousedown",
        onVerticalResizeStart as EventListener,
      );
      el.removeEventListener(
        "touchstart",
        onVerticalResizeStart as EventListener,
      );
      if (el.classList.contains("stx-shell-sidebar__header")) {
        el.style.cursor = "";
      }
    });
  document.removeEventListener(
    "mousemove",
    onVerticalResizeMove as EventListener,
  );
  document.removeEventListener("mouseup", onVerticalResizeEnd);
  document.removeEventListener(
    "touchmove",
    onVerticalResizeMove as EventListener,
  );
  document.removeEventListener("touchend", onVerticalResizeEnd);

  // Clear mobile inline styles from pane wrappers
  const paneSelectors =
    ".ws-ai-pane, .ws-worktree-pane, .ws-viewer-pane, .ws-module-pane";
  container.querySelectorAll<HTMLElement>(paneSelectors).forEach((pane) => {
    pane.style.removeProperty("flex");
    pane.style.removeProperty("height");
  });
}

// --- Init ---

export function init(): void {
  const container = document.getElementById("workspace-three-col");
  if (!container) return;

  const mql = window.matchMedia(MOBILE_QUERY);
  console.log(
    `[MobileGesture] Init: viewport ${window.innerWidth}x${window.innerHeight}, mobile=${mql.matches}`,
  );
  onMediaChange(mql);
  mql.addEventListener("change", onMediaChange);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
