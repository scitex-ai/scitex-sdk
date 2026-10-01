/**
 * AppLauncher — the standard app-navigation pattern (compass L624).
 *
 * A grid-glyph trigger opens a panel of app tiles in a CSS grid. Picking a
 * tile emits `stx-app-launcher:select` (bubbles, detail `{appId, appName}`)
 * and the CONSUMING APP performs the navigation — the component owns the
 * pattern, not the data or the routes.
 *
 * Tiles are real `<button>`s, so keyboard operability (Tab, Enter, Space)
 * comes from the platform. The grid glyph (田) is a single character in the
 * platform font — no icon font, no SVG asset, no bundler step.
 *
 * Usage:
 *   import { AppLauncher, APP_LAUNCHER_SELECT } from
 *     "scitex_sdk/ui/ts/app/app-launcher";
 *
 *   const launcher = new AppLauncher({
 *     container: "#app-launcher",
 *     apps: [
 *       { id: "writer", name: "Writer" },
 *       { id: "scholar", name: "Scholar", icon: "📚" },
 *       { id: "figrecipe", name: "FigRecipe", description: "figures" },
 *       { id: "console", name: "Console", icon: "💻" },
 *       { id: "storage", name: "Storage", icon: "🗄️" },
 *     ],
 *     current: "writer",
 *   });
 *   launcher.container.addEventListener(APP_LAUNCHER_SELECT, (e) => {
 *     const { appId, appName } =
 *       (e as CustomEvent<AppLauncherSelectDetail>).detail;
 *     window.location.href = "/" + appId + "/";
 *   });
 */

import { BaseComponent } from "../../_base/BaseComponent";
import { shellTranslate } from "../../_base/i18n";
import type {
  AppLauncherConfig,
  AppOption,
} from "./types";

const CLS = "stx-app-launcher";

/** Event emitted on the container when the user selects an app tile. */
export const APP_LAUNCHER_SELECT = "stx-app-launcher:select";

export class AppLauncher extends BaseComponent<AppLauncherConfig> {
  private trigger: HTMLButtonElement;
  private label: HTMLElement;
  private panel: HTMLElement;
  private grid: HTMLElement;
  private open = false;
  private outsideClickHandler: (e: MouseEvent) => void;
  private keyHandler: (e: KeyboardEvent) => void;

  constructor(config: AppLauncherConfig) {
    super(config);

    this.container.className = CLS;

    this.trigger = document.createElement("button");
    this.trigger.type = "button";
    this.trigger.className = `${CLS}__trigger`;
    this.trigger.setAttribute("aria-haspopup", "true");

    const glyph = document.createElement("span");
    glyph.className = `${CLS}__glyph`;
    glyph.textContent = "\u7530";
    glyph.setAttribute("aria-hidden", "true");
    this.trigger.appendChild(glyph);

    this.label = document.createElement("span");
    this.label.className = `${CLS}__label`;
    this.label.textContent = config.label ?? shellTranslate("apps");
    this.trigger.appendChild(this.label);

    this.panel = document.createElement("div");
    this.panel.className = `${CLS}__panel`;

    this.grid = document.createElement("div");
    this.grid.className = `${CLS}__grid`;
    this.grid.setAttribute("role", "list");
    this.panel.appendChild(this.grid);
    this.renderGrid();

    this.container.appendChild(this.trigger);
    this.container.appendChild(this.panel);

    this.trigger.addEventListener("click", () => this.toggle());

    this.outsideClickHandler = (e: MouseEvent): void => {
      if (!this.container.contains(e.target as Node)) {
        this.close();
      }
    };
    this.keyHandler = (e: KeyboardEvent): void => {
      if (e.key === "Escape") {
        this.close();
      }
    };
    document.addEventListener("click", this.outsideClickHandler);
    document.addEventListener("keydown", this.keyHandler);
  }

  /** (Re)build the tile grid from config.apps. */
  private renderGrid(): void {
    this.grid.innerHTML = "";
    if (this.config.apps.length === 0) {
      const empty = document.createElement("div");
      empty.className = `${CLS}__empty`;
      empty.textContent = shellTranslate("noAppsAvailable");
      this.grid.appendChild(empty);
      return;
    }
    for (const app of this.config.apps) {
      const tile = document.createElement("button");
      tile.type = "button";
      const isCurrent = this.config.current === app.id;
      tile.className = isCurrent
        ? `${CLS}__tile ${CLS}__tile--current`
        : `${CLS}__tile`;
      if (isCurrent) {
        tile.setAttribute("aria-current", "true");
      }
      tile.setAttribute("role", "listitem");
      tile.setAttribute("aria-label", app.name);

      const icon = document.createElement("span");
      icon.className = `${CLS}__tile-icon`;
      icon.textContent = app.icon ?? "\u7530";
      icon.setAttribute("aria-hidden", "true");
      tile.appendChild(icon);

      const name = document.createElement("span");
      name.className = `${CLS}__tile-label`;
      name.textContent = app.name;
      tile.appendChild(name);

      if (app.description) {
        const desc = document.createElement("span");
        desc.className = `${CLS}__tile-desc`;
        desc.textContent = app.description;
        tile.appendChild(desc);
      }

      tile.addEventListener("click", () => this.select(app));
      this.grid.appendChild(tile);
    }
  }

  /** Open or close the panel. */
  toggle(): void {
    if (this.open) {
      this.close();
    } else {
      this.open = true;
      this.container.classList.add(`${CLS}--open`);
      this.trigger.setAttribute("aria-expanded", "true");
    }
  }

  close(): void {
    if (!this.open) {
      return;
    }
    this.open = false;
    this.container.classList.remove(`${CLS}--open`);
    this.trigger.setAttribute("aria-expanded", "false");
  }

  /** Select an app: emit the event and close. The app does the rest. */
  private select(app: AppOption): void {
    this.close();
    this.emit(APP_LAUNCHER_SELECT, {
      appId: app.id,
      appName: app.name,
    });
  }

  override destroy(): void {
    document.removeEventListener("click", this.outsideClickHandler);
    document.removeEventListener("keydown", this.keyHandler);
    super.destroy();
  }
}
