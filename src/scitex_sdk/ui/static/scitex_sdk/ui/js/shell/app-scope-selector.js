/* AUTO-GENERATED from ts/shell/app-scope-selector.ts via esbuild — do not edit by hand. Rebuild: npm run build:ui -- --only js/shell/app-scope-selector.js */

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

// ts/_base/gettext.ts
var JS_CATALOG_ELEMENT_PREFIX = "scitex-i18n-catalog-";
var state = null;
function installCatalog(payload) {
  const current = state ?? { entries: {}, plural: null };
  state = {
    entries: { ...current.entries, ...payload.catalog },
    plural: payload.plural ?? current.plural
  };
}
function loadCatalogsFromDocument(doc) {
  const elements = doc.querySelectorAll(
    `script[type="application/json"][id^="${JS_CATALOG_ELEMENT_PREFIX}"]`
  );
  for (const element of Array.from(elements)) {
    installCatalog(JSON.parse(element.textContent || "{}"));
  }
}
function activeCatalog() {
  if (state === null) {
    state = { entries: {}, plural: null };
    if (typeof document !== "undefined") loadCatalogsFromDocument(document);
  }
  return state;
}
function gettext(msgid) {
  const entry = activeCatalog().entries[msgid];
  if (entry === void 0) return msgid;
  const translated = typeof entry === "string" ? entry : entry[0];
  return translated || msgid;
}

