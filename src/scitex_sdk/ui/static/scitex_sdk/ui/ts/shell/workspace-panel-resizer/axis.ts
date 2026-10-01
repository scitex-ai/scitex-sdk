/**
 * Axis abstraction for direction-agnostic resizing.
 *
 * Desktop (flex-direction: row)  → horizontal axis (width, clientX, col-resize)
 * Mobile  (flex-direction: column) → vertical axis (height, clientY, row-resize)
 *
 * The resizer auto-detects the axis from the container's computed flex-direction,
 * so all resizer logic works identically in both orientations — no ad-hoc patches.
 */

export interface AxisConfig {
  /** "horizontal" or "vertical" */
  orientation: "horizontal" | "vertical";
  /** CSS cursor to use while dragging */
  cursor: string;
  /** Get the pointer position from a MouseEvent or Touch */
  pointerPos(e: MouseEvent | Touch): number;
  /** Get the element's size along this axis */
  size(el: HTMLElement): number;
  /** Set the element's size along this axis */
  setSize(el: HTMLElement, px: number): void;
  /** Clear inline size on this axis */
  clearSize(el: HTMLElement): void;
  /** The CSS property name for size ("width" or "height") */
  sizeProp: "width" | "height";
  /** The CSS property name for max size ("maxWidth" or "maxHeight") */
  maxSizeProp: "maxWidth" | "maxHeight";
  /** Lock flex so the element doesn't resize with siblings */
  lockFlex(el: HTMLElement): void;
  /** Unlock flex to restore CSS-controlled sizing */
  unlockFlex(el: HTMLElement): void;
  /** Chevron classes for collapse direction */
  chevrons: {
    /** Icon class when panel is before resizer and collapsed */
    beforeCollapsed: string;
    /** Icon class when panel is before resizer and expanded */
    beforeExpanded: string;
    /** Icon class when panel is after resizer and collapsed */
    afterCollapsed: string;
    /** Icon class when panel is after resizer and expanded */
    afterExpanded: string;
  };
}

const HORIZONTAL: AxisConfig = {
  orientation: "horizontal",
  cursor: "col-resize",
  pointerPos: (e) => ("clientX" in e ? e.clientX : (e as Touch).clientX),
  size: (el) => el.offsetWidth,
  setSize: (el, px) => {
    el.style.width = `${px}px`;
  },
  clearSize: (el) => {
    el.style.width = "";
  },
  sizeProp: "width",
  maxSizeProp: "maxWidth",
  lockFlex: (el) => {
    el.style.flexShrink = "0";
    el.style.flexGrow = "0";
  },
  unlockFlex: (el) => {
    el.style.flexShrink = "";
    el.style.flexGrow = "";
  },
  chevrons: {
    beforeCollapsed: "fa-chevron-right",
    beforeExpanded: "fa-chevron-left",
    afterCollapsed: "fa-chevron-left",
    afterExpanded: "fa-chevron-right",
  },
};

const VERTICAL: AxisConfig = {
  orientation: "vertical",
  cursor: "row-resize",
  pointerPos: (e) => ("clientY" in e ? e.clientY : (e as Touch).clientY),
  size: (el) => el.offsetHeight,
  setSize: (el, px) => {
    // Must use !important to override mobile.css flex: 1 1 0% !important
    el.style.setProperty("height", `${px}px`, "important");
    el.style.setProperty("flex", `0 0 ${px}px`, "important");
  },
  clearSize: (el) => {
    el.style.height = "";
    el.style.removeProperty("flex");
  },
  sizeProp: "height",
  maxSizeProp: "maxHeight",
  lockFlex: (el) => {
    // Must use !important to override mobile.css flex: 1 1 0% !important
    el.style.setProperty("flex-shrink", "0", "important");
    el.style.setProperty("flex-grow", "0", "important");
  },
  unlockFlex: (el) => {
    el.style.removeProperty("flex-shrink");
    el.style.removeProperty("flex-grow");
    el.style.removeProperty("flex");
  },
  chevrons: {
    beforeCollapsed: "fa-chevron-down",
    beforeExpanded: "fa-chevron-up",
    afterCollapsed: "fa-chevron-up",
    afterExpanded: "fa-chevron-down",
  },
};

/**
 * Detect the resize axis from the container's flex-direction.
 * Falls back to horizontal if detection fails.
 */
export function detectAxis(container: HTMLElement): AxisConfig {
  const style = getComputedStyle(container);
  const dir = style.flexDirection;
  return dir === "column" || dir === "column-reverse" ? VERTICAL : HORIZONTAL;
}

/**
 * Get axis config by explicit name.
 * Use when you want to force a specific axis regardless of layout.
 */
export function getAxis(orientation: "horizontal" | "vertical"): AxisConfig {
  return orientation === "vertical" ? VERTICAL : HORIZONTAL;
}
