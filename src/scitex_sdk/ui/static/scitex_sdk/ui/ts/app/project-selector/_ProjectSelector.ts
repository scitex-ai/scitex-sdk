/**
 * ProjectSelector — the SDK project picker (compass L625).
 *
 * A dropdown with fuzzy search that lists the projects the user can access,
 * shows the current one on the trigger, and emits `stx-project-selector:change`
 * (bubbles, detail `{id, name}`) when the user picks another.
 *
 * The APP places it canonically in the left of its own header (after app
 * identity/title, before app-specific actions) via the
 * `.stx-app-header__slot--project-selector` guard; on non-header surfaces
 * (the workspace) it is placed app-locally. It never forks a second picker.
 * The data comes from `projects` or a `ProjectProvider`, so the component
 * knows nothing about users or permissions.
 *
 * Usage:
 *   const sel = new ProjectSelector({
 *     container: "#project-picker",
 *     provider: httpProjectProvider("/project/api/scope/projects/"),
 *   });
 *   sel.container.addEventListener(PROJECT_SELECTOR_CHANGE, (e) => { ... });
 */

import { BaseComponent } from "../../_base/BaseComponent";
import { gettext } from "../../_base/gettext";
import { shellTranslate } from "../../_base/i18n";
import type { ShellStringKey } from "../../_base/i18n";
import { fuzzyFilter } from "./fuzzy";
import type { ProjectSelectorConfig, ProjectOption, ProjectChoice, ProjectSelection } from "./types";
import type { ProjectProvider } from "./provider";
import { CommandRegistry } from "../../shell/keymap/_registry";
import type { CommandDef } from "../../shell/keymap/_registry";

const CLS = "stx-app-project-selector";

/** Event emitted on the container when the selection changes. */
export const PROJECT_SELECTOR_CHANGE = "stx-project-selector:change";
export const PROJECT_SELECTOR_SELECT = "project-selector:select";

let instanceCount = 0;

/** gettext first; a page without the scitex_ui catalog still gets the built-in shell JA. */
function translate(msgid: string, shellKey?: ShellStringKey): string {
  const translated = gettext(msgid);
  if (translated !== msgid || !shellKey) return translated;
  return shellTranslate(shellKey);
}

export class ProjectSelector extends BaseComponent<ProjectSelectorConfig> {
  /** Settles once the provider's listing has been rendered (immediately without one). */
  readonly ready: Promise<void>;
  readonly commands: CommandRegistry;
  readonly selectCommandId: string;
  private readonly selectCommand: CommandDef;
  private projects: ProjectOption[];
  private current: ProjectChoice | null;
  private filtered: ProjectChoice[] = [];
  private allowUserScope = false;
  private legacyPersistenceExpected: boolean;
  private pending = false;
  private generation = 0;
  private destroyed = false;
  private selectionError: HTMLElement;
  private activeIndex = 0;
  private status: "ready" | "loading" | "error" = "ready";
  private readonly uid: string;
  private trigger: HTMLButtonElement;
  private label: HTMLElement;
  private panel: HTMLElement;
  private search: HTMLInputElement | null = null;
  private list: HTMLElement;
  private open = false;
  private outsideClickHandler: (e: MouseEvent) => void;
  private keyHandler: (e: KeyboardEvent) => void;

