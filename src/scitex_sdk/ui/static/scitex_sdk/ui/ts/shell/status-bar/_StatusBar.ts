/**
 * StatusBar — bottom bar with left/center/right sections.
 *
 * Usage:
 *   import { StatusBar } from 'scitex_sdk/ui/ts/shell/status-bar';
 *   const bar = new StatusBar({ container: '#status' });
 *   bar.setItems('left', [{ id: 'line', text: 'Ln 42, Col 8' }]);
 */

import { BaseComponent } from "../../_base/BaseComponent";
import type { StatusBarConfig, StatusBarSection, StatusItem } from "./types";

const CLS = "stx-shell-status-bar";

export class StatusBar extends BaseComponent<StatusBarConfig> {
  private sections: Record<StatusBarSection, HTMLElement>;
  private items: Record<StatusBarSection, StatusItem[]>;

  constructor(config: StatusBarConfig) {
    super(config);
    this.container.classList.add(CLS);

    this.sections = {
      left: this.createSection("left"),
      center: this.createSection("center"),
      right: this.createSection("right"),
    };

    this.container.appendChild(this.sections.left);
    this.container.appendChild(this.sections.center);
    this.container.appendChild(this.sections.right);

    this.items = {
      left: config.items?.left ?? [],
      center: config.items?.center ?? [],
      right: config.items?.right ?? [],
    };

    if (config.showThemeToggle) {
      const isDark =
        document.documentElement.getAttribute("data-theme") === "dark";
      this.items.right.push({
        id: "__theme-toggle",
        text: "",
        // fa-circle-half-stroke is an unambiguous two-tone semicircle
        // that signals a toggle. Previous fa-sun was often confused for
        // a gear; fa-moon alone didn't hint at the dual-state affordance.
        icon: "fas fa-circle-half-stroke",
        title: `Theme: ${isDark ? "dark" : "light"} (click to switch)`,
        onClick: () => this.toggleTheme(),
      });
    }

    this.renderAll();
  }

  setItems(section: StatusBarSection, items: StatusItem[]): void {
    this.items[section] = items;
    this.renderSection(section);
  }

  addItem(section: StatusBarSection, item: StatusItem): void {
    this.items[section].push(item);
    this.renderSection(section);
  }

  removeItem(id: string): void {
    for (const section of ["left", "center", "right"] as StatusBarSection[]) {
      const idx = this.items[section].findIndex((i) => i.id === id);
      if (idx !== -1) {
        this.items[section].splice(idx, 1);
        this.renderSection(section);
        return;
      }
    }
  }

  updateItem(id: string, updates: Partial<StatusItem>): void {
    for (const section of ["left", "center", "right"] as StatusBarSection[]) {
      const item = this.items[section].find((i) => i.id === id);
      if (item) {
        Object.assign(item, updates);
        this.renderSection(section);
        return;
      }
    }
  }

  override destroy(): void {
    this.container.classList.remove(CLS);
    super.destroy();
  }

  private toggleTheme(): void {
    const html = document.documentElement;
    const current = html.getAttribute("data-theme");
    const next = current === "dark" ? "light" : "dark";
    html.setAttribute("data-theme", next);
    try {
      localStorage.setItem("stx-theme", next);
    } catch {
      /* noop */
    }
    this.updateItem("__theme-toggle", {
      icon: "fas fa-circle-half-stroke",
      title: `Theme: ${next} (click to switch)`,
    });
  }

  private createSection(name: StatusBarSection): HTMLElement {
    const el = document.createElement("div");
    el.className = `${CLS}__${name}`;
    return el;
  }

  private renderAll(): void {
    this.renderSection("left");
    this.renderSection("center");
    this.renderSection("right");
  }

  private renderSection(section: StatusBarSection): void {
    const el = this.sections[section];
    el.innerHTML = "";

    for (const item of this.items[section]) {
      const node = item.onClick
        ? document.createElement("button")
        : document.createElement("span");

      node.className = item.onClick ? `${CLS}__btn` : `${CLS}__item`;
      node.dataset.id = item.id;
      if (item.title) node.title = item.title;

      if (item.icon) {
        const icon = document.createElement("i");
        icon.className = item.icon;
        node.appendChild(icon);
      }

      node.appendChild(document.createTextNode(item.text));

      if (item.onClick) {
        (node as HTMLButtonElement).addEventListener("click", item.onClick);
      }

      el.appendChild(node);
    }
  }
}
