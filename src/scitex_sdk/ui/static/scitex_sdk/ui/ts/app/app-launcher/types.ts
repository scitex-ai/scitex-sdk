/**
 * Type definitions for the AppLauncher component.
 *
 * The AppLauncher is the standard app-navigation pattern (compass L624):
 * a grid-glyph trigger opens a panel of app tiles; picking one emits the
 * select event and the CONSUMING APP performs the navigation.
 *
 * The component owns the pattern — the markup, the BEM vocabulary, the grid
 * layout, and the event contract. It does NOT own the app list (which apps
 * exist is the app's) or the routing (the destination of a tile is the
 * app's). A launcher that hardcodes destinations would couple every adopter
 * to one app's route table.
 */

import type { BaseComponentConfig } from "../../_base/types";

export interface AppOption {
  /** Stable app identifier (passed back via the select event). */
  id: string;
  /** Display name (what the user sees on the tile). */
  name: string;
  /** Optional icon: a single character, emoji, or inline SVG string.
   * Defaults to the grid glyph 田 if omitted. */
  icon?: string;
  /** Optional short description line under the name. */
  description?: string;
}

/** Detail of the `stx-app-launcher:select` event. */
export interface AppLauncherSelectDetail {
  appId: string;
  appName: string;
}

export interface AppLauncherConfig extends BaseComponentConfig {
  /** The apps this launcher offers, in display order. The DATA comes from
   * the app — it knows its own app list and permissions; this component
   * owns the pattern, not the data. */
  apps: AppOption[];
  /** Trigger label. Defaults to "Apps". */
  label?: string;
  /** Currently active app id, if any — highlighted on the trigger. */
  current?: string | null;
}
