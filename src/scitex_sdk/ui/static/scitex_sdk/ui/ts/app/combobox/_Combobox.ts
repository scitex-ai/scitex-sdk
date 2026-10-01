/**
 * Combobox — fuzzy-typeahead select.
 *
 * A trigger button opens a popover containing a search input and a
 * filtered list of options. Arrow keys navigate; Enter selects; Esc
 * closes. Optionally exposes an `onCreate(query)` hook for "create new
 * value" flows (e.g. moving a task to a project that does not exist
 * yet in scitex-todo).
 *
 * Usage:
 *   import { Combobox } from "scitex_sdk/ui/ts/app/combobox";
 *   const cb = new Combobox({
 *     container: "#cb-container",
 *     trigger: "#cb-btn",
 *     items: [
 *       { value: "p0", label: "P0 (highest)" },
 *       { value: "p1", label: "P1" },
 *     ],
 *     value: "p1",
 *     placeholder: "Search…",
 *     onChange: (item) => console.log(item.value),
 *     onCreate: (query) => console.log("new value:", query),
 *   });
 *
 * Why a custom component (vs. a native <select> with datalist):
 *   - Native <select> cannot fuzzy-filter, cannot inject a "+ Create
 *     new" affordance, cannot group, and cannot be styled consistently
 *     across browsers.
 *   - The fuzzy match is the same subsequence algorithm used by fzf
 *     and by scitex-todo's existing fuzzy-search input, so the muscle
 *     memory transfers across the app.
 */

import { BaseComponent } from "../../_base/BaseComponent";
import { fuzzyMatch } from "../../_base/fuzzy";
import type { ComboboxConfig, ComboboxItem } from "./types";

const CLS = "stx-app-combobox";

interface IndexedItem {
  item: ComboboxItem;
  index: number;
}

export class Combobox extends BaseComponent<ComboboxConfig> {
  private triggerEl: HTMLElement;
  private inputEl: HTMLInputElement | null = null;
  private listEl: HTMLElement | null = null;
  private open = false;
  private currentValue: string | undefined;
  private highlightedIndex = -1;
  private filtered: IndexedItem[] = [];
  private outsideClickHandler: (e: MouseEvent) => void;

  constructor(config: ComboboxConfig) {
    super(config);
    this.currentValue = config.value;

    this.triggerEl =
      typeof config.trigger === "string"
        ? (document.querySelector<HTMLElement>(config.trigger) as HTMLElement)
        : config.trigger;

    if (!this.triggerEl) {
      throw new Error(`Combobox: trigger not found: ${config.trigger}`);
    }

    this.outsideClickHandler = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (
        this.open &&
        !this.container.contains(target) &&
        !this.triggerEl.contains(target)
      ) {
        this.close();
      }
    };

    this.triggerEl.addEventListener("click", (e) => {
      e.stopPropagation();
      this.toggle();
    });

    document.addEventListener("click", this.outsideClickHandler);

