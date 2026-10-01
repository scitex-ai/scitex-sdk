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
import type { ProjectSelectorConfig, ProjectOption } from "./types";

const CLS = "stx-app-project-selector";

/** Event emitted on the container when the selection changes. */
export const PROJECT_SELECTOR_CHANGE = "stx-project-selector:change";

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
  private projects: ProjectOption[];
  private current: ProjectOption | null;
  private filtered: ProjectOption[] = [];
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
    return this.current;
  }

  /** Replace the project list, keeping the selection when it is still present. */
  setProjects(projects: ProjectOption[], currentId?: string | null): void {
    this.projects = projects;
    const wanted = currentId === undefined ? this.current?.id : currentId;
    this.current = projects.find((p) => p.id === wanted) ?? null;
    this.renderLabel();
    this.renderList();
  }

  private async load(): Promise<void> {
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

  private emptyText(query: string): string | null {
    if (this.status === "loading") return gettext("Loading projects…");
    if (this.status === "error") return gettext("Could not load projects");
    if (this.projects.length === 0) return translate("No projects", "noProjects");
    if (this.filtered.length === 0 && query.trim() !== "") return gettext("No matching projects");
    return null;
  }

  private renderOption(project: ProjectOption, index: number): HTMLButtonElement {
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
      if (project) this.select(project);
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
    const currentIndex = this.projects.findIndex((p) => p.id === this.current?.id);
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
  private select(project: ProjectOption): void {
    const changed = this.current?.id !== project.id;
    this.current = project;
    this.renderLabel();
    this.renderList();
    this.close();
    if (!changed) return;
    this.config.provider?.rememberProject?.(project.id).catch(() => undefined);
    this.emit(PROJECT_SELECTOR_CHANGE, { id: project.id, name: project.name });
  }

  override destroy(): void {
    document.removeEventListener("click", this.outsideClickHandler);
    document.removeEventListener("keydown", this.keyHandler);
    super.destroy();
  }
}