// ts/_base/i18n.ts
var SHELL_STRINGS = {
  en: {
    apps: "Apps",
    noAppsAvailable: "No apps available",
    selectProject: "Select project",
    noProjects: "No projects",
    allProjects: "All Projects",
    scopeSelectionFailed: "Could not select scope"
  },
  ja: {
    apps: "\u30A2\u30D7\u30EA",
    noAppsAvailable: "\u5229\u7528\u53EF\u80FD\u306A\u30A2\u30D7\u30EA\u304C\u3042\u308A\u307E\u305B\u3093",
    selectProject: "\u30D7\u30ED\u30B8\u30A7\u30AF\u30C8\u3092\u9078\u629E\u3057\u3066\u304F\u3060\u3055\u3044",
    noProjects: "\u30D7\u30ED\u30B8\u30A7\u30AF\u30C8\u304C\u3042\u308A\u307E\u305B\u3093",
    allProjects: "\u3059\u3079\u3066\u306E\u30D7\u30ED\u30B8\u30A7\u30AF\u30C8",
    scopeSelectionFailed: "\u30B9\u30B3\u30FC\u30D7\u3092\u9078\u629E\u3067\u304D\u307E\u305B\u3093\u3067\u3057\u305F"
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

// ts/app/project-selector/fuzzy.ts
var WORD_BOUNDARY = /[\s/_\-.]/;
function fuzzyScore(query, text) {
  const needle = query.trim().toLowerCase();
  if (needle === "") return 0;
  const haystack = text.toLowerCase();
  let score = 0;
  let from = 0;
  let previous = -2;
  for (const char of needle) {
    const index = haystack.indexOf(char, from);
    if (index === -1) return null;
    if (index === previous + 1) score += 5;
    if (index === 0) score += 8;
    else if (WORD_BOUNDARY.test(haystack[index - 1])) score += 4;
    score -= Math.min(index - from, 3);
    previous = index;
    from = index + 1;
  }
  if (haystack.includes(needle)) score += 10;
  return score - haystack.length * 0.01;
}
function fuzzyFilter(items, query, textOf) {
  if (query.trim() === "") return [...items];
  return items.map((item, order) => ({ item, order, score: fuzzyScore(query, textOf(item)) })).filter((entry) => entry.score !== null).sort((a, b) => b.score - a.score || a.order - b.order).map((entry) => entry.item);
}

// ts/shell/keymap/_registry.ts
var CommandRegistry = class {
  commands = /* @__PURE__ */ new Map();
  /** The active page/app mode, or null when none is active (global only). */
  mode = null;
  /** Register or REPLACE a command. Returns false when the ID is taken by a
   *  DIFFERENT definition (a re-registration with the same ID is allowed —
   *  it is how an app updates its own command without clearing the world). */
  set(def) {
    const existing = this.commands.get(def.id);
    if (existing && existing !== def) {
      this.commands.set(def.id, def);
      return false;
    }
    this.commands.set(def.id, def);
    return true;
  }
  /** Unregister by ID. Returns true if something was removed. */
  unset(id) {
    return this.commands.delete(id);
  }
  /** True if a command with this ID is registered (regardless of mode). */
  has(id) {
    return this.commands.has(id);
  }
  /** Look up a command, reporting whether it is active in the current mode. */
  get(id) {
    const def = this.commands.get(id);
    if (!def) return null;
    return { def, active: this.isActive(def) };
  }
  /** All registered command IDs, sorted — a stable introspection surface. */
  ids() {
    return [...this.commands.keys()].sort();
  }
  /**
   * The full introspection model for the help UI / agent: every command with
   * its label, group, current-mode activeness, and the bindings that point at
   * it (resolved by the caller, since bindings live in the Keymap, not here).
   */
  list() {
    return this.ids().map((id) => {
      const def = this.commands.get(id);
      return {
        id,
        label: def.label,
        group: def.group,
        active: this.isActive(def),
        modes: def.modes ? [...def.modes].sort() : null
      };
    });
  }
  /** Activate a page/app mode. Global commands stay active; mode-scoped
   *  commands become active only when their mode matches. */
  setMode(mode) {
    this.mode = mode;
  }
  get currentMode() {
    return this.mode;
  }
  isActive(def) {
    if (!def.modes) return true;
    return this.mode !== null && def.modes.has(this.mode);
  }
  run(id, ...dispatch) {
    const def = this.commands.get(id);
    if (!def || !this.isActive(def)) return false;
    const consumed = def.action(dispatch[1]);
    return consumed !== false;
  }
};
var globalRegistry = new CommandRegistry();

// ts/app/project-selector/_ProjectSelector.ts
var CLS = "stx-app-project-selector";
var PROJECT_SELECTOR_CHANGE = "stx-project-selector:change";
var PROJECT_SELECTOR_SELECT = "project-selector:select";
var instanceCount = 0;
function translate(msgid, shellKey) {
  const translated = gettext(msgid);
  if (translated !== msgid || !shellKey) return translated;
  return shellTranslate(shellKey);
}
var ProjectSelector = class extends BaseComponent {
  /** Settles once the provider's listing has been rendered (immediately without one). */
  ready;
  commands;
  selectCommandId;
  selectCommand;
  projects;
  current;
  filtered = [];
  allowUserScope = false;
  legacyPersistenceExpected;
  pending = false;
  generation = 0;
  destroyed = false;
  selectionError;
  activeIndex = 0;
  status = "ready";
  uid;
  trigger;
  label;
  panel;
  search = null;
  list;
  open = false;
  outsideClickHandler;
  keyHandler;
  constructor(config) {
    super(config);
    this.commands = config.commands ?? new CommandRegistry();
    this.selectCommandId = config.selectCommandId ?? PROJECT_SELECTOR_SELECT;
    if (!this.selectCommandId || this.commands.has(this.selectCommandId)) {
      throw new Error(`project selector command already registered: ${this.selectCommandId}`);
    }
    this.selectCommand = { id: this.selectCommandId, label: gettext("Select project"), action: (payload) => this.select(payload) };
    this.uid = "stx-project-picker-" + ++instanceCount;
    this.projects = this.validProjects(config.projects ?? []);
    this.legacyPersistenceExpected = config.provider?.rememberProject !== void 0;
    this.allowUserScope = config.allowUserScope === true && typeof config.provider?.rememberScope === "function";
    this.current = this.choice(config.current, config.currentScope);
    this.commands.set(this.selectCommand);
    this.container.className = CLS;
    this.trigger = document.createElement("button");
    this.trigger.type = "button";
    this.trigger.className = `${CLS}__trigger`;
    this.trigger.setAttribute("aria-haspopup", "listbox");
    this.trigger.setAttribute("aria-expanded", "false");
    this.label = document.createElement("span");
    this.label.className = `${CLS}__current`;
    this.trigger.appendChild(this.label);
    this.panel = document.createElement("div");
    this.panel.className = `${CLS}__panel`;
    this.list = document.createElement("div");
    this.list.className = `${CLS}__list`;
    this.list.id = `${this.uid}-list`;
    this.list.setAttribute("role", "listbox");
    if (config.searchable !== false) {
      this.search = document.createElement("input");
      this.search.type = "search";
      this.search.className = `${CLS}__search`;
      this.search.placeholder = gettext("Search projects");
      this.search.setAttribute("aria-label", gettext("Search projects"));
      this.search.setAttribute("role", "combobox");
      this.search.setAttribute("aria-autocomplete", "list");
      this.search.setAttribute("aria-controls", this.list.id);
      this.search.setAttribute("autocomplete", "off");
      this.search.addEventListener("input", () => {
        this.activeIndex = 0;
        this.renderList();
      });
      this.search.addEventListener("keydown", (e) => this.onSearchKey(e));
      this.panel.appendChild(this.search);
    }
    this.panel.appendChild(this.list);
    this.selectionError = document.createElement("div");
    this.selectionError.className = `${CLS}__empty`;
    this.selectionError.setAttribute("role", "status");
    this.selectionError.hidden = true;
    this.container.appendChild(this.trigger);
    this.container.appendChild(this.panel);
    if (this.allowUserScope || this.legacyPersistenceExpected) this.container.appendChild(this.selectionError);
    this.trigger.addEventListener("click", () => this.toggle());
    this.trigger.addEventListener("keydown", (e) => {
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        this.show();
      }
    });
    this.outsideClickHandler = (e) => {
      if (!this.container.contains(e.target)) this.close();
    };
    this.keyHandler = (e) => {
      if (e.key === "Escape" && this.open) {
        this.close();
        this.trigger.focus?.();
      }
    };
    document.addEventListener("click", this.outsideClickHandler);
    document.addEventListener("keydown", this.keyHandler);
    this.ready = config.provider ? this.load() : Promise.resolve();
    this.renderLabel();
    this.renderList();
  }
  /** The selected project, or null. */
  getCurrent() {
    const project = this.current?.scope === "project" ? this.projects.find((p) => p.id === this.current?.id) : void 0;
    return project ? { ...project } : null;
  }
  /** Explicit selection, or null when no supported scope has been selected. */
  getSelection() {
    return this.current ? { scope: this.current.scope, id: this.current.id } : null;
  }
  validProjects(projects) {
    if (!Array.isArray(projects)) throw new Error("project listing must be an array");
    const seen = /* @__PURE__ */ new Set();
    return projects.filter((p) => {
      if (!p || typeof p.id !== "string" || !p.id.trim() || typeof p.name !== "string" || seen.has(p.id)) return false;
      seen.add(p.id);
      return true;
    }).map((p) => ({ id: p.id, name: p.name, ...typeof p.detail === "string" ? { detail: p.detail } : {} }));
  }
  choices() {
    const projects = this.projects.map((p) => ({ ...p, scope: "project" }));
    if (this.allowUserScope) projects.unshift({ scope: "user", id: null, name: translate("All Projects", "allProjects") });
    return projects;
  }
  choice(id, scope) {
    if (scope === "user") return this.allowUserScope ? this.choices()[0] : null;
    if (scope !== void 0 && scope !== "project") return null;
    return this.choices().find((p) => p.scope === "project" && p.id === id) ?? null;
  }
  /** Replace the project list, keeping the selection when it is still present. */
  setProjects(projects, currentId, currentScope) {
    const validated = this.validProjects(projects);
    this.generation++;
    this.pending = false;
    this.trigger.disabled = false;
    this.projects = validated;
    this.status = "ready";
    const wanted = currentId === void 0 ? this.current?.id : currentId;
    const scope = currentScope ?? (currentId === void 0 ? this.current?.scope : void 0);
    this.current = this.choice(wanted, scope);
    this.renderLabel();
    this.renderList();
  }
  async load() {
    const provider = this.config.provider;
    if (!provider) return;
    this.status = "loading";
    const generation = this.generation;
    try {
      const listing = await provider.listProjects();
      if (this.destroyed || generation !== this.generation) return;
      const projects = this.validProjects(listing.projects);
      if (listing.current_scope !== void 0 && listing.current_scope !== "user" && listing.current_scope !== "project") throw new Error("invalid current scope");
      if (listing.current_scope === "user" && listing.current != null) throw new Error("user scope requires null project id");
      this.allowUserScope = (this.config.allowUserScope === true || this.config.allowUserScope === void 0 && listing.allow_user_scope === true) && typeof provider.rememberScope === "function";
      if (this.allowUserScope && !this.selectionError.parentNode) this.container.appendChild(this.selectionError);
      this.status = "ready";
      this.setProjects(projects, this.config.current ?? listing.current ?? null, this.config.currentScope ?? listing.current_scope);
    } catch {
      if (this.destroyed || generation !== this.generation) return;
      this.status = "error";
      this.renderList();
    }
  }
  renderLabel() {
    if (this.current) {
      this.label.textContent = this.current.name;
      this.label.className = `${CLS}__current`;
    } else {
      this.label.textContent = this.config.placeholder ?? translate("Select project", "selectProject");
      this.label.className = `${CLS}__placeholder`;
    }
  }
  renderList() {
    this.list.innerHTML = "";
    const query = this.search?.value ?? "";
    this.filtered = fuzzyFilter(this.choices(), query, (p) => `${p.name} ${p.detail ?? ""}`);
    this.activeIndex = Math.min(this.activeIndex, Math.max(this.filtered.length - 1, 0));
    const emptyText = this.emptyText(query);
    if (emptyText) {
      const empty = document.createElement("div");
      empty.className = `${CLS}__empty`;
      empty.textContent = emptyText;
      this.list.appendChild(empty);
      this.search?.removeAttribute?.("aria-activedescendant");
      return;
    }
    this.filtered.forEach((project, index) => {
      this.list.appendChild(this.renderOption(project, index));
    });
    this.search?.setAttribute("aria-activedescendant", `${this.uid}-opt-${this.activeIndex}`);
  }
  emptyText(query) {
    if (this.status === "loading") return gettext("Loading projects\u2026");
    if (this.status === "error") return gettext("Could not load projects");
    if (this.projects.length === 0 && !this.allowUserScope) return translate("No projects", "noProjects");
    if (this.filtered.length === 0 && query.trim() !== "") return gettext("No matching projects");
    return null;
  }
  renderOption(project, index) {
    const option = document.createElement("button");
    option.type = "button";
    option.id = `${this.uid}-opt-${index}`;
    const isCurrent = this.current?.scope === project.scope && this.current?.id === project.id;
    const classes = [`${CLS}__option`];
    if (isCurrent) classes.push(`${CLS}__option--current`);
    if (index === this.activeIndex) classes.push(`${CLS}__option--active`);
    option.className = classes.join(" ");
    if (isCurrent) option.setAttribute("aria-current", "true");
    option.setAttribute("role", "option");
    option.setAttribute("aria-selected", String(isCurrent));
    option.tabIndex = -1;
    option.disabled = this.pending;
    const name = document.createElement("span");
    name.className = `${CLS}__option-name`;
    name.textContent = project.name;
    option.appendChild(name);
    if (project.detail) {
      const detail = document.createElement("span");
      detail.className = `${CLS}__option-detail`;
      detail.textContent = project.detail;
      option.appendChild(detail);
    }
    option.addEventListener("click", () => {
      if (this.commands.get(this.selectCommandId)?.def === this.selectCommand) this.commands.run(this.selectCommandId, { via: "button", source: option }, { scope: project.scope, id: project.id });
    });
    return option;
  }
  onSearchKey(e) {
    const last = this.filtered.length - 1;
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      const step = e.key === "ArrowDown" ? 1 : -1;
      this.activeIndex = last < 0 ? 0 : (this.activeIndex + step + last + 1) % (last + 1);
      this.renderList();
      this.list.children[this.activeIndex]?.scrollIntoView?.({ block: "nearest" });
    } else if (e.key === "Enter") {
      e.preventDefault();
      const project = this.filtered[this.activeIndex];
      if (project && this.commands.get(this.selectCommandId)?.def === this.selectCommand) this.commands.run(this.selectCommandId, { via: "keyboard", source: this.search }, { scope: project.scope, id: project.id });
    } else if (e.key === "Tab") {
      this.close();
    }
  }
  /** Open or close the option panel. */
  toggle() {
    if (this.open) this.close();
    else this.show();
  }
  show() {
    if (this.open) return;
    this.open = true;
    if (this.search) this.search.value = "";
    const currentIndex = this.choices().findIndex((p) => p.scope === this.current?.scope && p.id === this.current?.id);
    this.activeIndex = Math.max(currentIndex, 0);
    this.renderList();
    this.container.classList.add(`${CLS}--open`);
    this.trigger.setAttribute("aria-expanded", "true");
    this.search?.setAttribute("aria-expanded", "true");
    this.search?.focus?.();
  }
  close() {
    if (!this.open) return;
    this.open = false;
    this.container.classList.remove(`${CLS}--open`);
    this.trigger.setAttribute("aria-expanded", "false");
    this.search?.setAttribute("aria-expanded", "false");
  }
  /** Select a project: update the trigger, remember it, close, and emit the change. */
  select(payload) {
    if (this.destroyed || this.status !== "ready" || this.pending || !payload || typeof payload !== "object") return false;
    const value = payload;
    if (value.scope !== "user" && value.scope !== "project") return false;
    if (value.scope === "user" ? value.id !== null : typeof value.id !== "string" || !value.id.trim()) return false;
    const project = this.choices().find((p) => p.scope === value.scope && p.id === value.id);
    if (!project) return false;
    this.selectionError.hidden = true;
    const changed = this.current?.scope !== project.scope || this.current?.id !== project.id;
    if (!changed) {
      this.close();
      return false;
    }
    if (this.allowUserScope) {
      const remember2 = this.config.provider?.rememberScope;
      if (!this.allowUserScope || !remember2) return false;
      this.pending = true;
      this.trigger.disabled = true;
      this.renderList();
      const generation = ++this.generation;
      void this.acceptScope(project, generation);
      return true;
    }
    if (project.scope !== "project") return false;
    const provider = this.config.provider;
    let remember;
    try {
      remember = provider?.rememberProject;
    } catch {
      this.showSelectionError();
      return false;
    }
    if (typeof remember === "function" && provider) {
      this.legacyPersistenceExpected = true;
      this.pending = true;
      this.trigger.disabled = true;
      this.renderList();
      const generation = ++this.generation;
      void this.acceptProject(project, generation, provider, remember);
      return true;
    }
    if (this.legacyPersistenceExpected || remember !== void 0) {
      this.showSelectionError();
      return false;
    }
    this.applyChoice(project);
    return true;
  }
  showSelectionError() {
    if (!this.selectionError.parentNode) this.container.appendChild(this.selectionError);
    this.selectionError.textContent = translate("Could not select scope", "scopeSelectionFailed");
    this.selectionError.hidden = false;
  }
  async acceptProject(project, generation, provider, remember) {
    try {
      await remember.call(provider, project.id);
      if (!this.destroyed && generation === this.generation && this.config.provider === provider && provider.rememberProject === remember) this.applyChoice(project);
    } catch {
      if (!this.destroyed && generation === this.generation) this.showSelectionError();
    } finally {
      if (!this.destroyed && generation === this.generation) {
        this.pending = false;
        this.trigger.disabled = false;
        this.renderList();
      }
    }
  }
  async acceptScope(project, generation) {
    try {
      await this.config.provider.rememberScope({ scope: project.scope, id: project.id });
      if (!this.destroyed && generation === this.generation) this.applyChoice(project);
    } catch {
      if (!this.destroyed && generation === this.generation) {
        this.showSelectionError();
      }
    } finally {
      if (!this.destroyed && generation === this.generation) {
        this.pending = false;
        this.trigger.disabled = false;
        this.renderList();
      }
    }
  }
  applyChoice(project) {
    this.current = project;
    this.renderLabel();
    this.renderList();
    this.close();
    this.emit(PROJECT_SELECTOR_CHANGE, this.allowUserScope ? { scope: project.scope, id: project.id, name: project.name } : { id: project.id, name: project.name });
  }
  destroy() {
    this.destroyed = true;
    this.generation++;
    if (this.commands.get(this.selectCommandId)?.def === this.selectCommand) this.commands.unset(this.selectCommandId);
    document.removeEventListener("click", this.outsideClickHandler);
    document.removeEventListener("keydown", this.keyHandler);
    super.destroy();
  }
};

