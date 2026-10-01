/**
 * Tooltip — auto-positioned tooltip system using data-tooltip attributes.
 *
 * Usage:
 *   import { Tooltip } from 'scitex_sdk/ui/ts/app/tooltip';
 *   Tooltip.init();  // scans for [data-tooltip] elements
 *
 * HTML:
 *   <button data-tooltip="Save file">Save</button>
 *   <button data-tooltip="Delete" data-tooltip-position="top">Del</button>
 */

import { addDescribedBy, removeDescribedBy } from "../../_base/aria-describedby";
import type { TooltipConfig, TooltipPosition } from "./types";

const CLS = "stx-app-tooltip";
const MARGIN = 8;

/**
 * Id of the single shared tooltip node, referenced by the target's
 * `aria-describedby` while shown.
 *
 * ONE node is reused for every target, so only ONE element may reference it at
 * a time — which is already true, because only one tooltip is ever visible.
 * hideTooltip() removes the reference before currentTarget is cleared; leaving
 * it behind would point a still-focused control at a hidden node.
 */
const TOOLTIP_ID = "stx-app-tooltip-description";

let tooltipEl: HTMLDivElement | null = null;
let showTimeout: ReturnType<typeof setTimeout> | null = null;
let currentTarget: HTMLElement | null = null;

function getOrCreateTooltip(): HTMLDivElement {
  if (!tooltipEl) {
    tooltipEl = document.createElement("div");
    tooltipEl.className = CLS;
    tooltipEl.id = TOOLTIP_ID;
    tooltipEl.setAttribute("role", "tooltip");
    document.body.appendChild(tooltipEl);
  }
  return tooltipEl;
}

function bestPosition(
  target: DOMRect,
  preferred: TooltipPosition,
): TooltipPosition {
  if (preferred !== "auto") return preferred;

  const spaceAbove = target.top;
  const spaceBelow = window.innerHeight - target.bottom;
  const spaceLeft = target.left;
  const spaceRight = window.innerWidth - target.right;

  // Prefer bottom, then top, then right, then left
  if (spaceBelow >= 40) return "bottom";
  if (spaceAbove >= 40) return "top";
  if (spaceRight >= 100) return "right";
  if (spaceLeft >= 100) return "left";
  return "bottom";
}

function positionTooltip(
  tip: HTMLDivElement,
  target: DOMRect,
  pos: TooltipPosition,
): void {
  const tipRect = tip.getBoundingClientRect();

  let top = 0;
  let left = 0;

  switch (pos) {
    case "bottom":
      top = target.bottom + MARGIN;
      left = target.left + target.width / 2 - tipRect.width / 2;
      break;
    case "top":
      top = target.top - tipRect.height - MARGIN;
      left = target.left + target.width / 2 - tipRect.width / 2;
      break;
    case "right":
      top = target.top + target.height / 2 - tipRect.height / 2;
      left = target.right + MARGIN;
      break;
    case "left":
      top = target.top + target.height / 2 - tipRect.height / 2;
      left = target.left - tipRect.width - MARGIN;
      break;
  }

  // Clamp to viewport
  left = Math.max(4, Math.min(left, window.innerWidth - tipRect.width - 4));
  top = Math.max(4, Math.min(top, window.innerHeight - tipRect.height - 4));

  tip.style.top = `${top + window.scrollY}px`;
  tip.style.left = `${left + window.scrollX}px`;
}

function showTooltip(target: HTMLElement, config: TooltipConfig): void {
  const text = target.getAttribute("data-tooltip");
  if (!text) return;

  const tip = getOrCreateTooltip();
  tip.textContent = text;
  tip.style.display = "block";
  tip.style.opacity = "0";

  currentTarget = target;

  // The ASSISTIVE path. Everything else in this function is the visual one, and
  // for eighteen months that was all there was: the text lived in a data
  // attribute nothing exposes, so a screen reader got nothing from a tooltip.
  //
  // "last" because a tooltip DESCRIBES. Anything actionable — dim's "Sign in to
  // use this" — is added "first" by its own component, so the user hears what
  // they can DO before what the control WOULD do, whichever component ran
  // first. See _base/aria-describedby.
  addDescribedBy(target, TOOLTIP_ID, "last");

  // Position after content renders
  requestAnimationFrame(() => {
    const rect = target.getBoundingClientRect();
    const preferred =
      (target.getAttribute("data-tooltip-position") as TooltipPosition) ||
      config.position ||
      "auto";
    const pos = bestPosition(rect, preferred);
    positionTooltip(tip, rect, pos);
    tip.dataset.position = pos;
    tip.style.opacity = "1";
  });
}

function hideTooltip(): void {
  if (showTimeout) {
    clearTimeout(showTimeout);
    showTimeout = null;
  }
  // Drop the reference BEFORE clearing currentTarget — otherwise the target
  // keeps pointing at a node that is now hidden, and a still-focused control
  // describes itself with something nobody can see. Removes ONLY this
  // component's id: clearing the attribute would silently discard a
  // description another component owns, and the symptom (one description
  // instead of two) is invisible to anyone not listening for the missing one.
  if (currentTarget) {
    removeDescribedBy(currentTarget, TOOLTIP_ID);
  }
  if (tooltipEl) {
    tooltipEl.style.display = "none";
    tooltipEl.style.opacity = "0";
  }
  currentTarget = null;
}

export const Tooltip = {
  /** Initialize tooltip system. Call once. */
  init(config: TooltipConfig = {}): void {
    const delay = config.delay ?? 300;
    const root = config.root || document.body;

    root.addEventListener(
      "mouseenter",
      (e: Event) => {
        const target = (e.target as HTMLElement)?.closest?.(
          config.selector || "[data-tooltip]",
        ) as HTMLElement | null;
        if (!target) return;

        showTimeout = setTimeout(() => showTooltip(target, config), delay);
      },
      true,
    );

    root.addEventListener(
      "mouseleave",
      (e: Event) => {
        const target = (e.target as HTMLElement)?.closest?.(
          config.selector || "[data-tooltip]",
        );
        if (target) hideTooltip();
      },
      true,
    );

    // THE KEYBOARD PATH. Without these two, a tooltip reached only a user
    // holding a mouse: tab to the same control and there was nothing, no
    // visible tooltip and nothing in the accessibility tree either.
    //
    // focusin/focusout rather than focus/blur because those do not BUBBLE, and
    // this is a single delegated listener on the root — focus/blur here would
    // simply never fire for a descendant.
    //
    // No `delay` on the focus path, deliberately. The hover delay exists to
    // stop tooltips flickering as the pointer crosses a toolbar; keyboard focus
    // is a deliberate act with no such sweep, so the delay would only make the
    // control feel unresponsive to the users who most need the text.
    root.addEventListener(
      "focusin",
      (e: Event) => {
        const target = (e.target as HTMLElement)?.closest?.(
          config.selector || "[data-tooltip]",
        ) as HTMLElement | null;
        if (target) showTooltip(target, config);
      },
      true,
    );

    root.addEventListener(
      "focusout",
      (e: Event) => {
        const target = (e.target as HTMLElement)?.closest?.(
          config.selector || "[data-tooltip]",
        );
        if (target) hideTooltip();
      },
      true,
    );

    // Hide on scroll or resize
    window.addEventListener("scroll", hideTooltip, true);
    window.addEventListener("resize", hideTooltip);
  },

  /** Programmatically hide tooltip. */
  hide: hideTooltip,
};