    // Reflect the initial value on the trigger label so the consumer
    // does not have to set it manually.
    this.syncTriggerLabel();
  }

  /** Open the combobox popover. */
  show(): void {
    if (this.open) return;
    this.open = true;
    this.renderMenu();
    this.container.style.display = "block";
    this.positionMenu();
    // Focus the search input on the next frame so the popover has
    // already laid out (otherwise focus() races against display:block).
    requestAnimationFrame(() => this.inputEl?.focus());
  }

  /** Close the combobox popover. */
  close(): void {
    if (!this.open) return;
    this.open = false;
    this.container.style.display = "none";
    this.highlightedIndex = -1;
  }

  /** Toggle open / close. */
  toggle(): void {
    this.open ? this.close() : this.show();
  }

  /** Replace the option list (e.g. after the consumer created a new
   *  value via onCreate and now wants to include it). */
  setItems(items: ComboboxItem[]): void {
    this.config.items = items;
    if (this.open) {
      this.applyFilter(this.inputEl?.value || "");
      this.renderList();
    }
  }

  /** Programmatically set the selected value. Does NOT fire onChange. */
  setValue(value: string | undefined): void {
    this.currentValue = value;
    this.syncTriggerLabel();
  }

  /** Get the currently selected value. */
  getValue(): string | undefined {
    return this.currentValue;
  }

  override destroy(): void {
    document.removeEventListener("click", this.outsideClickHandler);
    super.destroy();
  }

  // ----- Render -------------------------------------------------------

  private renderMenu(): void {
    this.container.innerHTML = "";
    this.container.className = CLS;

    const menu = document.createElement("div");
    menu.className = `${CLS}__menu`;
    menu.setAttribute("role", "listbox");

    const input = document.createElement("input");
    input.type = "text";
    input.className = `${CLS}__input`;
    input.placeholder = this.config.placeholder || "Search…";
    input.autocomplete = "off";
    input.spellcheck = false;
    input.setAttribute("aria-autocomplete", "list");
    input.addEventListener("input", () => {
      this.applyFilter(input.value);
      this.highlightedIndex = this.filtered.length ? 0 : -1;
      this.renderList();
    });
    input.addEventListener("keydown", (e) => this.onInputKeydown(e));
    menu.appendChild(input);
    this.inputEl = input;

    const list = document.createElement("div");
    list.className = `${CLS}__list`;
    menu.appendChild(list);
    this.listEl = list;

    this.container.appendChild(menu);

    this.applyFilter("");
    this.highlightedIndex = this.filtered.length ? 0 : -1;
    this.renderList();
  }

  private renderList(): void {
    if (!this.listEl) return;
    this.listEl.innerHTML = "";

    if (!this.filtered.length) {
      const empty = document.createElement("div");
      empty.className = `${CLS}__empty`;
      empty.textContent = this.config.emptyText || "No matches";
      this.listEl.appendChild(empty);
    } else {
      let lastGroup: string | undefined = undefined;
      this.filtered.forEach((entry, idx) => {
        const { item } = entry;
        // Group header
        if (item.group && item.group !== lastGroup) {
          const hdr = document.createElement("div");
          hdr.className = `${CLS}__group`;
          hdr.textContent = item.group;
          this.listEl!.appendChild(hdr);
          lastGroup = item.group;
        } else if (!item.group) {
          lastGroup = undefined;
        }

        const row = document.createElement("div");
        row.className = `${CLS}__item`;
        row.setAttribute("role", "option");
        row.dataset.value = item.value;
        if (item.disabled) row.classList.add(`${CLS}__item--disabled`);
        if (idx === this.highlightedIndex) {
          row.classList.add(`${CLS}__item--highlighted`);
        }
        if (this.currentValue === item.value) {
          row.classList.add(`${CLS}__item--selected`);
        }
        row.textContent = item.label;
        if (!item.disabled) {
          row.addEventListener("mouseenter", () => {
            this.highlightedIndex = idx;
            this.refreshHighlight();
          });
          row.addEventListener("click", (e) => {
            e.stopPropagation();
            this.select(entry);
          });
        }
        this.listEl!.appendChild(row);
      });
    }

    // "Create new" affordance — only when consumer provided onCreate
    // AND the current query doesn't exactly match an existing label.
    const rawQuery = this.inputEl?.value || "";
    const q = rawQuery.trim();
    if (this.config.onCreate && q.length > 0) {
      const exists = this.config.items.some(
        (it) => it.label.toLowerCase() === q.toLowerCase(),
      );
      if (!exists) {
        const labelFn =
          this.config.createLabel ||
          ((raw: string) => `+ Create “${raw}”`);
        const row = document.createElement("div");
        row.className = `${CLS}__item ${CLS}__item--create`;
        row.setAttribute("role", "option");
        row.textContent = labelFn(q);
        row.addEventListener("click", (e) => {
          e.stopPropagation();
          this.config.onCreate?.(q);
          this.close();
        });
        this.listEl.appendChild(row);
      }
    }
  }

  private refreshHighlight(): void {
    if (!this.listEl) return;
    this.listEl
      .querySelectorAll(`.${CLS}__item--highlighted`)
      .forEach((el) => el.classList.remove(`${CLS}__item--highlighted`));
    const rows = this.listEl.querySelectorAll(`.${CLS}__item`);
    const target = rows[this.highlightedIndex] as HTMLElement | undefined;
    if (target) {
      target.classList.add(`${CLS}__item--highlighted`);
      // Keep the highlighted row in view as the user arrow-navigates.
      target.scrollIntoView({ block: "nearest" });
    }
  }

  private positionMenu(): void {
    const rect = this.triggerEl.getBoundingClientRect();
    this.container.style.position = "absolute";
    this.container.style.top = `${rect.bottom + window.scrollY}px`;
    if (this.config.align === "right") {
      this.container.style.right = `${window.innerWidth - rect.right}px`;
      this.container.style.left = "auto";
    } else {
      this.container.style.left = `${rect.left + window.scrollX}px`;
      this.container.style.right = "auto";
    }
    this.container.style.zIndex = "100";
  }

  private syncTriggerLabel(): void {
    if (this.config.updateTriggerLabel === false) return;
    const item = this.config.items.find((it) => it.value === this.currentValue);
    if (item) {
      this.triggerEl.textContent = item.label;
    }
  }

  // ----- Behaviour ----------------------------------------------------

  private onInputKeydown(e: KeyboardEvent): void {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (this.filtered.length) {
        this.highlightedIndex = Math.min(
          this.filtered.length - 1,
          this.highlightedIndex + 1,
        );
        this.refreshHighlight();
      }
      return;
    }
    if (e.key === "ArrowUp") {
      e.preventDefault();
      if (this.filtered.length) {
        this.highlightedIndex = Math.max(0, this.highlightedIndex - 1);
        this.refreshHighlight();
      }
      return;
    }
    if (e.key === "Enter") {
      e.preventDefault();
      if (this.highlightedIndex >= 0 && this.highlightedIndex < this.filtered.length) {
        this.select(this.filtered[this.highlightedIndex]);
      } else if (this.config.onCreate) {
        const q = (this.inputEl?.value || "").trim();
        if (q.length > 0) {
          const exists = this.config.items.some(
            (it) => it.label.toLowerCase() === q.toLowerCase(),
          );
          if (!exists) {
            this.config.onCreate(q);
            this.close();
          }
        }
      }
      return;
    }
    if (e.key === "Escape") {
      e.preventDefault();
      this.close();
      this.triggerEl.focus?.();
      return;
    }
  }

  private select(entry: IndexedItem): void {
    if (entry.item.disabled) return;
    this.currentValue = entry.item.value;
    this.syncTriggerLabel();
    this.config.onChange?.(entry.item);
    this.emit("combobox:change", { value: entry.item.value, item: entry.item });
    this.close();
  }

  private applyFilter(query: string): void {
    const q = query.toLowerCase().trim();
    if (!q) {
      this.filtered = this.config.items.map((item, index) => ({ item, index }));
      return;
    }
    const fuzzy = this.config.fuzzy !== false;
    const out: IndexedItem[] = [];
    this.config.items.forEach((item, index) => {
      const hay = `${item.label} ${item.value} ${item.group || ""}`.toLowerCase();
      const match = fuzzy ? Combobox.fuzzyMatch(q, hay) : hay.includes(q);
      if (match) out.push({ item, index });
    });
    this.filtered = out;
  }

  /** fzf-style subsequence match. Delegates to the shared implementation in
   *  `_base/fuzzy` so Combobox and Dropdown cannot drift apart — a list that
   *  filters differently from the one next to it teaches users to distrust
   *  both. Kept as a static method because it is part of the public surface. */
  static fuzzyMatch(query: string, hay: string): boolean {
    return fuzzyMatch(query, hay);
  }
}
