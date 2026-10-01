/**
 * Type definitions for the ThemeProvider component.
 */

export type Theme = "light" | "dark";

export interface ThemeProviderConfig {
  /** Initial theme (default: "light") */
  defaultTheme?: Theme;
  /** localStorage key for persistence (default: "stx-theme") */
  storageKey?: string;
  /** Target element for data-theme attribute (default: document.documentElement) */
  target?: HTMLElement;
  /** Called when theme changes */
  onThemeChange?: (theme: Theme) => void;
}
