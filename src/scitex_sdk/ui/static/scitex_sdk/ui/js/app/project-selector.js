/* AUTO-GENERATED from ts/app/project-selector/auto-mount.ts via esbuild — do not edit by hand. Rebuild: npx esbuild ts/app/project-selector/auto-mount.ts --bundle --format=esm --outfile=js/app/project-selector.js */
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

// ts/app/project-selector/_ProjectSelector.ts
var CLS = "stx-app-project-selector";
var PROJECT_SELECTOR_CHANGE = "stx-project-selector:change";
var instanceCount = 0;
function translate(msgid, shellKey) {
  const translated = gettext(msgid);
  if (translated !== msgid || !shellKey) return translated;
  return shellTranslate(shellKey);
}
var ProjectSelector = class extends BaseComponent {
  /** Settles once the provider's listing has been rendered (immediately without one). */
  ready;
  projects;
  current;
  filtered = [];
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
    this.uid = "stx-project-picker-" + ++instanceCount;
    this.projects = config.projects ?? [];
    this.current = this.projects.find((p) => p.id === config.current) ?? null;
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
    this.container.appendChild(this.trigger);
    this.container.appendChild(this.panel);
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
    return this.current;
  }
  /** Replace the project list, keeping the selection when it is still present. */
  setProjects(projects, currentId) {
    this.projects = projects;
    const wanted = currentId === void 0 ? this.current?.id : currentId;
    this.current = projects.find((p) => p.id === wanted) ?? null;
    this.renderLabel();
    this.renderList();
  }
  async load() {
    const provider = this.config.provider;
    if (!provider) return;
    this.status = "loading";
    try {
      const listing = await provider.listProjects();
      this.status = "ready";
      this.setProjects(listing.projects, this.config.current ?? listing.current ?? null);
    } catch {
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
    this.filtered = fuzzyFilter(this.projects, query, (p) => `${p.name} ${p.detail ?? ""}`);
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
    if (this.projects.length === 0) return translate("No projects", "noProjects");
    if (this.filtered.length === 0 && query.trim() !== "") return gettext("No matching projects");
    return null;
  }
  renderOption(project, index) {
    const option = document.createElement("button");
    option.type = "button";
    option.id = `${this.uid}-opt-${index}`;
    const isCurrent = this.current?.id === project.id;
    const classes = [`${CLS}__option`];
    if (isCurrent) classes.push(`${CLS}__option--current`);
    if (index === this.activeIndex) classes.push(`${CLS}__option--active`);
    option.className = classes.join(" ");
    if (isCurrent) option.setAttribute("aria-current", "true");
    option.setAttribute("role", "option");
    option.setAttribute("aria-selected", String(isCurrent));
    option.tabIndex = -1;
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
    option.addEventListener("click", () => this.select(project));
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
      if (project) this.select(project);
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
    const currentIndex = this.projects.findIndex((p) => p.id === this.current?.id);
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
  select(project) {
    const changed = this.current?.id !== project.id;
    this.current = project;
    this.renderLabel();
    this.renderList();
    this.close();
    if (!changed) return;
    this.config.provider?.rememberProject?.(project.id).catch(() => void 0);
    this.emit(PROJECT_SELECTOR_CHANGE, { id: project.id, name: project.name });
  }
  destroy() {
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
      await fetch(url, {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() },
        body: JSON.stringify({ id })
      });
    }
  };
}

// ts/app/project-selector/mount.ts
var PROJECT_PICKER_ATTRIBUTE = "data-stx-project-picker";
var MOUNTED_ATTRIBUTE = "data-stx-project-picker-mounted";
function projectNavigationUrl(template, id) {
  if (!template) return null;
  return template.split("{id}").join(encodeURIComponent(id));
}
function mountProjectPickers(root = document) {
  const mounted = [];
  const elements = root.querySelectorAll(`[${PROJECT_PICKER_ATTRIBUTE}]`);
  for (const element of Array.from(elements)) {
    if (element.hasAttribute(MOUNTED_ATTRIBUTE)) continue;
    const providerUrl = element.getAttribute("data-provider-url");
    if (!providerUrl) continue;
    element.setAttribute(MOUNTED_ATTRIBUTE, "");
    const selector = new ProjectSelector({
      container: element,
      provider: httpProjectProvider(providerUrl),
      current: element.getAttribute("data-current") || null,
      placeholder: element.getAttribute("data-placeholder") || void 0
    });
    const navigate = element.getAttribute("data-navigate");
    element.addEventListener(PROJECT_SELECTOR_CHANGE, (event) => {
      const { id } = event.detail;
      const url = projectNavigationUrl(navigate, id);
      if (url) window.location.assign(url);
    });
    mounted.push(selector);
  }
  return mounted;
}

// ts/app/project-selector/auto-mount.ts
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => mountProjectPickers());
} else {
  mountProjectPickers();
}