// ts/app/project-selector/provider.ts
function csrfToken() {
  if (typeof document === "undefined" || typeof document.cookie !== "string") return "";
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}
var PROJECT_PROVIDER_META_NAME = "stx-project-provider";
function hostProjectProvider(doc = document) {
  const url = doc.querySelector(`meta[name="${PROJECT_PROVIDER_META_NAME}"]`)?.getAttribute("content");
  return url ? httpProjectProvider(url) : null;
}
function httpProjectProvider(url) {
  return {
    async listProjects() {
      const response = await fetch(url, {
        credentials: "same-origin",
        headers: { Accept: "application/json" }
      });
      if (!response.ok) throw new Error(`project listing failed: HTTP ${response.status}`);
      const body = await response.json();
      return { projects: body.projects ?? [], current: body.current ?? null };
    },
    async rememberProject(id) {
      if (typeof id !== "string" || !id.trim()) throw new Error("project id required");
      const response = await fetch(url, {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() },
        body: JSON.stringify({ id })
      });
      if (!response.ok) throw new Error(`project selection failed: HTTP ${response.status}`);
    }
  };
}

// ts/app/project-selector/mount.ts
function projectNavigationUrl(template, id) {
  if (!template || typeof id !== "string" || !id.trim()) return null;
  return template.split("{id}").join(encodeURIComponent(id));
}

