/**
 * Sidebar — collapse/expand logic for stx-shell-sidebar.
 */

const CLS = "stx-shell-sidebar";

export interface SidebarOptions {
  width: number;
  collapsible: boolean;
  startCollapsed: boolean;
  title: string;
  icon: string;
  storageKey: string;
  onToggle?: (collapsed: boolean) => void;
}

export class Sidebar {
  readonly element: HTMLElement;
  readonly headerSlot: HTMLElement;
  readonly contentSlot: HTMLElement;
  private collapsed: boolean;
  private options: SidebarOptions;

  constructor(options: SidebarOptions) {
    this.options = options;

    const stored = localStorage.getItem(options.storageKey);
    this.collapsed =
      stored !== null ? stored === "true" : options.startCollapsed;

    this.element = document.createElement("aside");
    this.element.className = CLS;
    this.element.style.width = `${options.width}px`;

    // Header
    const header = document.createElement("div");
    header.className = `${CLS}__header`;

    const heading = document.createElement("h5");
    if (options.icon) {
      const icon = document.createElement("i");
      icon.className = options.icon;
      heading.appendChild(icon);
    }
    heading.appendChild(document.createTextNode(options.title));
    header.appendChild(heading);

    // Collapsed title
    const collapsedTitle = document.createElement("div");
    collapsedTitle.className = `${CLS}__title`;
    if (options.icon) {
      const collapsedIcon = document.createElement("i");
      collapsedIcon.className = options.icon;
      collapsedTitle.appendChild(collapsedIcon);
    }
    const collapsedLabel = document.createElement("span");
    collapsedLabel.textContent = options.title;
    collapsedTitle.appendChild(collapsedLabel);
    header.appendChild(collapsedTitle);

    // Toggle button
    if (options.collapsible) {
      const toggle = document.createElement("button");
      toggle.className = `${CLS}__toggle`;
      toggle.innerHTML = '<i class="fas fa-angles-left"></i>';
      toggle.addEventListener("click", (e) => {
        e.stopPropagation();
        this.toggle();
      });
      header.appendChild(toggle);

      this.element.addEventListener("click", () => {
        if (this.collapsed) this.toggle();
      });
    }

    this.headerSlot = header;
    this.element.appendChild(header);

    this.contentSlot = document.createElement("div");
    this.contentSlot.className = `${CLS}__content`;
    this.element.appendChild(this.contentSlot);

    if (this.collapsed) {
      this.element.classList.add(`${CLS}--collapsed`);
    }
  }

  isCollapsed(): boolean {
    return this.collapsed;
  }

  collapse(): void {
    if (!this.collapsed) this.toggle();
  }

  expand(): void {
    if (this.collapsed) this.toggle();
  }

  toggle(): void {
    this.collapsed = !this.collapsed;
    this.element.classList.toggle(`${CLS}--collapsed`, this.collapsed);
    localStorage.setItem(this.options.storageKey, String(this.collapsed));
    this.options.onToggle?.(this.collapsed);
  }
}
