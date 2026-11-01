/* AUTO-GENERATED from ts/app/filter-field/auto-mount.ts via esbuild — do not edit by hand. Rebuild: npm run build:ui -- --only js/app/filter-field.js */

// ts/app/filter-field/index.ts
var FilterField = class {
  constructor(element) {
    this.element = element;
    if (element.hasAttribute("data-stx-filter-mounted")) throw new Error("Filter already mounted");
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
    element.setAttribute("data-stx-filter-mounted", "");
    this.input.addEventListener("focus", this.onFocus);
    this.input.addEventListener("blur", this.onBlur);
    this.input.addEventListener("keydown", this.onKey);
    document.addEventListener("keydown", this.onShortcut, true);
    this.updateHint();
  }
  input;
  hint;
  icon;
  onFocus = () => this.updateHint();
  onBlur = () => this.updateHint();
  onKey = (event) => {
    if (event.key !== "Escape" || event.isComposing) return;
    event.preventDefault();
    event.stopPropagation();
    this.input.value = "";
    this.input.dispatchEvent(new Event("input", { bubbles: true }));
    this.input.blur();
  };
  onShortcut = (event) => {
    if (event.defaultPrevented || event.isComposing || !event.ctrlKey && !event.metaKey || event.shiftKey || event.altKey || event.key.toLowerCase() !== "k") return;
    const visible = Array.from(document.querySelectorAll("[data-stx-filter-mounted]")).filter((element) => element.getClientRects().length > 0 && getComputedStyle(element).visibility !== "hidden");
    const focused = visible.find((element) => element.contains(document.activeElement));
    if ((focused || visible[0]) !== this.element) return;
    event.preventDefault();
    this.input.focus();
    this.input.select();
  };
  updateHint() {
    const active = document.activeElement === this.input;
    this.hint.textContent = active ? "Esc" : "Ctrl+K";
    this.hint.title = active ? "Clear filter and leave search" : "Focus filter";
    this.input.setAttribute("aria-keyshortcuts", active ? "Escape" : "Control+K Meta+K");
  }
  destroy() {
    this.input.removeEventListener("focus", this.onFocus);
    this.input.removeEventListener("blur", this.onBlur);
    this.input.removeEventListener("keydown", this.onKey);
    document.removeEventListener("keydown", this.onShortcut, true);
    this.input.remove();
    this.icon.remove();
    this.hint.remove();
    this.element.removeAttribute("data-stx-filter-mounted");
    this.element.classList.remove("stx-filter-field");
    instances.delete(this.element);
  }
};
var instances = /* @__PURE__ */ new WeakMap();
function mountFilterFields(root = document) {
  const elements = Array.from(root.querySelectorAll("[data-stx-filter]"));
  if (root instanceof HTMLElement && root.matches("[data-stx-filter]")) elements.unshift(root);
  return elements.map((element) => {
    let instance = instances.get(element);
    if (!instance) {
      instance = new FilterField(element);
      instances.set(element, instance);
    }
    return instance;
  });
}

// ts/app/filter-field/auto-mount.ts
mountFilterFields();
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => mountFilterFields(), { once: true });
}
export {
  FilterField,
  mountFilterFields
};
