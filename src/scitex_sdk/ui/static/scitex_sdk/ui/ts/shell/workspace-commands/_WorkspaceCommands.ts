import { BaseComponent } from "../../_base/BaseComponent";
import type { BaseComponentConfig } from "../../_base/types";
import { gettext } from "../../_base/gettext";
import { CommandRegistry, Keymap, parseSequence } from "../keymap";

export type ShortcutPreferences = ReturnType<Keymap["serializeOverrides"]>;

export interface WorkspaceCommandsConfig extends BaseComponentConfig {
  registry: CommandRegistry;
  keymap: Keymap;
  /** Explicit payload-free leaf commands suitable for the palette. */
  commandIds: readonly string[];
  /** This component owns the keymap listener until destroy(). Defaults to document. */
  keyboardTarget?: Document | HTMLElement;
  /** Optional host persistence adapter. No account storage is created here. */
  onPreferencesChange?: (preferences: ShortcutPreferences) => void;
}

const owners = new WeakMap<Keymap, WorkspaceCommands>();
let nextId = 0;

function composing(event: KeyboardEvent): boolean {
  return event.isComposing || event.keyCode === 229 ||
    ["Dead", "Process", "Unidentified"].includes(event.key) ||
    event.getModifierState("AltGraph");
}

/** Opt-in command palette and shortcut controls over the leaf's existing registry.
 * It adds no default workspace shortcuts and never replaces legacy dispatchers.
 */
export class WorkspaceCommands extends BaseComponent<WorkspaceCommandsConfig> {
  readonly keymap: Keymap;
  private readonly ids: readonly string[];
  private readonly trigger: HTMLButtonElement;
  private readonly panel: HTMLElement;
  private readonly search: HTMLInputElement;
  private readonly results: HTMLElement;
  private readonly status: HTMLElement;
  private readonly detach: () => void;
  private destroyed = false;
  private compositionActive = false;
  private visibleIds: string[] = [];

