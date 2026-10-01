/* AUTO-GENERATED from ts/app/app-header/auto-mount.ts via esbuild — do not edit by hand. Rebuild: npx esbuild ts/app/app-header/auto-mount.ts --bundle --format=esm --outfile=js/app/app-header.js */
// src/scitex_ui/static/scitex_ui/ts/_base/BaseComponent.ts
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

// src/scitex_ui/static/scitex_ui/ts/app/app-header/types.ts
var APP_VERSION_ATTRIBUTE = "data-app-version";
var HEADER_ATTRIBUTE = "data-stx-app-header";
var APP_TITLE_ATTRIBUTE = "data-app-title";
function resolveAppVersion(root, explicit) {
  if (explicit != null && explicit.trim() !== "") return explicit.trim();
  const own = root.getAttribute(APP_VERSION_ATTRIBUTE);
  if (own && own.trim() !== "") return own.trim();
  const ancestor = root.closest(`[${APP_VERSION_ATTRIBUTE}]`);
  if (ancestor instanceof HTMLElement) {
    const value = ancestor.getAttribute(APP_VERSION_ATTRIBUTE);
    if (value && value.trim() !== "") return value.trim();
  }
  const documentRoot = root.ownerDocument?.documentElement;
  const host = documentRoot?.getAttribute(APP_VERSION_ATTRIBUTE);
  if (host && host.trim() !== "") return host.trim();
  return null;
}
function resolveAppTitle(root, explicit) {
  if (explicit != null && explicit.trim() !== "") return explicit.trim();
  const own = root.getAttribute(APP_TITLE_ATTRIBUTE);
  if (own && own.trim() !== "") return own.trim();
  const ancestor = root.closest(`[${APP_TITLE_ATTRIBUTE}]`);
  if (ancestor instanceof HTMLElement) {
    const value = ancestor.getAttribute(APP_TITLE_ATTRIBUTE);
    if (value && value.trim() !== "") return value.trim();
  }
  return "";
}
var SHELL_PROPS_META_NAME = "stx-app-shell";
function readShellProps(doc = document) {
  const meta = doc.querySelector(
    `meta[name="${SHELL_PROPS_META_NAME}"]`
  );
  if (!meta) return null;
  const raw = meta.getAttribute("content") ?? "";
  try {
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") {
      throw new TypeError("payload is not an object");
    }
    return parsed;
  } catch (error) {
    throw new Error(
      `AppHeader: <meta name="${SHELL_PROPS_META_NAME}"> carries an unreadable payload (${error.message}). Refusing to render a header that would silently drop the app's declared actions.`
    );
  }
}
function orderedActions(actions = []) {
  return actions.map((action, index) => ({ action, index })).sort((a, b) => {
    const byOrder = (a.action.order ?? 0) - (b.action.order ?? 0);
    return byOrder !== 0 ? byOrder : a.index - b.index;
  }).map((entry) => entry.action);
}

