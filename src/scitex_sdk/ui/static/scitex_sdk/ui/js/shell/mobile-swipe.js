/* AUTO-GENERATED from ts/shell/mobile-swipe.ts via esbuild — do not edit by hand. Rebuild: npx esbuild ts/shell/mobile-swipe.ts --bundle --format=iife --outfile=js/shell/mobile-swipe.js */
"use strict";
(() => {
  // ts/shell/mobile-swipe.ts
  var SWIPE_THRESHOLD = 40;
  var MOBILE_QUERY = "(max-width: 768px)";
  var MOBILE_COLLAPSE_KEY = "scitex-mobile-collapsed-panes";
  var isMobile = false;
  var SIDEBAR_IDS = [
    "stx-shell-ai-panel",
    "ws-worktree-sidebar",
    "ws-viewer-sidebar",
    "ws-apps-sidebar"
  ];
  var touchStartY = 0;
  var touchFingers = 0;
  var swipeTarget = null;
  function findParentSidebar(el) {
    return el.closest(".stx-shell-sidebar");
  }
  function onTouchStart(e) {
    if (!isMobile) return;
    touchFingers = e.touches.length;
    if (touchFingers >= 2) {
      touchStartY = e.touches[0].clientY;
      swipeTarget = findParentSidebar(e.target);
    }
  }
  function onTouchMove(e) {
    if (!isMobile || touchFingers < 2 || !swipeTarget) return;
    if (e.touches.length >= 2) {
      const dx = Math.abs(e.touches[0].clientX - e.touches[1].clientX);
      const dy = Math.abs(e.touches[0].clientY - e.touches[1].clientY);
      if (dx > 30) return;
      if (dy > 10) e.preventDefault();
    }
  }
  function onTouchEnd(e) {
    if (!isMobile || touchFingers < 2 || !swipeTarget) {
      touchFingers = 0;
      swipeTarget = null;
      return;
    }
    const dy = e.changedTouches[0].clientY - touchStartY;
    if (Math.abs(dy) > SWIPE_THRESHOLD) {
      if (dy < 0) {
        if (!swipeTarget.classList.contains("collapsed")) {
          const toggleBtn = swipeTarget.querySelector(".panel-toggle-btn");
          if (toggleBtn) toggleBtn.click();
          console.log(`[MobileGesture] Collapsed: ${swipeTarget.id}`);
          saveMobileCollapseState();
        }
      } else {
        if (swipeTarget.classList.contains("collapsed")) {
          const toggleBtn = swipeTarget.querySelector(".panel-toggle-btn");
          if (toggleBtn) toggleBtn.click();
          console.log(`[MobileGesture] Expanded: ${swipeTarget.id}`);
          saveMobileCollapseState();
        }
      }
    }
    touchFingers = 0;
    swipeTarget = null;
  }
  function saveMobileCollapseState() {
    const collapsed = [];
    SIDEBAR_IDS.forEach((id) => {
      const el = document.getElementById(id);
      if (el?.classList.contains("collapsed")) {
        collapsed.push(id);
      }
    });
    localStorage.setItem(MOBILE_COLLAPSE_KEY, JSON.stringify(collapsed));
  }
  function restoreMobileCollapseState() {
    try {
      const saved = localStorage.getItem(MOBILE_COLLAPSE_KEY);
      if (!saved) return;
      const collapsed = JSON.parse(saved);
      collapsed.forEach((id) => {
        const el = document.getElementById(id);
        if (el) {
          el.classList.add("collapsed");
          console.log(`[MobileGesture] Restored collapsed: ${id}`);
        }
      });
    } catch {
    }
  }
  function onDblClick(e) {
    if (!isMobile) return;
    const header = e.target.closest(
      ".stx-shell-sidebar__header"
    );
    if (!header) return;
    const sidebar = header.closest(".stx-shell-sidebar");
    if (!sidebar) return;
    const toggleBtn = sidebar.querySelector(".panel-toggle-btn");
    if (toggleBtn) {
      toggleBtn.click();
      saveMobileCollapseState();
      console.log(
        `[MobileGesture] Double-click toggle: ${sidebar.id} \u2192 ${sidebar.classList.contains("collapsed") ? "collapsed" : "expanded"}`
      );
    }
  }
  var vResTarget = null;
  var vResStartY = 0;
  var vResPrevPane = null;
  var vResNextPane = null;
  var vResPrevStartH = 0;
  var vResNextStartH = 0;
  function findPaneWrapper(el) {
    return el.closest(
      ".ws-ai-pane, .ws-worktree-pane, .ws-viewer-pane, .ws-module-pane"
    );
  }
  function findAdjacentPanes(resizer) {
    const pane = findPaneWrapper(resizer);
    if (!pane) return null;
    const isPaneClass = (el) => el.classList.contains("ws-ai-pane") || el.classList.contains("ws-worktree-pane") || el.classList.contains("ws-viewer-pane") || el.classList.contains("ws-module-pane");
    let prevPane = pane.previousElementSibling;
    while (prevPane && !isPaneClass(prevPane)) {
      prevPane = prevPane.previousElementSibling;
    }
    if (!prevPane) return null;
    return { prev: prevPane, next: pane };
  }
  function onVerticalResizeStart(e) {
    if (!isMobile) return;
    const target = e.target;
    const resizer = target.closest(".panel-resizer");
    const header = target.closest(".stx-shell-sidebar__header");
    const dragSource = resizer || header;
    if (!dragSource) return;
    let panes = null;
    if (resizer) {
      panes = findAdjacentPanes(resizer);
    } else if (header) {
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
    [vResPrevPane, vResNextPane].forEach((pane) => {
      const sidebar = pane.querySelector(
        ".stx-shell-sidebar.collapsed"
      );
      if (sidebar) sidebar.classList.remove("collapsed");
    });
    e.preventDefault();
    document.body.style.cursor = "row-resize";
    document.body.style.userSelect = "none";
    console.log(
      `[MobileResize] Start: prev=${vResPrevPane.id}(${vResPrevStartH}px) next=${vResNextPane.id}(${vResNextStartH}px)`
    );
  }
  function onVerticalResizeMove(e) {
    if (!vResTarget || !vResPrevPane || !vResNextPane) return;
    e.preventDefault();
    const clientY = "touches" in e ? e.touches[0].clientY : e.clientY;
    const MIN_PANE = 44;
    let dy = clientY - vResStartY;
    const maxUp = -(vResPrevStartH - MIN_PANE);
    const maxDown = vResNextStartH - MIN_PANE;
    dy = Math.max(maxUp, Math.min(maxDown, dy));
    const newPrevH = vResPrevStartH + dy;
    const newNextH = vResNextStartH - dy;
    vResPrevPane.style.setProperty("height", newPrevH + "px", "important");
    vResPrevPane.style.setProperty("flex", `0 0 ${newPrevH}px`, "important");
    vResNextPane.style.setProperty("height", newNextH + "px", "important");
    vResNextPane.style.setProperty("flex", `0 0 ${newNextH}px`, "important");
  }
  function onVerticalResizeEnd() {
    if (!vResTarget) return;
    const collapseIfSmall = (pane) => {
      if (!pane || pane.offsetHeight >= 60) return;
      const sidebar = pane.querySelector(".stx-shell-sidebar");
      if (sidebar) {
        sidebar.classList.add("collapsed");
        pane.style.removeProperty("height");
        pane.style.removeProperty("flex");
        saveMobileCollapseState();
      }
    };
    collapseIfSmall(vResPrevPane);
    collapseIfSmall(vResNextPane);
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
  function onMediaChange(mql) {
    if (mql.matches && !isMobile) {
      isMobile = true;
      enableMobile();
    } else if (!mql.matches && isMobile) {
      isMobile = false;
      disableMobile();
    }
  }
  function enableMobile() {
    console.log("[MobileGesture] Enabling vertical layout gestures");
    const container = document.getElementById("workspace-three-col");
    if (!container) return;
    const paneSelectors = ".ws-ai-pane, .ws-worktree-pane, .ws-viewer-pane, .ws-module-pane";
    container.querySelectorAll(paneSelectors).forEach((pane) => {
      pane.style.removeProperty("flex");
      pane.style.removeProperty("height");
    });
    container.querySelectorAll(".stx-shell-sidebar.collapsed").forEach((panel) => {
      panel.classList.remove("collapsed");
    });
    restoreMobileCollapseState();
    container.addEventListener("touchstart", onTouchStart, { passive: true });
    container.addEventListener("touchmove", onTouchMove, { passive: false });
    container.addEventListener("touchend", onTouchEnd, { passive: true });
    container.addEventListener("dblclick", onDblClick);
    const dragTargets = container.querySelectorAll(
      ".panel-resizer, .stx-shell-sidebar__header"
    );
    dragTargets.forEach((el) => {
      el.addEventListener("mousedown", onVerticalResizeStart);
      el.addEventListener("touchstart", onVerticalResizeStart, {
        passive: false
      });
      if (el.classList.contains("stx-shell-sidebar__header")) {
        el.style.cursor = "row-resize";
      }
    });
    document.addEventListener("mousemove", onVerticalResizeMove);
    document.addEventListener("mouseup", onVerticalResizeEnd);
    document.addEventListener(
      "touchmove",
      onVerticalResizeMove,
      { passive: false }
    );
    document.addEventListener("touchend", onVerticalResizeEnd);
  }
  function disableMobile() {
    const container = document.getElementById("workspace-three-col");
    if (!container) return;
    container.removeEventListener("touchstart", onTouchStart);
    container.removeEventListener("touchmove", onTouchMove);
    container.removeEventListener("touchend", onTouchEnd);
    container.removeEventListener("dblclick", onDblClick);
    container.querySelectorAll(".panel-resizer, .stx-shell-sidebar__header").forEach((el) => {
      el.removeEventListener(
        "mousedown",
        onVerticalResizeStart
      );
      el.removeEventListener(
        "touchstart",
        onVerticalResizeStart
      );
      if (el.classList.contains("stx-shell-sidebar__header")) {
        el.style.cursor = "";
      }
    });
    document.removeEventListener(
      "mousemove",
      onVerticalResizeMove
    );
    document.removeEventListener("mouseup", onVerticalResizeEnd);
    document.removeEventListener(
      "touchmove",
      onVerticalResizeMove
    );
    document.removeEventListener("touchend", onVerticalResizeEnd);
    const paneSelectors = ".ws-ai-pane, .ws-worktree-pane, .ws-viewer-pane, .ws-module-pane";
    container.querySelectorAll(paneSelectors).forEach((pane) => {
      pane.style.removeProperty("flex");
      pane.style.removeProperty("height");
    });
  }
  function init() {
    const container = document.getElementById("workspace-three-col");
    if (!container) return;
    const mql = window.matchMedia(MOBILE_QUERY);
    console.log(
      `[MobileGesture] Init: viewport ${window.innerWidth}x${window.innerHeight}, mobile=${mql.matches}`
    );
    onMediaChange(mql);
    mql.addEventListener("change", onMediaChange);
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
