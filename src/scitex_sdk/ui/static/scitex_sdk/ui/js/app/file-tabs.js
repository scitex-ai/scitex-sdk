/* AUTO-GENERATED from ts/app/file-tabs/index.ts via esbuild — do not edit by hand. Rebuild: npx esbuild ts/app/file-tabs/index.ts --bundle --format=esm --outfile=js/app/file-tabs.js */
var __defProp = Object.defineProperty;
var __defNormalProp = (obj, key, value) => key in obj ? __defProp(obj, key, { enumerable: true, configurable: true, writable: true, value }) : obj[key] = value;
var __publicField = (obj, key, value) => __defNormalProp(obj, typeof key !== "symbol" ? key + "" : key, value);

// ts/_base/BaseComponent.ts
var BaseComponent = class {
  constructor(config) {
    __publicField(this, "container");
    __publicField(this, "config");
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

// ts/app/file-tabs/_FileTabs.ts
var CLS = "stx-app-file-tabs";
var FileTabs = class extends BaseComponent {
  constructor(config) {
    super(config);
    __publicField(this, "tabs", []);
    __publicField(this, "activeTab", null);
    __publicField(this, "draggedPath", null);
    this.container.classList.add(CLS);
  }
  /** Add a tab (activates it). */
  addTab(tab) {
    if (!this.tabs.find((t) => t.path === tab.path)) {
      this.tabs.push(tab);
    }
    this.activeTab = tab.path;
    this.render();
  }
  /** Remove a tab. */
  removeTab(path) {
    this.tabs = this.tabs.filter((t) => t.path !== path);
    if (this.activeTab === path) {
      this.activeTab = this.tabs.length > 0 ? this.tabs[this.tabs.length - 1].path : null;
    }
    this.render();
  }
  /** Set the active tab. */
  setActive(path) {
    this.activeTab = path;
    this.render();
  }
  /** Mark a tab as dirty/clean. */
  setDirty(path, dirty) {
    const tab = this.tabs.find((t) => t.path === path);
    if (tab) {
      tab.isDirty = dirty;
      this.render();
    }
  }
  /** Get active tab path. */
  getActive() {
    return this.activeTab;
  }
  /** Get all open tab paths. */
  getPaths() {
    return this.tabs.map((t) => t.path);
  }
  /** Switch to next tab. */
  nextTab() {
    if (this.tabs.length === 0) return;
    const idx = this.tabs.findIndex((t) => t.path === this.activeTab);
    const next = (idx + 1) % this.tabs.length;
    this.config.onTabSwitch(this.tabs[next].path);
  }
  /** Switch to previous tab. */
  prevTab() {
    if (this.tabs.length === 0) return;
    const idx = this.tabs.findIndex((t) => t.path === this.activeTab);
    const prev = (idx - 1 + this.tabs.length) % this.tabs.length;
    this.config.onTabSwitch(this.tabs[prev].path);
  }
  destroy() {
    this.container.classList.remove(CLS);
    super.destroy();
  }
  render() {
    this.container.innerHTML = "";
    for (const tab of this.tabs) {
      const el = this.createTab(tab);
      this.container.appendChild(el);
    }
    if (this.config.showNewButton !== false && this.config.onNewFile) {
      const plus = document.createElement("button");
      plus.className = `${CLS}__new`;
      plus.innerHTML = "+";
      plus.title = "New file";
      plus.addEventListener("click", () => this.promptNewFile(plus));
      this.container.appendChild(plus);
    }
  }
  createTab(tab) {
    const isActive = tab.path === this.activeTab;
    const isPermanent = tab.path === this.config.permanentTab || tab.isPermanent;
    const label = tab.label || tab.path.split("/").pop() || tab.path;
    const el = document.createElement("button");
    el.className = `${CLS}__tab`;
    if (isActive) el.classList.add(`${CLS}__tab--active`);
    if (tab.isDirty) el.classList.add(`${CLS}__tab--dirty`);
    el.title = tab.path;
    const nameSpan = document.createElement("span");
    nameSpan.className = `${CLS}__label`;
    nameSpan.textContent = label;
    el.appendChild(nameSpan);
    if (tab.isDirty) {
      const dot = document.createElement("span");
      dot.className = `${CLS}__dirty`;
      dot.textContent = "\u25CF";
      el.appendChild(dot);
    }
    if (!isPermanent) {
      const closeBtn = document.createElement("span");
      closeBtn.className = `${CLS}__close`;
      closeBtn.textContent = "\xD7";
      closeBtn.title = "Close";
      closeBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        this.config.onTabClose(tab.path);
      });
      el.appendChild(closeBtn);
    }
    el.addEventListener("click", () => this.config.onTabSwitch(tab.path));
    if (this.config.onRename && !isPermanent) {
      el.addEventListener("dblclick", (e) => {
        e.preventDefault();
        this.startRename(tab.path, nameSpan);
      });
    }
    if (this.config.allowReorder !== false) {
      this.setupDrag(el, tab.path);
    }
    return el;
  }
  setupDrag(el, path) {
    el.draggable = true;
    el.addEventListener("dragstart", (e) => {
      this.draggedPath = path;
      el.classList.add(`${CLS}__tab--dragging`);
      e.dataTransfer?.setData("text/plain", path);
    });
    el.addEventListener("dragend", () => {
      this.draggedPath = null;
      el.classList.remove(`${CLS}__tab--dragging`);
    });
    el.addEventListener("dragover", (e) => {
      e.preventDefault();
      if (this.draggedPath && this.draggedPath !== path) {
        el.classList.add(`${CLS}__tab--drag-over`);
      }
    });
    el.addEventListener("dragleave", () => {
      el.classList.remove(`${CLS}__tab--drag-over`);
    });
    el.addEventListener("drop", (e) => {
      e.preventDefault();
      el.classList.remove(`${CLS}__tab--drag-over`);
      if (this.draggedPath && this.draggedPath !== path) {
        const fromIdx = this.tabs.findIndex((t) => t.path === this.draggedPath);
        const toIdx = this.tabs.findIndex((t) => t.path === path);
        if (fromIdx !== -1 && toIdx !== -1) {
          const [moved] = this.tabs.splice(fromIdx, 1);
          this.tabs.splice(toIdx, 0, moved);
          this.render();
        }
      }
    });
  }
  startRename(path, labelEl) {
    const fileName = path.split("/").pop() || path;
    const input = document.createElement("input");
    input.type = "text";
    input.value = fileName;
    input.className = `${CLS}__rename-input`;
    labelEl.style.display = "none";
    labelEl.parentElement?.insertBefore(input, labelEl);
    input.focus();
    input.select();
    const finish = () => {
      const newName = input.value.trim();
      labelEl.style.display = "";
      input.remove();
      if (newName && newName !== fileName && this.config.onRename) {
        const dir = path.includes("/") ? path.substring(0, path.lastIndexOf("/")) : "";
        this.config.onRename(path, dir ? `${dir}/${newName}` : newName);
      }
    };
    input.addEventListener("blur", finish);
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        finish();
      } else if (e.key === "Escape") {
        labelEl.style.display = "";
        input.remove();
      }
    });
  }
  promptNewFile(plusBtn) {
    if (!this.config.onNewFile) return;
    const input = document.createElement("input");
    input.type = "text";
    input.className = `${CLS}__new-input`;
    input.placeholder = "filename";
    this.container.insertBefore(input, plusBtn);
    input.focus();
    const finish = () => {
      const name = input.value.trim();
      input.remove();
      if (name) this.config.onNewFile(name);
    };
    input.addEventListener("blur", finish);
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        finish();
      } else if (e.key === "Escape") {
        input.remove();
      }
    });
  }
};
export {
  FileTabs
};
