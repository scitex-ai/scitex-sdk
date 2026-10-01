/* AUTO-GENERATED from ts/app/import-export/index.ts via esbuild — do not edit by hand. Rebuild: npx esbuild ts/app/import-export/index.ts --bundle --format=esm --outfile=js/app/import-export.js */

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

// ts/app/import-export/_ImportExport.ts
var CLS = "stx-app-import-export";
var IMPORT_EXPORT_CONFIRM = "stx-import-export:confirm";
var ImportExport = class extends BaseComponent {
  trigger;
  panel;
  body;
  selected = null;
  view = "list";
  open = false;
  outsideClickHandler;
  keyHandler;
  constructor(config) {
    super(config);
    this.container.className = CLS;
    this.trigger = document.createElement("button");
    this.trigger.type = "button";
    this.trigger.className = `${CLS}__trigger stx-button`;
    this.trigger.textContent = config.title ?? (config.direction === "export" ? "Export" : "Import");
    this.trigger.setAttribute("aria-haspopup", "true");
    this.panel = document.createElement("div");
    this.panel.className = `${CLS}__panel`;
    this.body = document.createElement("div");
    this.body.className = `${CLS}__body`;
    this.panel.appendChild(this.body);
    this.container.appendChild(this.trigger);
    this.container.appendChild(this.panel);
    this.trigger.addEventListener("click", () => this.toggle());
    this.outsideClickHandler = (e) => {
      if (!this.container.contains(e.target)) {
        this.close();
      }
    };
    this.keyHandler = (e) => {
      if (e.key !== "Escape") {
        return;
      }
      if (this.view === "confirm") {
        this.showList();
      } else {
        this.close();
      }
    };
    document.addEventListener("click", this.outsideClickHandler);
    document.addEventListener("keydown", this.keyHandler);
  }
  title() {
    return this.config.title ?? (this.config.direction === "export" ? "Export" : "Import");
  }
  confirmText(label) {
    if (this.config.confirmText) {
      return this.config.confirmText(label);
    }
    return this.config.direction === "export" ? `Export as ${label}?` : `Import ${label}?`;
  }
  toggle() {
    if (this.open) {
      this.close();
    } else {
      this.open = true;
      this.view = "list";
      this.render();
      this.container.classList.add(`${CLS}--open`);
      this.trigger.setAttribute("aria-expanded", "true");
    }
  }
  close() {
    if (!this.open) {
      return;
    }
    this.open = false;
    this.container.classList.remove(`${CLS}--open`);
    this.trigger.setAttribute("aria-expanded", "false");
  }
  /** Render the current view (list or confirm bar) into the panel body. */
  render() {
    if (this.view === "confirm") {
      this.renderConfirm();
    } else {
      this.renderList();
    }
  }
  renderList() {
    this.body.innerHTML = "";
    const title = document.createElement("div");
    title.className = `${CLS}__title`;
    title.textContent = this.title();
    this.body.appendChild(title);
    if (this.config.formats.length === 0) {
      const empty = document.createElement("div");
      empty.className = `${CLS}__empty`;
      empty.textContent = "No formats available";
      this.body.appendChild(empty);
      return;
    }
    const list = document.createElement("div");
    list.className = `${CLS}__list`;
    for (const format of this.config.formats) {
      const option = document.createElement("button");
      option.type = "button";
      option.className = `${CLS}__format`;
      option.setAttribute("role", "option");
      const label = document.createElement("span");
      label.className = `${CLS}__format-label`;
      label.textContent = format.label;
      option.appendChild(label);
      if (format.detail) {
        const detail = document.createElement("span");
        detail.className = `${CLS}__format-detail`;
        detail.textContent = format.detail;
        option.appendChild(detail);
      }
      option.addEventListener("click", () => this.select(format));
      list.appendChild(option);
    }
    this.body.appendChild(list);
  }
  renderConfirm() {
    const format = this.selected;
    if (!format) {
      this.showList();
      return;
    }
    this.body.innerHTML = "";
    const text = document.createElement("div");
    text.className = `${CLS}__confirm-text`;
    text.textContent = this.confirmText(format.label);
    this.body.appendChild(text);
    const bar = document.createElement("div");
    bar.className = `${CLS}__confirm-bar`;
    const cancel = document.createElement("button");
    cancel.type = "button";
    cancel.className = `${CLS}__cancel stx-button`;
    cancel.textContent = "Cancel";
    cancel.addEventListener("click", () => this.showList());
    bar.appendChild(cancel);
    const confirm = document.createElement("button");
    confirm.type = "button";
    confirm.className = `${CLS}__confirm stx-button stx-button--primary`;
    confirm.textContent = this.config.direction === "export" ? "Export" : "Import";
    confirm.addEventListener("click", () => this.confirm(format));
    bar.appendChild(confirm);
    this.body.appendChild(bar);
  }
  select(format) {
    this.selected = format;
    this.view = "confirm";
    this.render();
  }
  showList() {
    this.selected = null;
    this.view = "list";
    this.render();
  }
  /** The user confirmed: emit the event and close. The app does the rest. */
  confirm(format) {
    this.close();
    this.emit(IMPORT_EXPORT_CONFIRM, {
      direction: this.config.direction,
      formatId: format.id,
      formatLabel: format.label
    });
  }
  destroy() {
    document.removeEventListener("click", this.outsideClickHandler);
    document.removeEventListener("keydown", this.keyHandler);
    super.destroy();
  }
};
export {
  IMPORT_EXPORT_CONFIRM,
  ImportExport
};