// src/scitex_ui/static/scitex_ui/ts/app/app-header/_AppHeader.ts
var CLS = "stx-app-header";
var APP_HEADER_COMMAND = "stx-app-header:command";
var AppHeader = class extends BaseComponent {
  /** The `<header>` element this component owns. */
  headerEl;
  /** Leaf title — a span (NOT a heading): a mounted leaf must not add a second H1. */
  titleEl;
  /** Version badge; `hidden` when the version is unknown. */
  versionEl;
  /** Canonical project-selector slot, or `null` for a user-scoped app. */
  projectSlot;
  /** App-specific actions slot. */
  actionsEl;
  /** The contract payload this header rendered from, when the page carried one. */
  shellProps;
  constructor(config) {
    super(config);
    const doc = this.container.ownerDocument ?? document;
    this.shellProps = config.shellProps ?? readShellProps(doc);
    this.headerEl = document.createElement("header");
    this.headerEl.className = CLS;
    this.titleEl = document.createElement("span");
    this.titleEl.className = `${CLS}__title`;
    this.titleEl.textContent = config.title ?? (this.shellProps?.title || resolveAppTitle(this.container)) ?? "";
    this.versionEl = document.createElement("span");
    this.versionEl.className = `${CLS}__version`;
    this.actionsEl = document.createElement("div");
    this.actionsEl.className = `${CLS}__actions`;
    this.headerEl.append(this.titleEl, this.versionEl);
    if (config.projectSlot ?? this.wantsProjectSlot()) {
      this.projectSlot = document.createElement("div");
      this.projectSlot.className = `${CLS}__slot--project-selector`;
      this.headerEl.appendChild(this.projectSlot);
    } else {
      this.projectSlot = null;
    }
    this.headerEl.appendChild(this.actionsEl);
    this.container.appendChild(this.headerEl);
    this.setVersion(
      config.version || this.shellProps?.version || resolveAppVersion(this.container)
    );
    for (const element of config.actions ?? []) this.actionsEl.appendChild(element);
    for (const action of orderedActions(this.shellProps?.actions)) {
      this.actionsEl.appendChild(this.buildAction(action));
    }
  }
  /**
   * The slot exists for a project-scoped app that declares a provider. With no
   * payload at all (an app driving the component directly) it stays, because
   * that is what the header template promises.
   */
  wantsProjectSlot() {
    if (!this.shellProps) return true;
    return this.shellProps.scope === "project" && Boolean(this.shellProps.project);
  }
  /**
   * One action control. A control that names NEITHER a command nor an href does
   * nothing and renders identically to a working one (the /apps/storage/
   * measurement), so it is refused here as well as at the writer.
   */
  buildAction(action) {
    if (!action.command && !action.href) {
      throw new Error(
        `AppHeader: action ${JSON.stringify(action.id)} names neither a command nor an href. A control that does nothing must not render.`
      );
    }
    let element;
    if (action.href) {
      const anchor = document.createElement("a");
      anchor.href = action.href;
      element = anchor;
    } else {
      const button = document.createElement("button");
      button.type = "button";
      element = button;
    }
    element.className = `${CLS}__action`;
    element.textContent = action.label;
    element.setAttribute("data-stx-action", action.id);
    if (action.command) {
      const command = action.command;
      element.setAttribute("data-stx-command", command);
      element.addEventListener("click", () => {
        this.emit(APP_HEADER_COMMAND, { command, action: action.id });
      });
    }
    return element;
  }
  /** Set the leaf title (the leaf owns the translation of what it passes). */
  setTitle(title) {
    this.titleEl.textContent = title;
  }
  /**
   * Set the version badge. An unknown/empty version HIDES the badge (it never
   * renders a placeholder): the element stays in place so a later
   * `setVersion()` reveals it without rebuilding the header row.
   */
  setVersion(version) {
    const resolved = (version ?? "").trim();
    if (resolved === "") {
      this.versionEl.hidden = true;
      this.versionEl.textContent = "";
      return;
    }
    this.versionEl.hidden = false;
    this.versionEl.textContent = `${this.config.versionPrefix ?? "v"}${resolved}`;
  }
  /** Append one app-specific action into the actions slot. */
  addAction(element) {
    this.actionsEl.appendChild(element);
  }
  destroy() {
    this.headerEl.remove();
    super.destroy();
  }
};

// src/scitex_ui/static/scitex_ui/ts/app/app-header/mount.ts
var MOUNTED_ATTRIBUTE = "data-stx-app-header-mounted";
var instances = [];
function mountAppHeader(root = document, options = {}) {
  const mounted = [];
  for (const element of Array.from(
    root.querySelectorAll(`[${HEADER_ATTRIBUTE}]`)
  )) {
    if (element.hasAttribute(MOUNTED_ATTRIBUTE)) continue;
    element.setAttribute(MOUNTED_ATTRIBUTE, "");
    const header = new AppHeader({ ...options, container: element });
    instances.push(header);
    mounted.push(header);
  }
  return mounted;
}
function getAppHeader() {
  return instances.length === 1 ? instances[0] : null;
}
var stxAppHeader = {
  mount: mountAppHeader,
  get: getAppHeader
};

// src/scitex_ui/static/scitex_ui/ts/app/app-header/auto-mount.ts
window.stxAppHeader = stxAppHeader;
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => mountAppHeader());
} else {
  mountAppHeader();
}
export {
  APP_HEADER_COMMAND,
  APP_TITLE_ATTRIBUTE,
  APP_VERSION_ATTRIBUTE,
  AppHeader,
  HEADER_ATTRIBUTE,
  SHELL_PROPS_META_NAME,
  orderedActions,
  readShellProps,
  resolveAppTitle,
  resolveAppVersion
};
