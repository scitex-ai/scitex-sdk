/* AUTO-GENERATED from ts/shell/launcher-overlay.ts via esbuild — do not edit by hand. Rebuild: npx esbuild ts/shell/launcher-overlay.ts --bundle --format=iife --outfile=js/shell/launcher-overlay.js */
"use strict";
(() => {
  // ts/shell/launcher-overlay.ts
  var LAUNCHER_OVERLAY_SELECTOR = ".stx-launcher-overlay, [data-stx-launcher-overlay]";
  var RETRACT_ATTRIBUTE = "data-stx-launcher-retracted";
  var PRESSED_ATTRIBUTE = "data-stx-launcher-pressed";
  var ACTIONABLE_SELECTOR = 'a[href], button, [role="button"], input, select, textarea, summary, [tabindex]:not([tabindex="-1"])';
  function overlaysIn(scope, given) {
    if (given) return Array.from(given);
    return Array.from(scope.querySelectorAll(LAUNCHER_OVERLAY_SELECTOR));
  }
  function intersectsLauncher(control, overlays = document.querySelectorAll(LAUNCHER_OVERLAY_SELECTOR)) {
    const c = control.getBoundingClientRect();
    if (c.width === 0 && c.height === 0) return false;
    for (const overlay of overlays) {
      const o = overlay.getBoundingClientRect();
      if (o.width === 0 && o.height === 0) continue;
      const separated = c.right <= o.left || c.left >= o.right || c.bottom <= o.top || c.top >= o.bottom;
      if (!separated) return true;
    }
    return false;
  }
  function retract(overlays, control, onObscured) {
    for (const overlay of overlays) {
      overlay.setAttribute(RETRACT_ATTRIBUTE, "true");
      onObscured?.(control, overlay);
    }
  }
  function restore(overlays) {
    for (const overlay of overlays) overlay.removeAttribute(RETRACT_ATTRIBUTE);
  }
  function initLauncherOverlay(options = {}) {
    if (typeof document === "undefined") return () => {
    };
    const overlays = overlaysIn(document, options.overlays);
    if (overlays.length === 0) return () => {
    };
    const pressedTargets = /* @__PURE__ */ new Set();
    let retractedFor = null;
    const overlayFor = (node) => {
      if (!node) return null;
      return overlays.find((overlay) => overlay === node || overlay.contains(node)) ?? null;
    };
    const onPointerDown = (event) => {
      const overlay = overlayFor(event.target);
      if (!overlay) return;
      overlay.setAttribute(PRESSED_ATTRIBUTE, "true");
      pressedTargets.add(overlay);
    };
    const onPointerUp = () => {
      for (const overlay of pressedTargets) overlay.removeAttribute(PRESSED_ATTRIBUTE);
      pressedTargets.clear();
    };
    const clearIfRetracted = () => {
      if (retractedFor === null) return;
      restore(overlays);
      retractedFor = null;
    };
    const onFocusIn = (event) => {
      const control = event.target?.closest?.(ACTIONABLE_SELECTOR) ?? null;
      if (!control || overlayFor(control)) return;
      if (!intersectsLauncher(control, overlays)) {
        clearIfRetracted();
        return;
      }
      control.scrollIntoView?.({ block: "nearest", inline: "nearest" });
      requestAnimationFrame(() => {
        if (!intersectsLauncher(control, overlays)) {
          if (retractedFor === control) clearIfRetracted();
          return;
        }
        retract(overlays, control, options.onObscured);
        retractedFor = control;
      });
    };
    const onFocusOut = (event) => {
      const next = event.relatedTarget;
      if (next && overlayFor(next)) return;
      clearIfRetracted();
    };
    const onPointerDownAnywhere = (event) => {
      const overlay = overlayFor(event.target);
      if (!overlay) clearIfRetracted();
    };
    document.addEventListener("pointerdown", onPointerDown, true);
    document.addEventListener("pointerdown", onPointerDownAnywhere, true);
    document.addEventListener("pointerup", onPointerUp, true);
    document.addEventListener("pointercancel", onPointerUp, true);
    document.addEventListener("focusin", onFocusIn, true);
    document.addEventListener("focusout", onFocusOut, true);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown, true);
      document.removeEventListener("pointerdown", onPointerDownAnywhere, true);
      document.removeEventListener("pointerup", onPointerUp, true);
      document.removeEventListener("pointercancel", onPointerUp, true);
      document.removeEventListener("focusin", onFocusIn, true);
      document.removeEventListener("focusout", onFocusOut, true);
      onPointerUp();
      clearIfRetracted();
    };
  }
  var stxLauncherOverlay = {
    LAUNCHER_OVERLAY_SELECTOR,
    RETRACT_ATTRIBUTE,
    PRESSED_ATTRIBUTE,
    ACTIONABLE_SELECTOR,
    intersectsLauncher,
    initLauncherOverlay
  };
  if (typeof window !== "undefined") {
    window.stxLauncherOverlay = stxLauncherOverlay;
    const autoInit = () => {
      initLauncherOverlay();
    };
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", autoInit);
    } else {
      autoInit();
    }
  }
})();
