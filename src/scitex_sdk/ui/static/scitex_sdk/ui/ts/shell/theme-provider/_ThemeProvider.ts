/**
 * ThemeProvider — manages light/dark theme via data-theme attribute.
 *
 * Usage:
 *   import { ThemeProvider } from 'scitex_sdk/ui/ts/shell/theme-provider';
 *   const theme = new ThemeProvider({ defaultTheme: 'dark' });
 *   theme.toggle();
 */

import type { Theme, ThemeProviderConfig } from "./types";

const DEFAULT_STORAGE_KEY = "stx-theme";

export class ThemeProvider {
  private target: HTMLElement;
  private storageKey: string;
  private config: ThemeProviderConfig;

  constructor(config: ThemeProviderConfig = {}) {
    this.config = config;
    this.target = config.target ?? document.documentElement;
    this.storageKey = config.storageKey ?? DEFAULT_STORAGE_KEY;

    const stored = localStorage.getItem(this.storageKey) as Theme | null;
    const initial = stored ?? config.defaultTheme ?? "light";
    this.apply(initial);
  }

  getTheme(): Theme {
    return (this.target.getAttribute("data-theme") as Theme) ?? "light";
  }

  setTheme(theme: Theme): void {
    this.apply(theme);
  }

  toggle(): Theme {
    const next = this.getTheme() === "light" ? "dark" : "light";
    this.apply(next);
    return next;
  }

  destroy(): void {
    this.target.removeAttribute("data-theme");
  }

  private apply(theme: Theme): void {
    this.target.setAttribute("data-theme", theme);
    localStorage.setItem(this.storageKey, theme);
    this.config.onThemeChange?.(theme);
  }
}