// ts/_base/scope.ts
var APP_SCOPE_META_NAME = "stx-app-scope";
var SCOPE_USER = "user";
var SCOPE_PROJECT = "project";
var AppScopeMarkerInvalidError = class extends Error {
  constructor(content) {
    super(
      `scitex-ui: <meta name="${APP_SCOPE_META_NAME}"> is present with content=${JSON.stringify(content)}, which is not one of "${SCOPE_USER}" | "${SCOPE_PROJECT}". The scitex-app SDK emits only "project" (user-scoped apps emit NO marker at all), so a present-but-unrecognised marker means the two sides disagree \u2014 a renamed value or a stale build. This is an integration bug; scitex-ui will not guess a scope.`
    );
    this.name = "AppScopeMarkerInvalidError";
  }
};
function appScope(doc = document) {
  const meta = doc.querySelector(`meta[name="${APP_SCOPE_META_NAME}"]`);
  if (!meta) return SCOPE_USER;
  const raw = meta.getAttribute("content");
  const content = raw === null ? null : raw.trim().toLowerCase();
  if (content === SCOPE_PROJECT) return SCOPE_PROJECT;
  if (content === SCOPE_USER || content === null || content === "") {
    return SCOPE_USER;
  }
  throw new AppScopeMarkerInvalidError(raw);
}

// ts/shell/app-scope-selector.ts
function mountProjectSelectorByScope(options, doc = document) {
  const provider = options.provider ?? (options.projects ? void 0 : hostProjectProvider(doc) ?? void 0);
  if ((options.scope ?? appScope(doc)) !== SCOPE_PROJECT && !(options.allowUserScope === true && typeof provider?.rememberScope === "function")) {
    return null;
  }
  const selector = new ProjectSelector({
    container: options.container,
    projects: options.projects,
    provider,
    current: options.current,
    placeholder: options.placeholder,
    allowUserScope: options.allowUserScope,
    currentScope: options.currentScope
  });
  const navigate = options.navigate;
  const container = typeof options.container === "string" ? doc.querySelector(options.container) : options.container;
  if (navigate && container) {
    container.addEventListener(PROJECT_SELECTOR_CHANGE, (event) => {
      const detail = event.detail;
      if (!detail || detail.scope !== void 0 && detail.scope !== "project") return;
      const url = projectNavigationUrl(navigate, detail.id);
      if (url) window.location.assign(url);
    });
  }
  return selector;
}
export {
  PROJECT_SELECTOR_CHANGE,
  hostProjectProvider,
  mountProjectSelectorByScope
};
