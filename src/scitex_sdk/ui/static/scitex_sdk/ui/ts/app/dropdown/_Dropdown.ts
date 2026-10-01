/**
 * Dropdown — context menu attached to a trigger element.
 *
 * Usage:
 *   import { Dropdown } from 'scitex_sdk/ui/ts/app/dropdown';
 *   const menu = new Dropdown({
 *     container: '#menu-container',
 *     trigger: '#menu-btn',
 *     items: [
 *       { id: 'copy', label: 'Copy', icon: 'fas fa-copy' },
 *       { id: 'sep', label: '', separator: true },
 *       { id: 'delete', label: 'Delete', icon: 'fas fa-trash' },
 *     ],
 *     onSelect: (item) => console.log(item.id),
 *   });
 */

import { BaseComponent } from "../../_base/BaseComponent";
import { fuzzyMatch } from "../../_base/fuzzy";
import type { DropdownConfig, DropdownItem } from "./types";

const CLS = "stx-app-dropdown";

/** Item count above which the filter appears on its own. */
const DEFAULT_FILTER_THRESHOLD = 8;

export class Dropdown extends BaseComponent<DropdownConfig> {
  private triggerEl: HTMLElement;
  private open = false;
  private query = "";
  private outsideClickHandler: (e: MouseEvent) => void;
  private triggerClickHandler: (e: MouseEvent) => void;

  constructor(config: DropdownConfig) {
    super(config);

    this.triggerEl =
      typeof config.trigger === "string"
        ? (document.querySelector<HTMLElement>(config.trigger) as HTMLElement)
        : config.trigger;

    if (!this.triggerEl) {
      throw new Error(`Dropdown: trigger not found: ${config.trigger}`);
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

    // Held as a field rather than an inline closure so destroy() can actually
    // remove it. The previous version passed an anonymous function, which is
    // unremovable: every destroyed Dropdown left a live listener on its
    // trigger, and a re-created one then fired toggle() twice per click.
    this.triggerClickHandler = (e: MouseEvent) => {
      e.stopPropagation();
      this.toggle();
    };

    this.triggerEl.addEventListener("click", this.triggerClickHandler);
    document.addEventListener("click", this.outsideClickHandler);
  }

  /** Whether the filter input should be shown for the current item list. */
  private get filterEnabled(): boolean {
    if (this.config.filter !== undefined) return this.config.filter;
    const threshold = this.config.filterThreshold ?? DEFAULT_FILTER_THRESHOLD;
    const selectable = this.config.items.filter((i) => !i.separator).length;
    return selectable > threshold;
  }

  /** Items surviving the current query. Separators are dropped while
   *  filtering — a divider between two groups is meaningless once the groups
   *  it separated have been filtered away. */
  private visibleItems(): DropdownItem[] {
    if (!this.query) return this.config.items;
    const q = this.query.toLowerCase();
    return this.config.items.filter(
      (item) => !item.separator && fuzzyMatch(q, item.label.toLowerCase()),
    );
  }

  /** Open the dropdown. */
  show(): void {
    if (this.open) return;
    this.open = true;
    // Reset the query on every open. A dropdown that reopens still filtered
    // by what you typed last time appears to have lost its items.
    this.query = "";
    this.renderMenu();
    this.container.style.display = "block";
    this.positionMenu();
    this.container
      .querySelector<HTMLInputElement>(`.${CLS}__filter`)
      ?.focus();
  }

  /** Close the dropdown. */
  close(): void {
    if (!this.open) return;
    this.open = false;
    this.container.style.display = "none";
  }

  /** Toggle open/close. */
  toggle(): void {
    this.open ? this.close() : this.show();
  }

  /** Update items dynamically. */
  setItems(items: DropdownItem[]): void {
    this.config.items = items;
    if (this.open) this.renderMenu();
  }

  override destroy(): void {
    document.removeEventListener("click", this.outsideClickHandler);
    this.triggerEl.removeEventListener("click", this.triggerClickHandler);
    super.destroy();
  }

  private renderMenu(): void {
    this.container.innerHTML = "";
    this.container.className = CLS;

    if (this.filterEnabled) this.container.appendChild(this.buildFilter());

    const items = this.visibleItems();

    const menu = document.createElement("ul");
    menu.className = `${CLS}__menu`;

    if (items.length === 0) {
      const empty = document.createElement("li");
      empty.className = `${CLS}__empty`;
      empty.textContent = this.config.emptyText ?? "No matches";
      menu.appendChild(empty);
      this.container.appendChild(menu);
      return;
    }

    for (const item of items) {
      if (item.separator) {
        const sep = document.createElement("li");
        sep.className = `${CLS}__separator`;
        menu.appendChild(sep);
        continue;
      }

      const li = document.createElement("li");
      li.className = `${CLS}__item`;
      if (item.disabled) li.classList.add(`${CLS}__item--disabled`);

      if (item.icon) {
        const icon = document.createElement("i");
        icon.className = item.icon;
        li.appendChild(icon);
      }

      const label = document.createElement("span");
      label.textContent = item.label;
      li.appendChild(label);

      if (!item.disabled) {
        li.addEventListener("click", (e) => {
          e.stopPropagation();
          this.close();
          item.onClick?.();
          this.config.onSelect?.(item);
        });
      }

      menu.appendChild(li);
    }

    this.container.appendChild(menu);
  }

  private buildFilter(): HTMLInputElement {
    const input = document.createElement("input");
    input.type = "text";
    input.className = `${CLS}__filter`;
    input.placeholder = this.config.filterPlaceholder ?? "Filter…";
    input.value = this.query;
    // The list is the live region; the input labels itself so a screen reader
    // announces what typing here does.
    input.setAttribute("aria-label", input.placeholder);

    input.addEventListener("click", (e) => e.stopPropagation());

    input.addEventListener("input", () => {
      this.query = input.value;
      // Re-render replaces the input, so restore focus and caret. Without
      // this the field loses focus after the first keystroke and the user
      // types one character per click.
      const caret = input.selectionStart;
      this.renderMenu();
      const next = this.container.querySelector<HTMLInputElement>(
        `.${CLS}__filter`,
      );
      if (next) {
        next.focus();
        if (caret !== null) next.setSelectionRange(caret, caret);
      }
    });

    input.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        this.close();
        this.triggerEl.focus();
        return;
      }
      if (e.key === "Enter") {
        // Enter on a single remaining match selects it — the whole point of
        // typing to narrow. Ambiguous when several remain, so it does nothing.
        const remaining = this.visibleItems().filter((i) => !i.disabled);
        if (remaining.length === 1) {
          e.preventDefault();
          const only = remaining[0];
          this.close();
          only.onClick?.();
          this.config.onSelect?.(only);
        }
      }
    });

    return input;
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
}
