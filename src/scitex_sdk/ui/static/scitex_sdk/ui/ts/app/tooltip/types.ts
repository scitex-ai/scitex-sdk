/**
 * Type definitions for the Tooltip component.
 */

export type TooltipPosition = "top" | "bottom" | "left" | "right" | "auto";

export interface TooltipConfig {
  /** Default position (default: "auto" — avoids viewport edges) */
  position?: TooltipPosition;
  /** Delay in ms before showing (default: 300) */
  delay?: number;
  /** CSS selector for elements with data-tooltip attribute (default: "[data-tooltip]") */
  selector?: string;
  /** Root element to observe (default: document.body) */
  root?: HTMLElement;
}
