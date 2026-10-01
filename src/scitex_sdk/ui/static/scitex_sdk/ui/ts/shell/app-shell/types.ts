/**
 * Type definitions for the AppShell component.
 */

import type { BaseComponentConfig } from "../../_base/types";

export interface AppShellConfig extends BaseComponentConfig {
  /** Initial sidebar width in px (default: 250) */
  sidebarWidth?: number;
  /** Allow sidebar collapse (default: true) */
  collapsible?: boolean;
  /** Start collapsed (default: false) */
  startCollapsed?: boolean;
  /** Sidebar title text */
  sidebarTitle?: string;
  /** Sidebar title icon class (e.g. "fas fa-folder") */
  sidebarIcon?: string;
  /** Preset accent key (e.g. "writer", "figrecipe") */
  accent?: string;
  /** Custom accent color hex (overrides preset; user/creator configurable) */
  accentColor?: string;
  /** localStorage key for sidebar state */
  storageKey?: string;
  /** Called when sidebar toggles */
  onSidebarToggle?: (collapsed: boolean) => void;
}
