/**
 * AppShell — workspace layout with sidebar + content slots.
 *
 * Usage:
 *   import { AppShell } from 'scitex_sdk/ui/ts/shell/app-shell';
 *   const shell = new AppShell({
 *     container: '#app',
 *     sidebarTitle: 'Files',
 *     accent: 'figrecipe',        // preset
 *     accentColor: '#7c5cbf',     // or custom hex (overrides preset)
 *   });
 *   shell.sidebarContent.appendChild(myFileBrowser);
 *   shell.mainContent.appendChild(myEditor);
 */

import { BaseComponent } from "../../_base/BaseComponent";
import type { AppShellConfig } from "./types";
import { Sidebar } from "./_Sidebar";

export class AppShell extends BaseComponent<AppShellConfig> {
  private sidebar: Sidebar;
  private mainEl: HTMLElement;
  readonly sidebarContent: HTMLElement;
  readonly mainContent: HTMLElement;

  constructor(config: AppShellConfig) {
    super(config);
    this.container.classList.add("stx-shell-layout");

    this.sidebar = new Sidebar({
      width: config.sidebarWidth ?? 250,
      collapsible: config.collapsible ?? true,
      startCollapsed: config.startCollapsed ?? false,
      title: config.sidebarTitle ?? "Sidebar",
      icon: config.sidebarIcon ?? "",
      storageKey: config.storageKey ?? "stx-sidebar-state",
      onToggle: config.onSidebarToggle,
    });
    this.sidebarContent = this.sidebar.contentSlot;
    this.container.appendChild(this.sidebar.element);

    this.mainEl = document.createElement("main");
    this.mainEl.className = "stx-shell-content";

    // Accent: custom color takes priority over preset key
    if (config.accentColor) {
      this.setAccentColor(config.accentColor);
    } else if (config.accent) {
      this.mainEl.setAttribute("data-app-accent", config.accent);
    }

    this.mainContent = this.mainEl;
    this.container.appendChild(this.mainEl);
  }

  /** Set preset accent key (e.g. "writer", "figrecipe"). */
  setAccent(accent: string): void {
    this.mainEl.removeAttribute("data-app-accent-custom");
    this.mainEl.setAttribute("data-app-accent", accent);
    this.mainEl.style.removeProperty("--stx-app-accent");
  }

  /** Set custom accent color hex (user/creator configurable). */
  setAccentColor(color: string): void {
    this.mainEl.removeAttribute("data-app-accent");
    this.mainEl.setAttribute("data-app-accent-custom", color);
    this.mainEl.style.setProperty("--stx-app-accent", color);
  }

  collapseSidebar(): void {
    this.sidebar.collapse();
  }

  expandSidebar(): void {
    this.sidebar.expand();
  }

  toggleSidebar(): void {
    this.sidebar.toggle();
  }

  isSidebarCollapsed(): boolean {
    return this.sidebar.isCollapsed();
  }

  override destroy(): void {
    this.container.classList.remove("stx-shell-layout");
    super.destroy();
  }
}
