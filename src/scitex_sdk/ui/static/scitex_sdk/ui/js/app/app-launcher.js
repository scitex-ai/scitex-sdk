/* AUTO-GENERATED from ts/app/app-launcher/index.ts via esbuild — do not edit by hand. Rebuild: npx esbuild ts/app/app-launcher/index.ts --bundle --format=esm --outfile=js/app/app-launcher.js */

// ts/_base/BaseComponent.ts
var BaseComponent = class {
  container;
  config;
  constructor(config) {
    this.config = config;
    const el = typeof config.container === "string" ? document.querySelector(config.container) : config.container;
    if (!el) {
      throw new Error(
        `${this.constructor.name}: container not found: ${config.container}`
      );
    }
    this.container = el;
  }
  /** Emit a custom event on the container. */
  emit(name, detail) {
    this.container.dispatchEvent(
      new CustomEvent(name, { detail, bubbles: true })
    );
  }
  /** Destroy the component and clean up DOM. */
  destroy() {
    this.container.innerHTML = "";
  }
};

// ts/_base/i18n.ts
var SHELL_STRINGS = {
  en: {
    apps: "Apps",
    noAppsAvailable: "No apps available",
    selectProject: "Select project",
    noProjects: "No projects"
  },
  ja: {
    apps: "\u30A2\u30D7\u30EA",
    noAppsAvailable: "\u5229\u7528\u53EF\u80FD\u306A\u30A2\u30D7\u30EA\u304C\u3042\u308A\u307E\u305B\u3093",
    selectProject: "\u30D7\u30ED\u30B8\u30A7\u30AF\u30C8\u3092\u9078\u629E\u3057\u3066\u304F\u3060\u3055\u3044",
    noProjects: "\u30D7\u30ED\u30B8\u30A7\u30AF\u30C8\u304C\u3042\u308A\u307E\u305B\u3093"
  }
};
function normalize(lang) {
  if (!lang) return "en";
  const code = lang.trim().toLowerCase();
  if (code === "ja" || code.startsWith("ja-")) return "ja";
  return "en";
}
function shellTranslate(key, doc = document) {
  const lang = normalize(doc?.documentElement?.lang);
  return SHELL_STRINGS[lang][key] ?? SHELL_STRINGS.en[key];
}

// ts/app/app-launcher/_AppLauncher.ts
var CLS = "stx-app-launcher";
var APP_LAUNCHER_SELECT = "stx-app-launcher:select";
var AppLauncher = class extends BaseComponent {
  trigger;
  label;
  panel;
  grid;
  open = false;
  outsideClickHandler;
  keyHandler;
  constructor(config) {
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
    this.outsideClickHandler = (e) => {
      if (!this.container.contains(e.target)) {
        this.close();
      }
    };
    this.keyHandler = (e) => {
      if (e.key === "Escape") {
        this.close();
      }
    };
    document.addEventListener("click", this.outsideClickHandler);
    document.addEventListener("keydown", this.keyHandler);
  }
  /** (Re)build the tile grid from config.apps. */
  renderGrid() {
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
      tile.className = isCurrent ? `${CLS}__tile ${CLS}__tile--current` : `${CLS}__tile`;
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
  toggle() {
    if (this.open) {
      this.close();
    } else {
      this.open = true;
      this.container.classList.add(`${CLS}--open`);
      this.trigger.setAttribute("aria-expanded", "true");
    }
  }
  close() {
    if (!this.open) {
      return;
    }
    this.open = false;
    this.container.classList.remove(`${CLS}--open`);
    this.trigger.setAttribute("aria-expanded", "false");
  }
  /** Select an app: emit the event and close. The app does the rest. */
  select(app) {
    this.close();
    this.emit(APP_LAUNCHER_SELECT, {
      appId: app.id,
      appName: app.name
    });
  }
  destroy() {
    document.removeEventListener("click", this.outsideClickHandler);
    document.removeEventListener("keydown", this.keyHandler);
    super.destroy();
  }
};
export {
  APP_LAUNCHER_SELECT,
  AppLauncher
};