  constructor(config: ProjectSelectorConfig) {
    super(config);
    this.commands = config.commands ?? new CommandRegistry();
    this.selectCommandId = config.selectCommandId ?? PROJECT_SELECTOR_SELECT;
    if (!this.selectCommandId || this.commands.has(this.selectCommandId)) {
      throw new Error(`project selector command already registered: ${this.selectCommandId}`);
    }
    this.selectCommand = { id: this.selectCommandId, label: gettext("Select project"), action: (payload) => this.select(payload) };
    this.uid = "stx-project-picker-" + ++instanceCount;
    this.projects = this.validProjects(config.projects ?? []);
    this.legacyPersistenceExpected = config.provider?.rememberProject !== undefined;
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

    this.outsideClickHandler = (e: MouseEvent): void => {
      if (!this.container.contains(e.target as Node)) this.close();
    };
    this.keyHandler = (e: KeyboardEvent): void => {
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
  getCurrent(): ProjectOption | null {
    const project = this.current?.scope === "project"
      ? this.projects.find((p) => p.id === this.current?.id) : undefined;
    return project ? { ...project } : null;
  }

  /** Explicit selection, or null when no supported scope has been selected. */
  getSelection(): ProjectSelection | null {
    return this.current ? { scope: this.current.scope, id: this.current.id } as ProjectSelection : null;
  }

  private validProjects(projects: unknown): ProjectOption[] {
    if (!Array.isArray(projects)) throw new Error("project listing must be an array");
    const seen = new Set<string>();
    return projects.filter((p): p is ProjectOption => {
      if (!p || typeof p.id !== "string" || !p.id.trim() || typeof p.name !== "string" || seen.has(p.id)) return false;
      seen.add(p.id);
      return true;
    }).map((p) => ({ id: p.id, name: p.name, ...(typeof p.detail === "string" ? { detail: p.detail } : {}) }));
  }

  private choices(): ProjectChoice[] {
    const projects: ProjectChoice[] = this.projects.map((p) => ({ ...p, scope: "project" }));
    if (this.allowUserScope) projects.unshift({ scope: "user", id: null, name: translate("All Projects", "allProjects") });
    return projects;
  }

  private choice(id?: string | null, scope?: string): ProjectChoice | null {
    if (scope === "user") return this.allowUserScope ? this.choices()[0] : null;
    if (scope !== undefined && scope !== "project") return null;
    return this.choices().find((p) => p.scope === "project" && p.id === id) ?? null;
  }

  /** Replace the project list, keeping the selection when it is still present. */
  setProjects(projects: ProjectOption[], currentId?: string | null, currentScope?: "user" | "project"): void {
    const validated = this.validProjects(projects);
    this.generation++;
    this.pending = false;
    this.trigger.disabled = false;
    this.projects = validated;
    this.status = "ready";
    const wanted = currentId === undefined ? this.current?.id : currentId;
    const scope = currentScope ?? (currentId === undefined ? this.current?.scope : undefined);
    this.current = this.choice(wanted, scope);
    this.renderLabel();
    this.renderList();
  }

  private async load(): Promise<void> {
    const provider = this.config.provider;
    if (!provider) return;
    this.status = "loading";
    const generation = this.generation;
    try {
      const listing = await provider.listProjects();
      if (this.destroyed || generation !== this.generation) return;
      const projects = this.validProjects(listing.projects);
      if (listing.current_scope !== undefined && listing.current_scope !== "user" && listing.current_scope !== "project") throw new Error("invalid current scope");
      if (listing.current_scope === "user" && listing.current != null) throw new Error("user scope requires null project id");
      this.allowUserScope = (this.config.allowUserScope === true || (this.config.allowUserScope === undefined && listing.allow_user_scope === true)) && typeof provider.rememberScope === "function";
      if (this.allowUserScope && !this.selectionError.parentNode) this.container.appendChild(this.selectionError);
      this.status = "ready";
      this.setProjects(projects, this.config.current ?? listing.current ?? null, this.config.currentScope ?? listing.current_scope);
    } catch {
      if (this.destroyed || generation !== this.generation) return;
      this.status = "error";
      this.renderList();
    }
  }

  private renderLabel(): void {
    if (this.current) {
      this.label.textContent = this.current.name;
      this.label.className = `${CLS}__current`;
    } else {
      this.label.textContent = this.config.placeholder ?? translate("Select project", "selectProject");
      this.label.className = `${CLS}__placeholder`;
    }
  }

  private renderList(): void {
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

  private emptyText(query: string): string | null {
    if (this.status === "loading") return gettext("Loading projects…");
    if (this.status === "error") return gettext("Could not load projects");
    if (this.projects.length === 0 && !this.allowUserScope) return translate("No projects", "noProjects");
    if (this.filtered.length === 0 && query.trim() !== "") return gettext("No matching projects");
    return null;
  }

  private renderOption(project: ProjectChoice, index: number): HTMLButtonElement {
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

  private onSearchKey(e: KeyboardEvent): void {
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
  toggle(): void {
    if (this.open) this.close();
    else this.show();
  }

  private show(): void {
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

  close(): void {
    if (!this.open) return;
    this.open = false;
    this.container.classList.remove(`${CLS}--open`);
    this.trigger.setAttribute("aria-expanded", "false");
    this.search?.setAttribute("aria-expanded", "false");
  }

  /** Select a project: update the trigger, remember it, close, and emit the change. */
  private select(payload: unknown): boolean {
    if (this.destroyed || this.status !== "ready" || this.pending || !payload || typeof payload !== "object") return false;
    const value = payload as { scope?: unknown; id?: unknown };
    if (value.scope !== "user" && value.scope !== "project") return false;
    if (value.scope === "user" ? value.id !== null : typeof value.id !== "string" || !value.id.trim()) return false;
    const project = this.choices().find((p) => p.scope === value.scope && p.id === value.id);
    if (!project) return false;
    this.selectionError.hidden = true;
    const changed = this.current?.scope !== project.scope || this.current?.id !== project.id;
    if (!changed) { this.close(); return false; }
    if (this.allowUserScope) {
      const remember = this.config.provider?.rememberScope;
      if (!this.allowUserScope || !remember) return false;
      this.pending = true;
      this.trigger.disabled = true;
      this.renderList();
      const generation = ++this.generation;
      void this.acceptScope(project, generation);
      return true;
    }
    if (project.scope !== "project") return false;
    const provider = this.config.provider;
    let remember: ProjectProvider["rememberProject"];
    try { remember = provider?.rememberProject; } catch { this.showSelectionError(); return false; }
    if (typeof remember === "function" && provider) {
      this.legacyPersistenceExpected = true;
      this.pending = true;
      this.trigger.disabled = true;
      this.renderList();
      const generation = ++this.generation;
      void this.acceptProject(project, generation, provider, remember);
      return true;
    }
    if (this.legacyPersistenceExpected || remember !== undefined) {
      this.showSelectionError();
      return false;
    }
    this.applyChoice(project);
    return true;
  }

  private showSelectionError(): void {
    if (!this.selectionError.parentNode) this.container.appendChild(this.selectionError);
    this.selectionError.textContent = translate("Could not select scope", "scopeSelectionFailed");
    this.selectionError.hidden = false;
  }

  private async acceptProject(
    project: ProjectChoice & { scope: "project" },
    generation: number,
    provider: ProjectProvider,
    remember: (id: string) => Promise<void>,
  ): Promise<void> {
    try {
      await remember.call(provider, project.id);
      if (!this.destroyed && generation === this.generation &&
          this.config.provider === provider && provider.rememberProject === remember) this.applyChoice(project);
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

  private async acceptScope(project: ProjectChoice, generation: number): Promise<void> {
    try {
      await this.config.provider!.rememberScope!({ scope: project.scope, id: project.id } as ProjectSelection);
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

  private applyChoice(project: ProjectChoice): void {
    this.current = project;
    this.renderLabel();
    this.renderList();
    this.close();
    this.emit(PROJECT_SELECTOR_CHANGE, this.allowUserScope
      ? { scope: project.scope, id: project.id, name: project.name }
      : { id: project.id, name: project.name });
  }

  override destroy(): void {
    this.destroyed = true;
    this.generation++;
    if (this.commands.get(this.selectCommandId)?.def === this.selectCommand) this.commands.unset(this.selectCommandId);
    document.removeEventListener("click", this.outsideClickHandler);
    document.removeEventListener("keydown", this.keyHandler);
    super.destroy();
  }
}
