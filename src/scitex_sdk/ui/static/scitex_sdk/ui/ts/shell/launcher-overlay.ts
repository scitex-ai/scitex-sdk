/**
 * Launcher overlay — the collision runtime.
 *
 * Card: ui-shared-brand-dock-tour-primitives-20260917
 * SSOT: scitex-hub PR 923, docs/product/PRIVATE_BETA_LOGIN_TO_WOW.md §4
 *
 * §4: "An actionable control must never remain hidden behind it. Scroll the
 * control clear, collapse/move the launcher, or temporarily hide it. Do not
 * solve collisions with a permanent full-width spacer."
 *
 * WHY THIS IS A RUNTIME AND NOT A LAYOUT RULE. The band the shipped dock
 * reserves (`body { padding-bottom: <dock clearance> }`) makes the app surface
 * permanently shorter on every page and every screen, to protect a control that
 * is at most one gesture away from being covered. The expensive cost is paid
 * always; the rare case is what it buys. This module pays it the other way
 * round: the page owns the whole viewport, and the ONE moment that matters —
 * while a control has focus — is handled by moving something.
 *
 * ORDER OF ESCALATION, deliberately:
 *   1. scroll the control clear (cheapest, keeps the launcher where the user
 *      expects it, and is what a keyboard user needs);
 *   2. if it still intersects, retract the overlay (`data-stx-launcher-retracted`)
 *      until focus leaves. Nothing reserves space for it, so this is a state
 *      that ends, not a band that persists.
 *
 * The overlay is translucency, not pointer-events: an idle overlay is still
 * clickable, which is what makes it a launcher rather than a ribbon.
 *
 * Loaded as an IIFE bundle by a page that renders a launcher; self-guards when
 * there is none (no launcher in the DOM -> attaches nothing).
 */

/** The overlay itself. Hub owns the markup and may add its own class. */
export const LAUNCHER_OVERLAY_SELECTOR = ".stx-launcher-overlay, [data-stx-launcher-overlay]";

/** Set (briefly) while the overlay has to be out of the way — §4's "hide it". */
export const RETRACT_ATTRIBUTE = "data-stx-launcher-retracted";

/** Set on pointerdown, cleared on pointerup/cancel: §4's "touch/press" state.
 *  `:active` is unreliable for a press that travels, which is the normal case
 *  on a dock, and CSS cannot express "pressed" across the trip. */
export const PRESSED_ATTRIBUTE = "data-stx-launcher-pressed";

/** What counts as actionable. Focus in a container is not a collision. */
export const ACTIONABLE_SELECTOR =
  'a[href], button, [role="button"], input, select, textarea, summary, [tabindex]:not([tabindex="-1"])';

export interface LauncherOverlayOptions {
  /** Restrict to these overlays; default: every overlay in the document. */
  overlays?: Iterable<Element>;
  /** Called with the control that could not be cleared — for a host's telemetry. */
  onObscured?: (control: Element, overlay: Element) => void;
}

function overlaysIn(scope: ParentNode, given?: Iterable<Element>): Element[] {
  if (given) return Array.from(given);
  return Array.from(scope.querySelectorAll(LAUNCHER_OVERLAY_SELECTOR));
}

/** True when `control`'s box overlaps any overlay's box. */
export function intersectsLauncher(
  control: Element,
  overlays: Iterable<Element> = document.querySelectorAll(LAUNCHER_OVERLAY_SELECTOR),
): boolean {
  const c = control.getBoundingClientRect();
  if (c.width === 0 && c.height === 0) return false;
  for (const overlay of overlays) {
    const o = overlay.getBoundingClientRect();
    if (o.width === 0 && o.height === 0) continue;
    const separated =
      c.right <= o.left || c.left >= o.right || c.bottom <= o.top || c.top >= o.bottom;
    if (!separated) return true;
  }
  return false;
}

function retract(overlays: Element[], control: Element, onObscured?: LauncherOverlayOptions["onObscured"]): void {
  for (const overlay of overlays) {
    overlay.setAttribute(RETRACT_ATTRIBUTE, "true");
    onObscured?.(control, overlay);
  }
}

function restore(overlays: Element[]): void {
  for (const overlay of overlays) overlay.removeAttribute(RETRACT_ATTRIBUTE);
}

/**
 * Wire the overlay's interaction states and focus collision handling.
 * Returns a teardown function; a no-op when the document has no launcher.
 */
export function initLauncherOverlay(options: LauncherOverlayOptions = {}): () => void {
  if (typeof document === "undefined") return () => {};
  const overlays = overlaysIn(document, options.overlays);
  if (overlays.length === 0) return () => {};

  const pressedTargets = new Set<Element>();
  let retractedFor: Element | null = null;

  const overlayFor = (node: Element | null): Element | null => {
    if (!node) return null;
    return overlays.find((overlay) => overlay === node || overlay.contains(node)) ?? null;
  };

  const onPointerDown = (event: Event) => {
    const overlay = overlayFor(event.target as Element | null);
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

  const onFocusIn = (event: Event) => {
    const control = (event.target as Element | null)?.closest?.(ACTIONABLE_SELECTOR) ?? null;
    // The overlay's own controls cannot be "hidden behind" it.
    if (!control || overlayFor(control)) return;
    if (!intersectsLauncher(control, overlays)) {
      clearIfRetracted();
      return;
    }
    // 1. cheapest: bring the control into view.
    control.scrollIntoView?.({ block: "nearest", inline: "nearest" });
    // 2. then re-measure — scrolling is async for a smooth scroll, so this is
    //    one frame later, and only then is "still covered" a fact.
    requestAnimationFrame(() => {
      if (!intersectsLauncher(control, overlays)) {
        if (retractedFor === control) clearIfRetracted();
        return;
      }
      retract(overlays, control, options.onObscured);
      retractedFor = control;
    });
  };

  const onFocusOut = (event: Event) => {
    const next = (event as FocusEvent).relatedTarget as Element | null;
    if (next && overlayFor(next)) return; // moving INTO the launcher is not leaving
    clearIfRetracted();
  };

  // A retraction must not outlive the press that caused it either: a tap
  // outside while the overlay is retracted means the user is done with it.
  const onPointerDownAnywhere = (event: Event) => {
    const overlay = overlayFor(event.target as Element | null);
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

/** Manually retract/restore, for a host that hides the overlay itself. */
export const stxLauncherOverlay = {
  LAUNCHER_OVERLAY_SELECTOR,
  RETRACT_ATTRIBUTE,
  PRESSED_ATTRIBUTE,
  ACTIONABLE_SELECTOR,
  intersectsLauncher,
  initLauncherOverlay,
};

declare global {
  interface Window {
    stxLauncherOverlay?: typeof stxLauncherOverlay;
  }
}

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
