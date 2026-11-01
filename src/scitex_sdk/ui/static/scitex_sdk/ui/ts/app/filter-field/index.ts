/** Shared filter chrome. Apps own filtering data; the SDK owns input and hints. */
export class FilterField {
  readonly input: HTMLInputElement;
  private readonly hint: HTMLElement;
  private readonly icon: SVGSVGElement;
  private readonly onFocus = () => this.updateHint();
  private readonly onBlur = () => this.updateHint();
  private readonly onKey = (event: KeyboardEvent) => {
    if (event.key !== "Escape" || event.isComposing) return;
    event.preventDefault();
    event.stopPropagation();
    this.input.value = "";
    this.input.dispatchEvent(new Event("input", { bubbles: true }));
    this.input.blur();
  };
  private readonly onShortcut = (event: KeyboardEvent) => {
    if (event.defaultPrevented || event.isComposing || !event.ctrlKey && !event.metaKey ||
        event.shiftKey || event.altKey || event.key.toLowerCase() !== "k") return;
    // A page may contain several filters. The focused filter, otherwise the
    // first visible one, owns the shortcut; hidden tab panes cannot steal it.
    const visible = Array.from(document.querySelectorAll<HTMLElement>("[data-stx-filter-field-mounted]"))
      .filter(element => element.getClientRects().length > 0 && getComputedStyle(element).visibility !== "hidden");
    const focused = visible.find(element => element.contains(document.activeElement));
    if ((focused || visible[0]) !== this.element) return;
    event.preventDefault();
    this.input.focus();
    this.input.select();
  };

  constructor(readonly element: HTMLElement) {
    if (element.hasAttribute("data-stx-filter-field-mounted")) throw new Error("Filter already mounted");
    const subject = element.dataset.filterSubject?.trim();
    if (!subject) throw new Error("A filter needs data-filter-subject");
    if (element.children.length) throw new Error("Use an empty SDK filter mount");
    element.classList.add("stx-filter-field");
    this.icon = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    this.icon.classList.add("stx-filter-field__icon");
    this.icon.setAttribute("viewBox", "0 0 24 24");
    this.icon.setAttribute("aria-hidden", "true");
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", "M3 4h18l-7 8v7l-4 2v-9z");
    this.icon.append(path);
    this.input = document.createElement("input");
    this.input.type = "search";
    this.input.className = "stx-filter-field__input";
    this.input.id = element.dataset.filterId || "";
    this.input.name = "q";
    this.input.maxLength = 200;
    this.input.autocomplete = "off";
    this.input.placeholder = `Filter ${subject} with keywords`;
    this.input.setAttribute("aria-label", `Filter ${subject}`);
    this.hint = document.createElement("kbd");
    this.hint.className = "stx-filter-field__hint";
    element.append(this.icon, this.input, this.hint);
    element.setAttribute("data-stx-filter-field-mounted", "");
    this.input.addEventListener("focus", this.onFocus);
    this.input.addEventListener("blur", this.onBlur);
    this.input.addEventListener("keydown", this.onKey);
    // Runs ahead of the host global search handler, which yields to claimed keys.
    document.addEventListener("keydown", this.onShortcut, true);
    this.updateHint();
  }

  private updateHint(): void {
    const active = document.activeElement === this.input;
    this.hint.textContent = active ? "Esc" : "Ctrl+K";
    this.hint.title = active ? "Clear filter and leave search" : "Focus filter";
    this.input.setAttribute("aria-keyshortcuts", active ? "Escape" : "Control+K Meta+K");
  }

  destroy(): void {
    this.input.removeEventListener("focus", this.onFocus);
    this.input.removeEventListener("blur", this.onBlur);
    this.input.removeEventListener("keydown", this.onKey);
    document.removeEventListener("keydown", this.onShortcut, true);
    this.input.remove();
    this.icon.remove();
    this.hint.remove();
    this.element.removeAttribute("data-stx-filter-field-mounted");
    this.element.classList.remove("stx-filter-field");
    instances.delete(this.element);
  }
}

const instances = new WeakMap<HTMLElement, FilterField>();
export function mountFilterFields(root: ParentNode = document): FilterField[] {
  const elements = Array.from(root.querySelectorAll<HTMLElement>("[data-stx-filter-field]"));
  if (root instanceof HTMLElement && root.matches("[data-stx-filter-field]")) elements.unshift(root);
  return elements.map(element => {
    let instance = instances.get(element);
    if (!instance) {
      instance = new FilterField(element);
      instances.set(element, instance);
    }
    return instance;
  });
}
