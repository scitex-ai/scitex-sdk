/**
 * Type definitions for the StatusBar component.
 */

import type { BaseComponentConfig } from "../../_base/types";

export type StatusBarSection = "left" | "center" | "right";

export interface StatusItem {
  id: string;
  text: string;
  icon?: string;
  onClick?: () => void;
  title?: string;
}

export interface StatusBarConfig extends BaseComponentConfig {
  items?: {
    left?: StatusItem[];
    center?: StatusItem[];
    right?: StatusItem[];
  };
  /** Show a theme toggle button in the right section (default: false) */
  showThemeToggle?: boolean;
}