  constructor(config: WorkspaceCommandsConfig) {
    super(config);
    if (config.keymap.commands !== config.registry) {
      throw new Error("WorkspaceCommands requires the keymap's command registry");
    }
    if (owners.has(config.keymap)) throw new Error("WorkspaceCommands already owns this keymap");
    this.keymap = config.keymap;
    this.ids = [...new Set(config.commandIds)];
    this.container.classList.add("stx-workspace-commands");
    this.trigger = document.createElement("button");
    this.trigger.type = "button";
    this.trigger.textContent = gettext("Commands");
    this.trigger.setAttribute("aria-expanded", "false");
    this.panel = document.createElement("section");
    this.panel.id = `stx-workspace-commands-${++nextId}`;
    this.panel.className = "stx-workspace-commands__panel";
    this.panel.setAttribute("aria-label", gettext("Workspace commands"));
    this.panel.hidden = true;
    this.panel.addEventListener("compositionstart", () => { this.compositionActive = true; });
    this.panel.addEventListener("compositionend", () => { this.compositionActive = false; });
    this.trigger.setAttribute("aria-controls", this.panel.id);
    this.search = document.createElement("input");
    this.search.type = "search";
    this.search.setAttribute("aria-label", gettext("Find command"));
    this.search.placeholder = gettext("Find command");
    this.search.addEventListener("input", () => this.refresh());
    this.search.addEventListener("keydown", (event) => {
      if (event.defaultPrevented || this.compositionActive || composing(event)) return;
      if (event.key === "Enter" && this.visibleIds.length) {
        if (this.run(this.visibleIds[0], "keyboard")) event.preventDefault();
      }
    });
    this.panel.addEventListener("keydown", (event) => {
      if (event.defaultPrevented || this.compositionActive || composing(event)) return;
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        this.close();
        this.trigger.focus();
      }
    });
    this.trigger.addEventListener("click", () => this.panel.hidden ? this.open() : this.close());
    this.results = document.createElement("div");
    this.status = document.createElement("p");
    this.status.setAttribute("role", "status");
    this.panel.append(this.search, this.results, this.status);
    this.container.append(this.trigger, this.panel);
    this.detach = this.keymap.attach(config.keyboardTarget ?? document);
    owners.set(this.keymap, this);
    this.refresh();
  }

  open(): void {
    if (this.destroyed) return;
    this.panel.hidden = false;
    this.trigger.setAttribute("aria-expanded", "true");
    this.search.value = "";
    this.status.textContent = "";
    this.refresh();
    this.search.focus();
  }

  close(): void {
    this.panel.hidden = true;
    this.trigger.setAttribute("aria-expanded", "false");
  }

  /** Refresh after the host changes commands, modes, or loaded preferences. */
  refresh(): void {
    if (this.destroyed) return;
    const focusedRow = document.activeElement?.closest<HTMLElement>(".stx-workspace-commands__row");
    const restoreFocus = focusedRow && this.results.contains(focusedRow) ? focusedRow.dataset.commandId : undefined;
    this.results.replaceChildren();
    const query = this.search.value.trim().toLocaleLowerCase();
    const commands = this.config.registry.list().filter((command) =>
      command.active && this.ids.includes(command.id) &&
      command.label.toLocaleLowerCase().includes(query));
    this.visibleIds = commands.map((command) => command.id);
    const help = this.keymap.help().commands;
    for (const command of commands) {
      const row = document.createElement("div");
      row.className = "stx-workspace-commands__row";
      row.dataset.commandId = command.id;
      const run = this.button(command.label, () => this.run(command.id, "button"));
      run.dataset.commandId = command.id;
      const shortcut = document.createElement("input");
      shortcut.type = "text";
      shortcut.setAttribute("aria-label", `${gettext("Shortcut for")} ${command.label}`);
      shortcut.placeholder = "C-x C-p";
      shortcut.value = help.find((entry) => entry.id === command.id)?.chords[0] ?? "";
      const apply = this.button(gettext("Apply shortcut"), () => this.apply(command.id, shortcut.value));
      const disable = this.button(gettext("Disable shortcut"), () => {
        this.keymap.unbind(command.id);
        this.changed();
      });
      const reset = this.button(gettext("Reset shortcut"), () => {
        this.editShortcut(command.id, () => {
          const preferences = this.keymap.serializeOverrides();
          delete preferences.overrides[command.id];
          preferences.unbound = preferences.unbound.filter((id) => id !== command.id);
          this.keymap.loadOverrides(preferences);
        });
      });
      // A command may be callable without having a factory keyboard binding.
      const hasFactoryBinding = this.keymap.hasFactoryBinding(command.id);
      apply.disabled = disable.disabled = reset.disabled = !hasFactoryBinding;
      row.append(run, shortcut, apply, disable, reset);
      this.results.append(row);
      if (restoreFocus === command.id) shortcut.focus();
    }
    if (!commands.length) {
      const empty = document.createElement("p");
      empty.textContent = gettext("No matching commands");
      this.results.append(empty);
    }
    const hint = document.createElement("p");
    hint.textContent = gettext("Shortcut notation: C = Ctrl, M = Alt, S = Shift, M2 = Command. Separate keys with spaces.");
    this.results.append(hint);
  }

  private button(label: string, action: () => unknown): HTMLButtonElement {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = label;
    button.addEventListener("click", (event) => {
      // The initiating click must not close a leaf popup that the command opens.
      event.stopPropagation();
      if (!this.destroyed) action();
    });
    return button;
  }

  private run(id: string, via: "button" | "keyboard"): boolean {
    if (this.destroyed || !this.ids.includes(id) || !this.config.registry.get(id)?.active) return false;
    this.close();
    this.trigger.focus();
    return this.config.registry.run(id, { via, source: this.search });
  }

  private apply(id: string, sequence: string): void {
    this.editShortcut(id, () => {
      if (!parseSequence(sequence).length) throw new Error(gettext("Enter a shortcut"));
      this.keymap.enable(id);
      this.keymap.setOverride(id, sequence);
    });
  }

  private editShortcut(id: string, edit: () => void): void {
    const previous = this.keymap.serializeOverrides();
    try {
      edit();
      const conflict = this.keymap.overrideConflicts().find((item) =>
        item.newCommandId === id || item.existingCommandId === id);
      if (conflict) throw new Error(`${gettext("Shortcut already used by")} ${conflict.existingCommandId === id ? conflict.newCommandId : conflict.existingCommandId}`);
    } catch (error) {
      this.keymap.loadOverrides(previous);
      this.status.textContent = error instanceof Error ? error.message : gettext("Invalid shortcut");
      return;
    }
    this.changed();
  }

  private changed(): void {
    this.status.textContent = gettext("Shortcut updated");
    this.refresh();
    this.config.onPreferencesChange?.(this.keymap.serializeOverrides());
  }

  override destroy(): void {
    if (this.destroyed) return;
    this.destroyed = true;
    this.compositionActive = false;
    this.detach();
    if (owners.get(this.keymap) === this) owners.delete(this.keymap);
    super.destroy();
  }
}
